"""Domain models (frozen, validated dataclasses)."""

from .decision import Decision, DecisionResult, Reason, ReasonCode
from .facts import (
    CandidateSet,
    Condition,
    FactConflict,
    FactVerification,
    Observation,
    PageInput,
    ProductFact,
    RejectedFact,
    StructuredProduct,
)
from .intent import ScoringWeights, SpecConstraint, UserIntent
from .money import Money, parse_amount
from .results import (
    DisqualifiedCandidate,
    RankedCandidate,
    RankResult,
    SelectionResult,
    StageError,
    Violation,
    ViolationCode,
    FlagCode,
)

__all__ = [
    "CandidateSet", "Decision", "DecisionResult", "Reason", "ReasonCode", "Condition", "DisqualifiedCandidate", "FactConflict", "FactVerification", "Money",
    "Observation", "PageInput", "ProductFact", "RankResult", "RankedCandidate", "RejectedFact",
    "ScoringWeights", "SelectionResult", "SpecConstraint", "StageError", "StructuredProduct",
    "UserIntent", "Violation", "ViolationCode", "FlagCode", "parse_amount",
]
