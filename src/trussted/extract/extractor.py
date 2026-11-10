"""Stage 1: page -> grounded ProductFacts. The LLM is untrusted and only ever sees page text."""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib import resources
from typing import Any

from ..config import ExtractionConfig, SanitizeConfig
from ..errors import (
    ConfigError,
    ExtractionError,
    LLMError,
    LLMTransientError,
    SanitizationError,
)
from ..llm.base import LLMClient, LLMRequest, LLMResponse
from ..models.facts import Observation, PageInput, ProductFact, RejectedFact
from ..models.ids import merchant_id_from_url
from .facts_builder import Rejected, build_fact, normalize_for_match
from .sanitize import sanitize_html
from .schema import product_list_schema

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PageExtraction:
    observation: Observation
    facts: tuple[ProductFact, ...]
    rejected: tuple[RejectedFact, ...]
    warnings: tuple[str, ...] = ()


def load_prompt(version: str) -> str:
    try:
        return resources.files("trussted.extract.prompts").joinpath(f"{version}.txt").read_text(
            encoding="utf-8"
        )
    except (FileNotFoundError, ModuleNotFoundError, OSError) as exc:
        raise ConfigError(f"prompt {version!r} not found") from exc


def _dedupe_key(fact: ProductFact) -> tuple[str, int, str, str]:
    return (fact.name.casefold(), fact.price.amount_minor, fact.price.currency, fact.sku or "")


class ProductExtractor:
    def __init__(
        self,
        llm: LLMClient,
        extraction: ExtractionConfig,
        sanitize: SanitizeConfig,
        *,
        system_prompt: str | None = None,
        nonce_factory: Callable[[], str] = lambda: secrets.token_hex(8),
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._llm = llm
        self._cfg = extraction
        self._sanitize_cfg = sanitize
        self._system = system_prompt if system_prompt is not None else load_prompt(
            extraction.prompt_version
        )
        self._nonce = nonce_factory
        self._sleep = sleep
        self._schema = product_list_schema(extraction.max_products_per_page)

    def extract(self, page: PageInput) -> PageExtraction:
        merchant_id = merchant_id_from_url(page.url)
        try:
            clean = sanitize_html(page.html, self._sanitize_cfg)
        except SanitizationError as exc:
            raise ExtractionError(f"{page.url}: {exc}") from exc

        digest = hashlib.sha256(f"{page.url}\n{page.html}".encode()).hexdigest()
        observation_id = f"obs_{digest[:16]}"
        flags = list(clean.flags)
        if not clean.text:
            flags.append("empty_page")
        observation = Observation(
            observation_id=observation_id, url=page.url, merchant_id=merchant_id,
            content_hash=hashlib.sha256(page.html.encode()).hexdigest(),
            text_chars=len(clean.text), hidden_chars_removed=clean.hidden_chars_removed,
            control_chars_removed=clean.control_chars_removed, truncated=clean.truncated,
            flags=tuple(sorted(set(flags))), structured=clean.structured,
        )
        if not clean.text:
            return PageExtraction(observation, (), ())

        response = self._call_llm(clean.text)
        items, warnings = self._parse_payload(response)
        normalized_text = normalize_for_match(clean.text)

        facts: list[ProductFact] = []
        rejected: list[RejectedFact] = []
        seen: set[tuple[str, int, str, str]] = set()
        for index, raw in enumerate(items):
            try:
                fact = build_fact(
                    index=index, raw=raw, observation_id=observation_id,
                    merchant_id=merchant_id, normalized_page_text=normalized_text, cfg=self._cfg,
                    source_url=page.url,
                )
            except Rejected as exc:
                name = raw.get("name") if isinstance(raw, Mapping) else None
                rejected.append(RejectedFact(observation_id, index, exc.reason,
                                             name if isinstance(name, str) else None))
                continue
            key = _dedupe_key(fact)
            if key in seen:
                rejected.append(RejectedFact(observation_id, index, "duplicate", fact.name))
                continue
            seen.add(key)
            facts.append(fact)
        logger.info("extracted observation=%s facts=%d rejected=%d model=%s",
                    observation_id, len(facts), len(rejected), response.model)
        return PageExtraction(observation, tuple(facts), tuple(rejected), tuple(warnings))

    def _call_llm(self, page_text: str) -> LLMResponse:
        marker = f"page_data_{self._nonce()}"
        body = page_text.replace(marker, "")
        request = LLMRequest(
            system=self._system,
            user=f"Extract all product offers from the page text between the markers.\n"
                 f"<{marker}>\n{body}\n</{marker}>",
            schema=self._schema, seed=self._cfg.seed, timeout_s=self._cfg.timeout_s,
        )
        attempt = 0
        while True:
            try:
                return self._llm.complete_json(request)
            except LLMTransientError as exc:
                if attempt >= self._cfg.max_retries:
                    raise ExtractionError(f"LLM unavailable after {attempt + 1} attempts: {exc}") from exc
                self._sleep(self._cfg.retry_backoff_s * (2**attempt))
                attempt += 1
            except LLMError as exc:
                raise ExtractionError(f"LLM failure: {exc}") from exc

    def _parse_payload(self, response: LLMResponse) -> tuple[list[Any], list[str]]:
        data = response.data
        if not isinstance(data, Mapping) or not isinstance(data.get("products"), list):
            raise ExtractionError("LLM output missing 'products' list")
        items: list[Any] = list(data["products"])
        warnings: list[str] = []
        if len(items) > self._cfg.max_products_per_page:
            items = items[: self._cfg.max_products_per_page]
            warnings.append("products_truncated")
        return items, warnings
