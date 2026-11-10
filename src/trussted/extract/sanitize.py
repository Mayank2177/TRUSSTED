"""HTML -> clean visible text. Removes hidden/invisible content and collects page JSON-LD.

Limitations (documented, not hidden): hidden-content detection uses inline attributes/styles
only; CSS in stylesheets is not evaluated. Injection-pattern matches are advisory flags.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from html.parser import HTMLParser

from ..config import SanitizeConfig
from ..errors import SanitizationError
from ..models.facts import StructuredProduct
from .structured import parse_jsonld_products

_VOID = frozenset(
    "area base br col embed hr img input link meta param source track wbr".split()
)
_SKIP = frozenset("script style noscript template svg iframe object canvas".split())
_BLOCK = frozenset(
    "address article aside blockquote br dd div dl dt fieldset footer form h1 h2 h3 h4 h5 h6 "
    "header hr li main nav ol p pre section table td th tr ul".split()
)
_HIDDEN_STYLE = re.compile(
    r"display:none|visibility:hidden|font-size:0(?![\d.])|opacity:0(?:\.0*)?(?:;|$)"
    r"|(?:left|top|text-indent):-\d{4,}px",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class SanitizedPage:
    text: str
    structured: tuple[StructuredProduct, ...]
    hidden_chars_removed: int
    control_chars_removed: int
    truncated: bool
    flags: tuple[str, ...]


def _is_hidden(tag: str, attrs: dict[str, str | None]) -> bool:
    if "hidden" in attrs:
        return True
    if (attrs.get("aria-hidden") or "").strip().lower() == "true":
        return True
    if tag == "input" and (attrs.get("type") or "").strip().lower() == "hidden":
        return True
    style = attrs.get("style")
    return bool(style and _HIDDEN_STYLE.search(re.sub(r"\s+", "", style)))


class _Collector(HTMLParser):
    def __init__(self, config: SanitizeConfig) -> None:
        super().__init__(convert_charrefs=True)
        self._config = config
        self._stack: list[tuple[str, bool, bool]] = []  # (tag, hidden, skip)
        self._hidden = 0
        self._skip = 0
        self._in_jsonld = False
        self._jsonld_buf: list[str] = []
        self.parts: list[str] = []
        self.hidden_chars = 0
        self.jsonld_blocks: list[str] = []
        self.flags: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr_map = {k.lower(): v for k, v in attrs}
        if tag in _VOID:
            if tag in _BLOCK and not self._skip and not self._hidden:
                self.parts.append("\n")
            return
        hidden = _is_hidden(tag, attr_map)
        skip = tag in _SKIP
        if tag == "script" and (attr_map.get("type") or "").lower().split(";")[0].strip() == "application/ld+json":
            self._in_jsonld = True
            self._jsonld_buf = []
        self._stack.append((tag, hidden, skip))
        self._hidden += hidden
        self._skip += skip
        if tag in _BLOCK and not self._skip and not self._hidden:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _VOID:
            return
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                while len(self._stack) > i:
                    t, hidden, skip = self._stack.pop()
                    self._hidden -= hidden
                    self._skip -= skip
                    if t == "script" and self._in_jsonld:
                        self._finish_jsonld()
                if tag in _BLOCK and not self._skip and not self._hidden:
                    self.parts.append("\n")
                return
        # unmatched end tag: ignore

    def _finish_jsonld(self) -> None:
        self._in_jsonld = False
        raw = "".join(self._jsonld_buf)
        self._jsonld_buf = []
        if len(self.jsonld_blocks) >= self._config.max_jsonld_blocks:
            self.flags.add("jsonld_limit_exceeded")
        elif len(raw) > self._config.max_jsonld_bytes:
            self.flags.add("jsonld_limit_exceeded")
        elif raw.strip():
            self.jsonld_blocks.append(raw)

    def handle_data(self, data: str) -> None:
        if self._in_jsonld:
            self._jsonld_buf.append(data)
        elif self._skip:
            return
        elif self._hidden:
            self.hidden_chars += len(data.strip())
        else:
            self.parts.append(data)


def _clean(text: str) -> tuple[str, int]:
    removed = 0
    out: list[str] = []
    for ch in unicodedata.normalize("NFKC", text):
        if ch in "\r\x0b\x0c":
            out.append("\n")
        elif ch in "\n\t ":
            out.append(ch)
        elif unicodedata.category(ch) in ("Cc", "Cf", "Co", "Cs", "Cn"):
            removed += 1
        else:
            out.append(ch)
    cleaned = "".join(out)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r" ?\n ?", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip(), removed


def sanitize_html(html: str, config: SanitizeConfig) -> SanitizedPage:
    if not isinstance(html, str):
        raise SanitizationError("html must be a string")
    if len(html) > config.max_html_chars:
        raise SanitizationError(f"html exceeds {config.max_html_chars} characters")
    collector = _Collector(config)
    try:
        collector.feed(html)
        collector.close()
    except (AssertionError, ValueError, RecursionError) as exc:
        raise SanitizationError(f"unparseable html: {exc}") from exc

    text, control_removed = _clean("".join(collector.parts))
    flags = set(collector.flags)
    truncated = len(text) > config.max_text_chars
    if truncated:
        text = text[: config.max_text_chars]
        flags.add("truncated")
    if collector.hidden_chars:
        flags.add("hidden_text_removed")
    if control_removed:
        flags.add("control_chars_removed")
    if any(re.search(p, text, re.IGNORECASE | re.DOTALL) for p in config.injection_patterns):
        flags.add("injection_marker_detected")

    products, jsonld_flags = parse_jsonld_products(collector.jsonld_blocks)
    flags.update(jsonld_flags)
    return SanitizedPage(
        text=text,
        structured=tuple(products),
        hidden_chars_removed=collector.hidden_chars,
        control_chars_removed=control_removed,
        truncated=truncated,
        flags=tuple(sorted(flags)),
    )
