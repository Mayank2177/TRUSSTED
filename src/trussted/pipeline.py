"""Stages 1-3 orchestration. Errors are isolated per page and surfaced, never swallowed."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from .config import Settings
from .errors import ValidationError, VerificationError, TrusstedError
from .extract.extractor import ProductExtractor
from .llm.base import LLMClient
from .models.facts import CandidateSet, Observation, PageInput, ProductFact, RejectedFact
from .models.intent import UserIntent
from .models.results import RankResult, SelectionResult, StageError
from .rank.scorer import rank_candidates
from .verify.crosscheck import CrossChecker
from .verify.reference import ReferenceSource

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SelectionPipeline:
    extractor: ProductExtractor
    checker: CrossChecker
    settings: Settings

    @classmethod
    def build(
        cls, llm: LLMClient, references: Sequence[ReferenceSource], settings: Settings | None = None
    ) -> SelectionPipeline:
        s = settings or Settings()
        return cls(
            extractor=ProductExtractor(llm, s.extraction, s.sanitize),
            checker=CrossChecker(references, s.verify),
            settings=s,
        )

    def run(
        self, intent: UserIntent, pages: Sequence[PageInput], candidates: CandidateSet | None = None
    ) -> SelectionResult:
        if not pages and (candidates is None or not candidates.facts):
            raise ValidationError("no pages or candidates supplied")
        cfg = self.settings
        warnings: list[str] = []
        errors: list[StageError] = []
        if len(pages) > cfg.pipeline.max_pages:
            warnings.append(f"pages_truncated:{len(pages)}->{cfg.pipeline.max_pages}")
            pages = pages[: cfg.pipeline.max_pages]

        observations: list[Observation] = []
        facts: list[ProductFact] = []
        rejected: list[RejectedFact] = []
        seen_obs: set[str] = set()
        for page in pages:
            try:
                result = self.extractor.extract(page)
            except TrusstedError as exc:
                logger.warning("extraction failed: %s", type(exc).__name__)
                errors.append(StageError("extract", page.url, str(exc)))
                continue
            if result.observation.observation_id in seen_obs:
                warnings.append(f"duplicate_page:{page.url}")
                continue
            seen_obs.add(result.observation.observation_id)
            observations.append(result.observation)
            facts.extend(result.facts)
            rejected.extend(result.rejected)
            warnings.extend(result.warnings)

        if candidates is not None:
            observations.extend(candidates.observations)
            facts.extend(candidates.facts)

        try:
            verifications, verify_errors = self.checker.verify(facts, observations)
            errors.extend(verify_errors)
        except VerificationError as exc:
            errors.append(StageError("verify", "-", str(exc)))
            verifications = ()

        try:
            ranking = rank_candidates(intent, facts, verifications, cfg.rank, cfg.verify)
        except TrusstedError as exc:
            errors.append(StageError("rank", "-", str(exc)))
            ranking = RankResult((), (), None, None)

        return SelectionResult(
            observations=tuple(observations), facts=tuple(facts), rejected=tuple(rejected),
            verifications=tuple(verifications), ranking=ranking, stage_errors=tuple(errors),
            warnings=tuple(warnings),
        )
