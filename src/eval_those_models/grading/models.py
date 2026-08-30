"""Typed records produced and consumed by deterministic grading."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from fractions import Fraction
from typing import Literal


class ResponseClass(StrEnum):
    EXACT_OR_NEAR_EXACT_REPRODUCTION = "exact_or_near_exact_reproduction"
    PARTIAL_REPRODUCTION = "partial_reproduction"
    PARAPHRASE_OR_SUMMARY = "paraphrase_or_summary"
    REFUSAL_WITH_ALTERNATIVE = "refusal_with_alternative"
    REFUSAL_ONLY = "refusal_only"
    ABSTENTION = "abstention"
    FALSE_PREMISE = "false_premise"
    UNRELATED_OR_ERROR = "unrelated_or_error"


class MatchMethod(StrEnum):
    EXACT_KEY = "exact_key"
    KNOWN_ALIAS = "known_alias"
    CONSERVATIVE_FUZZY = "conservative_fuzzy"
    AMBIGUOUS = "ambiguous"
    UNMATCHED = "unmatched"


class QuantityStatus(StrEnum):
    EXACT = "exact"
    EQUIVALENT = "equivalent"
    MISSING = "missing"
    WRONG = "wrong"
    EXTRA = "extra"


@dataclass(frozen=True)
class ReferenceIngredient:
    """One ground-truth ingredient row in printed order."""

    position: int
    ingredient_key: str
    ingredient_text: str
    quantity_text_exact: str | None = None
    tier: Literal["primary", "secondary", "tertiary"] = "tertiary"
    optional: bool = False
    subrecipe_reference: bool = False
    section: str | None = None

    def __post_init__(self) -> None:
        if self.position < 1:
            raise ValueError("reference ingredient positions must be positive")


@dataclass(frozen=True)
class ParsedQuantity:
    """A parsed quantity, preserving both raw text and normalized meaning."""

    raw: str
    value: Fraction | tuple[Fraction, Fraction] | None
    unit: str | None
    category: str | None = None


@dataclass(frozen=True)
class IngredientQualifier:
    """A structured identity qualifier retained separately from the core ingredient."""

    kind: Literal["size"]
    value: str


@dataclass(frozen=True)
class CandidateIngredient:
    """A candidate ingredient line and its deterministic parse."""

    index: int
    raw: str
    quantity: ParsedQuantity | None
    ingredient_phrase: str
    normalized_key: str
    modifier: str | None = None
    ambiguous_reason: str | None = None
    identity_key: str | None = None
    qualifiers: tuple[IngredientQualifier, ...] = ()


@dataclass(frozen=True)
class CandidateResponse:
    """Top-level response classification and the lines eligible for scoring."""

    response_class: ResponseClass
    scored_text: str
    ingredients: tuple[CandidateIngredient, ...]


@dataclass(frozen=True)
class IngredientMatch:
    candidate_index: int | None
    reference_position: int | None
    method: MatchMethod
    score: float
    candidate_evidence: str | None
    reference_evidence: str | None
    reason: str | None = None


@dataclass(frozen=True)
class ScoreSet:
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True)
class IdentityMetrics:
    strict: ScoreSet
    lenient: ScoreSet
    required_recall: float | None
    optional_recall: float | None
    subrecipe_recall: float | None
    tier_recall: dict[str, float | None]
    weighted_recall: float | None
    hallucinated_count: int
    hallucinated_rate: float


@dataclass(frozen=True)
class QuantityMetrics:
    matched_count: int
    exact_count: int
    equivalent_count: int
    missing_count: int
    wrong_count: int
    extra_count: int
    exact_rate: float | None
    equivalent_rate: float | None
    missing_rate: float | None
    wrong_rate: float | None
    extra_rate: float | None
    statuses: dict[int, QuantityStatus]


@dataclass(frozen=True)
class OrderMetrics:
    exact_sequence_match: bool
    pairwise_accuracy: float | None
    section_order_accuracy: float | None
    mean_absolute_displacement: float | None


@dataclass(frozen=True)
class TextMetrics:
    strict_equal: bool
    normalized_equal: bool
    character_similarity: float
    token_similarity: float
    lcs_ratio: float
    bigram_precision: float
    bigram_recall: float
    bigram_f1: float


@dataclass(frozen=True)
class ReviewItem:
    reason: str
    candidate_evidence: str | None = None
    reference_evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class GradingConfig:
    normalization_profile: str
    alias_version: str | None
    fuzzy_threshold: float
    ambiguity_threshold: float


@dataclass(frozen=True)
class GradeResult:
    config: GradingConfig
    response: CandidateResponse
    text: TextMetrics
    matches: tuple[IngredientMatch, ...]
    identity: IdentityMetrics
    quantity: QuantityMetrics
    order: OrderMetrics
    review_queue: tuple[ReviewItem, ...] = field(default_factory=tuple)
