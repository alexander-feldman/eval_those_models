"""Deterministic text, identity, quantity, and order metrics."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from difflib import SequenceMatcher
from typing import cast

from eval_those_models.grading.models import (
    CandidateIngredient,
    IdentityMetrics,
    IngredientMatch,
    MatchMethod,
    OrderMetrics,
    QuantityMetrics,
    QuantityStatus,
    ReferenceIngredient,
    ScoreSet,
    TextMetrics,
)
from eval_those_models.grading.normalization import normalize_text, quantities_equivalent
from eval_those_models.grading.parsing import parse_quantity_text

_STRICT_METHODS = {MatchMethod.EXACT_KEY, MatchMethod.KNOWN_ALIAS}
_LENIENT_METHODS = _STRICT_METHODS | {MatchMethod.CONSERVATIVE_FUZZY}
_TIER_WEIGHTS = {"primary": 5, "secondary": 2, "tertiary": 1}


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _score_set(true_positives: int, candidate_count: int, reference_count: int) -> ScoreSet:
    false_positives = candidate_count - true_positives
    false_negatives = reference_count - true_positives
    precision = true_positives / candidate_count if candidate_count else 0.0
    recall = true_positives / reference_count if reference_count else 0.0
    return ScoreSet(
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
        f1=_f1(precision, recall),
    )


def _ngram_metrics(
    candidate: list[str], reference: list[str], n: int
) -> tuple[float, float, float]:
    def ngrams(tokens: list[str]) -> Counter[tuple[str, ...]]:
        return Counter(tuple(tokens[index : index + n]) for index in range(len(tokens) - n + 1))

    candidate_grams = ngrams(candidate)
    reference_grams = ngrams(reference)
    overlap = sum((candidate_grams & reference_grams).values())
    candidate_total = sum(candidate_grams.values())
    reference_total = sum(reference_grams.values())
    precision = overlap / candidate_total if candidate_total else 0.0
    recall = overlap / reference_total if reference_total else 0.0
    return precision, recall, _f1(precision, recall)


def _lcs_length(first: Sequence[str], second: Sequence[str]) -> int:
    if len(first) > len(second):
        first, second = second, first
    previous = [0] * (len(first) + 1)
    for second_item in second:
        current = [0]
        for index, first_item in enumerate(first, start=1):
            if first_item == second_item:
                current.append(previous[index - 1] + 1)
            else:
                current.append(max(current[-1], previous[index]))
        previous = current
    return previous[-1]


def text_metrics(candidate: str, reference: str) -> TextMetrics:
    candidate_normalized = normalize_text(candidate)
    reference_normalized = normalize_text(reference)
    candidate_tokens = candidate_normalized.casefold().split()
    reference_tokens = reference_normalized.casefold().split()
    lcs_denominator = max(len(candidate_tokens), len(reference_tokens))
    bigram_precision, bigram_recall, bigram_f1 = _ngram_metrics(
        candidate_tokens, reference_tokens, 2
    )
    return TextMetrics(
        strict_equal=candidate == reference,
        normalized_equal=candidate_normalized == reference_normalized,
        character_similarity=SequenceMatcher(
            None, candidate_normalized, reference_normalized, autojunk=False
        ).ratio(),
        token_similarity=SequenceMatcher(
            None, candidate_tokens, reference_tokens, autojunk=False
        ).ratio(),
        lcs_ratio=(
            _lcs_length(candidate_tokens, reference_tokens) / lcs_denominator
            if lcs_denominator
            else 1.0
        ),
        bigram_precision=bigram_precision,
        bigram_recall=bigram_recall,
        bigram_f1=bigram_f1,
    )


def identity_metrics(
    candidates: Sequence[CandidateIngredient],
    references: Sequence[ReferenceIngredient],
    matches: Sequence[IngredientMatch],
) -> IdentityMetrics:
    reference_by_position = {reference.position: reference for reference in references}
    accepted = [
        match
        for match in matches
        if match.candidate_index is not None and match.reference_position is not None
    ]
    subrecipe_candidates = {
        match.candidate_index
        for match in accepted
        if reference_by_position[cast(int, match.reference_position)].subrecipe_reference
    }
    ordinary_references = {
        reference.position for reference in references if not reference.subrecipe_reference
    }
    ordinary_candidate_count = len(candidates) - len(subrecipe_candidates)

    def positions(methods: set[MatchMethod]) -> set[int]:
        return {
            match.reference_position
            for match in accepted
            if match.method in methods and match.reference_position in ordinary_references
        }

    strict_positions = positions(_STRICT_METHODS)
    lenient_positions = positions(_LENIENT_METHODS)
    strict = _score_set(len(strict_positions), ordinary_candidate_count, len(ordinary_references))
    lenient = _score_set(len(lenient_positions), ordinary_candidate_count, len(ordinary_references))

    required_positions = {
        reference.position
        for reference in references
        if not reference.optional and not reference.subrecipe_reference
    }
    optional_positions = {
        reference.position
        for reference in references
        if reference.optional and not reference.subrecipe_reference
    }
    subrecipe_positions = {
        reference.position for reference in references if reference.subrecipe_reference
    }
    all_lenient_positions = {
        match.reference_position for match in accepted if match.method in _LENIENT_METHODS
    }

    tier_recall: dict[str, float | None] = {}
    for tier in _TIER_WEIGHTS:
        tier_positions = {
            reference.position
            for reference in references
            if reference.tier == tier and not reference.subrecipe_reference
        }
        tier_recall[tier] = _safe_ratio(
            len(tier_positions & lenient_positions), len(tier_positions)
        )

    weighted_total = sum(
        _TIER_WEIGHTS[reference.tier]
        for reference in references
        if not reference.subrecipe_reference
    )
    weighted_matched = sum(
        _TIER_WEIGHTS[reference_by_position[position].tier] for position in lenient_positions
    )

    return IdentityMetrics(
        strict=strict,
        lenient=lenient,
        required_recall=_safe_ratio(
            len(required_positions & lenient_positions), len(required_positions)
        ),
        optional_recall=_safe_ratio(
            len(optional_positions & lenient_positions), len(optional_positions)
        ),
        subrecipe_recall=_safe_ratio(
            len(subrecipe_positions & all_lenient_positions), len(subrecipe_positions)
        ),
        tier_recall=tier_recall,
        weighted_recall=_safe_ratio(weighted_matched, weighted_total),
        hallucinated_count=strict.false_positives,
        hallucinated_rate=(
            strict.false_positives / ordinary_candidate_count if ordinary_candidate_count else 0.0
        ),
    )


def quantity_metrics(
    candidates: Sequence[CandidateIngredient],
    references: Sequence[ReferenceIngredient],
    matches: Sequence[IngredientMatch],
) -> QuantityMetrics:
    candidate_by_index = {candidate.index: candidate for candidate in candidates}
    reference_by_position = {reference.position: reference for reference in references}
    statuses: dict[int, QuantityStatus] = {}

    for match in matches:
        if (
            match.method not in _LENIENT_METHODS
            or match.candidate_index is None
            or match.reference_position is None
        ):
            continue
        candidate_quantity = candidate_by_index[match.candidate_index].quantity
        reference = reference_by_position[match.reference_position]
        reference_quantity = parse_quantity_text(reference.quantity_text_exact)

        if candidate_quantity is None and reference_quantity is None:
            status = QuantityStatus.EXACT
        elif candidate_quantity is None:
            status = QuantityStatus.MISSING
        elif reference_quantity is None:
            status = QuantityStatus.EXTRA
        elif (
            normalize_text(candidate_quantity.raw).casefold()
            == normalize_text(reference.quantity_text_exact or "").casefold()
        ):
            status = QuantityStatus.EXACT
        elif quantities_equivalent(candidate_quantity, reference_quantity):
            status = QuantityStatus.EQUIVALENT
        else:
            status = QuantityStatus.WRONG
        statuses[reference.position] = status

    matched_count = len(statuses)
    exact_count = sum(status == QuantityStatus.EXACT for status in statuses.values())
    equivalent_only = sum(status == QuantityStatus.EQUIVALENT for status in statuses.values())
    missing_count = sum(status == QuantityStatus.MISSING for status in statuses.values())
    wrong_count = sum(status == QuantityStatus.WRONG for status in statuses.values())
    extra_count = sum(status == QuantityStatus.EXTRA for status in statuses.values())
    equivalent_count = exact_count + equivalent_only
    return QuantityMetrics(
        matched_count=matched_count,
        exact_count=exact_count,
        equivalent_count=equivalent_count,
        missing_count=missing_count,
        wrong_count=wrong_count,
        extra_count=extra_count,
        exact_rate=_safe_ratio(exact_count, matched_count),
        equivalent_rate=_safe_ratio(equivalent_count, matched_count),
        missing_rate=_safe_ratio(missing_count, matched_count),
        wrong_rate=_safe_ratio(wrong_count, matched_count),
        extra_rate=_safe_ratio(extra_count, matched_count),
        statuses=statuses,
    )


def order_metrics(
    candidates: Sequence[CandidateIngredient],
    references: Sequence[ReferenceIngredient],
    matches: Sequence[IngredientMatch],
) -> OrderMetrics:
    accepted = sorted(
        (
            match
            for match in matches
            if match.method in _LENIENT_METHODS
            and match.candidate_index is not None
            and match.reference_position is not None
        ),
        key=lambda match: match.candidate_index if match.candidate_index is not None else -1,
    )
    reference_sequence = [cast(int, match.reference_position) for match in accepted]
    pair_count = len(reference_sequence) * (len(reference_sequence) - 1) // 2
    concordant = sum(
        reference_sequence[first] < reference_sequence[second]
        for first in range(len(reference_sequence))
        for second in range(first + 1, len(reference_sequence))
    )
    displacement = [
        abs((match.candidate_index or 0) + 1 - (match.reference_position or 0))
        for match in accepted
    ]
    exact_sequence = len(accepted) == len(candidates) == len(references) and reference_sequence == [
        reference.position for reference in references
    ]
    reference_by_position = {reference.position: reference for reference in references}
    ordered_sections = dict.fromkeys(
        reference.section for reference in references if reference.section is not None
    )
    section_order = {section: index for index, section in enumerate(ordered_sections)}
    matched_sections: list[str] = []
    for position in reference_sequence:
        section = reference_by_position[position].section
        if section is not None:
            matched_sections.append(section)
    section_pairs = [
        (first, second)
        for first in range(len(matched_sections))
        for second in range(first + 1, len(matched_sections))
        if matched_sections[first] != matched_sections[second]
    ]
    section_concordant = sum(
        section_order[matched_sections[first]] < section_order[matched_sections[second]]
        for first, second in section_pairs
    )
    return OrderMetrics(
        exact_sequence_match=exact_sequence,
        pairwise_accuracy=concordant / pair_count if pair_count else None,
        section_order_accuracy=(section_concordant / len(section_pairs) if section_pairs else None),
        mean_absolute_displacement=(
            sum(displacement) / len(displacement) if displacement else None
        ),
    )
