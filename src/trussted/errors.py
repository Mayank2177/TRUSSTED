"""Exception hierarchy. Pipeline boundaries convert these into fail-closed outcomes."""

from __future__ import annotations


class TrusstedError(Exception):
    """Base class for all expected, handled errors."""


class ConfigError(TrusstedError):
    """Invalid or missing configuration."""


class ValidationError(TrusstedError):
    """Domain data failed validation."""


class SanitizationError(TrusstedError):
    """Page content could not be safely sanitized."""


class LLMError(TrusstedError):
    """Failure calling the language model."""


class LLMTransientError(LLMError):
    """Retryable LLM failure (timeout, rate limit, 5xx)."""


class LLMResponseError(LLMError):
    """LLM returned something unusable."""


class ExtractionError(TrusstedError):
    """Extraction stage failed for a page."""


class VerificationError(TrusstedError):
    """Cross-check stage failed."""


class RankingError(TrusstedError):
    """Ranking stage failed."""


class IntegrationError(TrusstedError):
    """A third-party API call failed in a non-retryable way."""


class TransientIntegrationError(IntegrationError):
    """A third-party API call failed after retries (network, 429, 5xx)."""


class PaymentError(IntegrationError):
    """A payment operation was refused or failed."""
