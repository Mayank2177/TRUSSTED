"""Typed, validated configuration. Every tunable lives here; nothing is buried in logic.

Scalar fields can be overridden from the environment as ``TRUSSTED_<SECTION>_<FIELD>``
(e.g. ``TRUSSTED_EXTRACTION_MAX_RETRIES=3``). Complex fields are set in code.
"""

from __future__ import annotations

import os
import re
import types
from collections.abc import Mapping
from dataclasses import dataclass, field, fields, replace
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

from .errors import ConfigError

Severity = Literal["low", "medium", "high"]
UnknownPolicy = Literal["flag", "violation"]

_SEVERITIES = ("low", "medium", "high")
_POLICIES = ("flag", "violation")
_PROMPT_VERSION_RE = re.compile(r"^[a-z0-9_]{1,64}$")


def _require(cond: bool, message: str) -> None:
    if not cond:
        raise ConfigError(message)


@dataclass(frozen=True, slots=True)
class SanitizeConfig:
    max_html_chars: int = 2_000_000
    max_text_chars: int = 60_000
    max_jsonld_blocks: int = 20
    max_jsonld_bytes: int = 200_000
    # Advisory heuristics only (they raise a flag; they are NOT a defence).
    injection_patterns: tuple[str, ...] = (
        r"ignore\s+(all\s+|any\s+)?(previous|prior|above)\s+(instructions|prompts?)",
        r"disregard\s+(the\s+)?(system|previous|above)",
        r"\byou\s+are\s+now\b",
        r"\bsystem\s+prompt\b",
        r"\b(select|choose|buy|purchase|pick)\s+this\s+(item|product|offer|one)\b",
        r"do\s+not\s+(tell|inform|notify)\s+the\s+user",
        r"\bAI\s+(agent|assistant|model)s?\b.{0,40}\b(must|should|always|only)\b",
    )

    def __post_init__(self) -> None:
        for name in ("max_html_chars", "max_text_chars", "max_jsonld_blocks", "max_jsonld_bytes"):
            _require(getattr(self, name) > 0, f"sanitize.{name} must be > 0")
        for pattern in self.injection_patterns:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ConfigError(f"invalid injection pattern {pattern!r}: {exc}") from exc


@dataclass(frozen=True, slots=True)
class ExtractionConfig:
    prompt_version: str = "extraction_v1"
    max_products_per_page: int = 50
    max_specs_per_product: int = 60
    max_text_field_chars: int = 300
    min_evidence_chars: int = 3
    max_retries: int = 2
    retry_backoff_s: float = 0.5
    timeout_s: float = 60.0
    seed: int | None = 0

    def __post_init__(self) -> None:
        _require(bool(_PROMPT_VERSION_RE.match(self.prompt_version)), "invalid prompt_version")
        _require(self.max_products_per_page > 0, "max_products_per_page must be > 0")
        _require(self.max_specs_per_product > 0, "max_specs_per_product must be > 0")
        _require(self.max_text_field_chars >= 10, "max_text_field_chars must be >= 10")
        _require(self.min_evidence_chars >= 1, "min_evidence_chars must be >= 1")
        _require(self.max_retries >= 0, "max_retries must be >= 0")
        _require(self.retry_backoff_s >= 0, "retry_backoff_s must be >= 0")
        _require(self.timeout_s > 0, "timeout_s must be > 0")


def _default_severities() -> Mapping[str, Severity]:
    return MappingProxyType(
        {"price": "high", "currency": "high", "recurring": "high", "spec": "high", "brand": "medium"}
    )


def _default_spec_aliases() -> Mapping[str, tuple[str, ...]]:
    return MappingProxyType(
        {"capacity": ("storage", "storage capacity", "disk size", "memory", "memory size")}
    )


@dataclass(frozen=True, slots=True)
class VerifyConfig:
    price_tolerance_pct: Decimal = Decimal("0")
    price_tolerance_minor: int = 0
    severities: Mapping[str, Severity] = field(default_factory=_default_severities)
    spec_aliases: Mapping[str, tuple[str, ...]] = field(default_factory=_default_spec_aliases)

    def __post_init__(self) -> None:
        _require(self.price_tolerance_pct >= 0, "price_tolerance_pct must be >= 0")
        _require(self.price_tolerance_minor >= 0, "price_tolerance_minor must be >= 0")
        for key, sev in self.severities.items():
            _require(sev in _SEVERITIES, f"invalid severity for {key!r}: {sev!r}")

    def severity(self, kind: str) -> Severity:
        """Severity for a conflict kind; unknown kinds default to 'high' (fail closed)."""
        return self.severities.get(kind, "high")


def _default_unknown_policy() -> Mapping[str, UnknownPolicy]:
    return MappingProxyType(
        {"shipping": "flag", "delivery": "flag", "condition": "flag", "recurring": "flag"}
    )


@dataclass(frozen=True, slots=True)
class RankConfig:
    exclude_high_conflicts: bool = True
    unknown_policy: Mapping[str, UnknownPolicy] = field(default_factory=_default_unknown_policy)
    missing_component_score: Decimal = Decimal("0")
    score_places: int = 6

    def __post_init__(self) -> None:
        _require(Decimal("0") <= self.missing_component_score <= Decimal("1"),
                 "missing_component_score must be in [0, 1]")
        _require(0 <= self.score_places <= 12, "score_places must be in [0, 12]")
        for key, pol in self.unknown_policy.items():
            _require(pol in _POLICIES, f"invalid unknown policy for {key!r}: {pol!r}")

    def policy_for(self, name: str) -> UnknownPolicy:
        return self.unknown_policy.get(name, "flag")


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    max_pages: int = 20

    def __post_init__(self) -> None:
        _require(self.max_pages > 0, "max_pages must be > 0")


@dataclass(frozen=True, slots=True)
class LLMConfig:
    model: str = ""
    max_tokens: int = 4096
    api_key_env: str = "ANTHROPIC_API_KEY"

    def __post_init__(self) -> None:
        _require(self.max_tokens > 0, "max_tokens must be > 0")


@dataclass(frozen=True, slots=True)
class PolicyConfig:
    policy_version: str = "policy_v1"
    stage_error_result: str = "STEP_UP"          # STEP_UP or BLOCK
    step_up_total_above: Decimal | None = None   # major units of the intent currency
    require_reference_above: Decimal | None = Decimal("50")
    min_winner_margin: Decimal | None = Decimal("0.02")
    step_up_flags: tuple[str, ...] = ("COST_LOWER_BOUND", "RECURRING_UNKNOWN", "CONFLICT_PRESENT")
    step_up_page_flags: tuple[str, ...] = ("injection_marker_detected", "hidden_text_removed")

    def __post_init__(self) -> None:
        _require(self.stage_error_result in ("STEP_UP", "BLOCK"), "invalid stage_error_result")
        _require(bool(self.policy_version.strip()), "policy_version is empty")
        for name in ("step_up_total_above", "require_reference_above", "min_winner_margin"):
            v = getattr(self, name)
            _require(v is None or (v.is_finite() and v >= 0), f"{name} must be >= 0 or None")


@dataclass(frozen=True, slots=True)
class Channel3Config:
    base_url: str = "https://api.trychannel3.com"
    api_key_env: str = "CHANNEL3_API_KEY"
    timeout_s: float = 15.0
    max_retries: int = 2
    retry_backoff_s: float = 0.5
    default_limit: int = 10
    max_limit: int = 30

    def __post_init__(self) -> None:
        _require(self.base_url.startswith("https://"), "channel3 base_url must be https")
        _require(self.timeout_s > 0 and self.max_retries >= 0, "invalid channel3 timeout/retries")
        _require(1 <= self.default_limit <= self.max_limit, "invalid channel3 limits")


@dataclass(frozen=True, slots=True)
class PayPalConfig:
    environment: str = "sandbox"                 # "sandbox" or "live"
    allow_live: bool = False                     # live money requires explicit opt-in
    client_id_env: str = "PAYPAL_CLIENT_ID"
    client_secret_env: str = "PAYPAL_CLIENT_SECRET"
    return_url: str = ""
    cancel_url: str = ""
    timeout_s: float = 20.0
    max_retries: int = 2
    retry_backoff_s: float = 0.5

    def __post_init__(self) -> None:
        _require(self.environment in ("sandbox", "live"), "paypal environment must be sandbox|live")
        _require(self.environment == "sandbox" or self.allow_live,
                 "live PayPal requires allow_live=True")
        for name in ("return_url", "cancel_url"):
            v = getattr(self, name)
            _require(v == "" or v.startswith("https://"), f"paypal {name} must be https")
        _require(self.timeout_s > 0 and self.max_retries >= 0, "invalid paypal timeout/retries")

    @property
    def base_url(self) -> str:
        return ("https://api-m.sandbox.paypal.com" if self.environment == "sandbox"
                else "https://api-m.paypal.com")


@dataclass(frozen=True, slots=True)
class Settings:
    sanitize: SanitizeConfig = field(default_factory=SanitizeConfig)
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)
    verify: VerifyConfig = field(default_factory=VerifyConfig)
    rank: RankConfig = field(default_factory=RankConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    policy: PolicyConfig = field(default_factory=PolicyConfig)
    channel3: Channel3Config = field(default_factory=Channel3Config)
    paypal: PayPalConfig = field(default_factory=PayPalConfig)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        source = os.environ if env is None else env
        base = cls()
        updates = {
            f.name: _apply_env(getattr(base, f.name), f.name, source) for f in fields(cls)
        }
        return replace(base, **updates)


def _unwrap_optional(annotation: Any) -> tuple[Any, bool]:
    if get_origin(annotation) in (Union, types.UnionType):
        args = get_args(annotation)
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1 and len(args) == 2:
            return non_none[0], True
    return annotation, False


def _coerce(raw: str, annotation: Any, key: str) -> Any:
    base, optional = _unwrap_optional(annotation)
    value = raw.strip()
    if optional and value == "":
        return None
    try:
        if base is bool:
            lowered = value.lower()
            if lowered in ("1", "true", "yes", "on"):
                return True
            if lowered in ("0", "false", "no", "off"):
                return False
            raise ValueError("expected a boolean")
        if base is int:
            return int(value)
        if base is float:
            return float(value)
        if base is Decimal:
            return Decimal(value)
        if base is str:
            return raw
    except (ValueError, InvalidOperation) as exc:
        raise ConfigError(f"{key}: cannot parse {raw!r} ({exc})") from exc
    raise ConfigError(f"{key}: not configurable via environment")


def _apply_env(section: Any, section_name: str, env: Mapping[str, str]) -> Any:
    hints = get_type_hints(type(section))
    updates: dict[str, Any] = {}
    for f in fields(section):
        key = f"TRUSSTED_{section_name}_{f.name}".upper()
        if key in env:
            updates[f.name] = _coerce(env[key], hints[f.name], key)
    return replace(section, **updates) if updates else section
