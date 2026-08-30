"""Conservative one-to-one ingredient matching."""

from __future__ import annotations

import re
from collections import defaultdict, deque
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher

from eval_those_models.grading.models import (
    CandidateIngredient,
    IngredientMatch,
    MatchMethod,
    ReferenceIngredient,
    ReviewItem,
)
from eval_those_models.grading.normalization import normalize_ingredient_key
from eval_those_models.grading.parsing import parse_ingredient_line

_LEADING_MEASURE = ("tsp ", "tbsp ", "tbs ", "teaspoon ", "tablespoon ")


def _clean_reference_variant(text: str) -> str:
    normalized = normalize_ingredient_key(text)
    normalized = re.sub(r"\s+optional$", "", normalized)
    normalized = re.sub(r"\s+page\s+\d+$", "", normalized)
    return normalized


def _reference_variants(reference: ReferenceIngredient) -> set[str]:
    variants = {_clean_reference_variant(reference.ingredient_key)}
    base_ingredient = reference.ingredient_text.partition(",")[0]
    variants.add(_clean_reference_variant(base_ingredient))
    for value in (reference.ingredient_key, reference.ingredient_text):
        parsed = parse_ingredient_line(value, 0)
        if parsed is not None and parsed.ambiguous_reason != "negated ingredient mention":
            variants.add(_clean_reference_variant(parsed.normalized_key))
    expanded = set(variants)
    for variant in variants:
        for measure in _LEADING_MEASURE:
            if variant.startswith(measure):
                expanded.add(variant.removeprefix(measure))
    return {variant for variant in expanded if variant}


def _reference_identity_variants(reference: ReferenceIngredient) -> set[str]:
    variants = set(_reference_variants(reference))
    for value in (reference.ingredient_key, reference.ingredient_text):
        parsed = parse_ingredient_line(value, 0)
        if parsed is not None and parsed.identity_key:
            variants.add(_clean_reference_variant(parsed.identity_key))
    return variants


def _matching_key(candidate: CandidateIngredient) -> str:
    return candidate.identity_key or candidate.normalized_key


def _qualifier_values(candidate: CandidateIngredient) -> dict[str, str]:
    return {qualifier.kind: qualifier.value for qualifier in candidate.qualifiers}


def _reference_qualifier_values(reference: ReferenceIngredient) -> dict[str, str]:
    for value in (reference.ingredient_text, reference.ingredient_key):
        parsed = parse_ingredient_line(value, 0)
        if parsed is not None and parsed.qualifiers:
            return _qualifier_values(parsed)
    return {}


@dataclass(frozen=True)
class AliasTable:
    """Versioned aliases keyed by the canonical ground-truth ingredient key."""

    version: str
    aliases: Mapping[str, Collection[str]]


@dataclass(frozen=True)
class MatchResult:
    matches: tuple[IngredientMatch, ...]
    review_queue: tuple[ReviewItem, ...]


def ingredient_similarity(candidate_key: str, reference_key: str) -> float:
    """Return a conservative lexical similarity without semantic inference."""
    candidate_tokens = set(candidate_key.split())
    reference_tokens = set(reference_key.split())
    if not candidate_tokens or not reference_tokens:
        return 0.0
    overlap = len(candidate_tokens & reference_tokens)
    token_f1 = 2 * overlap / (len(candidate_tokens) + len(reference_tokens))
    sequence = SequenceMatcher(None, candidate_key, reference_key, autojunk=False).ratio()
    return max(token_f1, sequence)


def match_ingredients(
    candidates: Sequence[CandidateIngredient],
    references: Sequence[ReferenceIngredient],
    *,
    alias_table: AliasTable | None = None,
    fuzzy_threshold: float = 0.9,
    ambiguity_threshold: float = 0.8,
    tie_margin: float = 0.025,
) -> MatchResult:
    """Match candidates to references once each, preferring auditable exact rules."""
    if not 0 <= ambiguity_threshold <= fuzzy_threshold <= 1:
        raise ValueError("matching thresholds must satisfy 0 <= ambiguity <= fuzzy <= 1")
    if tie_margin < 0:
        raise ValueError("tie_margin must be non-negative")

    reference_variants = {
        reference.position: _reference_variants(reference) for reference in references
    }
    reference_identity_variants = {
        reference.position: _reference_identity_variants(reference) for reference in references
    }
    normalized_references = {
        reference.position: normalize_ingredient_key(reference.ingredient_key)
        for reference in references
    }
    normalized_aliases: dict[str, set[str]] = defaultdict(set)
    if alias_table is not None:
        for canonical, aliases in alias_table.aliases.items():
            canonical_key = normalize_ingredient_key(canonical)
            normalized_aliases[canonical_key].update(
                normalize_ingredient_key(alias) for alias in aliases
            )

    unmatched_candidates = {candidate.index for candidate in candidates}
    unmatched_references = {reference.position for reference in references}
    candidate_by_index = {candidate.index: candidate for candidate in candidates}
    reference_by_position = {reference.position: reference for reference in references}
    matches: list[IngredientMatch] = []
    reviews: list[ReviewItem] = []

    def record(
        candidate: CandidateIngredient, reference: ReferenceIngredient, method: MatchMethod
    ) -> None:
        matches.append(
            IngredientMatch(
                candidate_index=candidate.index,
                reference_position=reference.position,
                method=method,
                score=1.0,
                candidate_evidence=candidate.raw,
                reference_evidence=reference.ingredient_text,
            )
        )
        unmatched_candidates.remove(candidate.index)
        unmatched_references.remove(reference.position)
        candidate_qualifiers = _qualifier_values(candidate)
        reference_qualifiers = _reference_qualifier_values(reference)
        shared_kinds = candidate_qualifiers.keys() & reference_qualifiers.keys()
        if any(candidate_qualifiers[kind] != reference_qualifiers[kind] for kind in shared_kinds):
            qualifier_reason = "ingredient qualifiers conflict"
        elif reference_qualifiers.keys() - candidate_qualifiers.keys():
            qualifier_reason = "ingredient qualifier missing"
        elif candidate_qualifiers.keys() - reference_qualifiers.keys():
            qualifier_reason = "ingredient qualifier added"
        else:
            qualifier_reason = None
        if qualifier_reason is not None:
            reviews.append(
                ReviewItem(
                    reason=qualifier_reason,
                    candidate_evidence=candidate.raw,
                    reference_evidence=(reference.ingredient_text,),
                )
            )

    # Match duplicate keys in stable order rather than collapsing them into a set.
    exact_positions: dict[str, deque[int]] = defaultdict(deque)
    for reference in references:
        for variant in reference_variants[reference.position]:
            exact_positions[variant].append(reference.position)
    for candidate in candidates:
        if candidate.ambiguous_reason == "negated ingredient mention":
            continue
        positions = exact_positions[candidate.normalized_key]
        while positions and positions[0] not in unmatched_references:
            positions.popleft()
        if positions:
            record(candidate, reference_by_position[positions.popleft()], MatchMethod.EXACT_KEY)

    identity_positions: dict[str, deque[int]] = defaultdict(deque)
    for reference in references:
        if reference.position not in unmatched_references:
            continue
        for variant in reference_identity_variants[reference.position]:
            identity_positions[variant].append(reference.position)
    for candidate in candidates:
        if (
            candidate.index not in unmatched_candidates
            or candidate.ambiguous_reason == "negated ingredient mention"
        ):
            continue
        positions = identity_positions[_matching_key(candidate)]
        while positions and positions[0] not in unmatched_references:
            positions.popleft()
        if positions:
            record(candidate, reference_by_position[positions.popleft()], MatchMethod.EXACT_KEY)

    for candidate in candidates:
        if candidate.index not in unmatched_candidates or candidate.ambiguous_reason is not None:
            continue
        possible = [
            reference
            for reference in references
            if reference.position in unmatched_references
            and _matching_key(candidate)
            in normalized_aliases[normalized_references[reference.position]]
        ]
        possible_keys = {normalized_references[reference.position] for reference in possible}
        if len(possible) == 1 or (possible and len(possible_keys) == 1):
            record(candidate, possible[0], MatchMethod.KNOWN_ALIAS)
        elif len(possible) > 1:
            reviews.append(
                ReviewItem(
                    reason="alias maps to multiple unmatched references",
                    candidate_evidence=candidate.raw,
                    reference_evidence=tuple(item.ingredient_text for item in possible),
                )
            )

    fuzzy_options: dict[int, list[tuple[float, int]]] = {}
    for candidate_index in sorted(unmatched_candidates):
        candidate = candidate_by_index[candidate_index]
        if candidate.ambiguous_reason is not None:
            reviews.append(
                ReviewItem(reason=candidate.ambiguous_reason, candidate_evidence=candidate.raw)
            )
            continue
        options = sorted(
            (
                (
                    max(
                        ingredient_similarity(_matching_key(candidate), reference_variant)
                        for reference_variant in reference_identity_variants[reference_position]
                    ),
                    reference_position,
                )
                for reference_position in unmatched_references
            ),
            reverse=True,
        )
        fuzzy_options[candidate_index] = options

    fuzzy_pairs: list[tuple[float, int, int]] = []
    ambiguous_candidates: set[int] = set()
    for candidate_index, options in fuzzy_options.items():
        if not options:
            continue
        best_score, best_position = options[0]
        second_score = options[1][0] if len(options) > 1 else 0.0
        if best_score >= ambiguity_threshold and best_score - second_score <= tie_margin:
            ambiguous_candidates.add(candidate_index)
            top_references = tuple(
                reference_by_position[position].ingredient_text
                for score, position in options
                if best_score - score <= tie_margin
            )
            reviews.append(
                ReviewItem(
                    reason="fuzzy match has competing references",
                    candidate_evidence=candidate_by_index[candidate_index].raw,
                    reference_evidence=top_references,
                )
            )
        elif best_score >= fuzzy_threshold:
            fuzzy_pairs.extend(
                (score, candidate_index, reference_position)
                for score, reference_position in options
                if score >= fuzzy_threshold
            )
        elif best_score >= ambiguity_threshold:
            ambiguous_candidates.add(candidate_index)
            reviews.append(
                ReviewItem(
                    reason="fuzzy match falls below the acceptance threshold",
                    candidate_evidence=candidate_by_index[candidate_index].raw,
                    reference_evidence=(reference_by_position[best_position].ingredient_text,),
                )
            )

    for score, candidate_index, reference_position in sorted(fuzzy_pairs, reverse=True):
        if (
            candidate_index not in unmatched_candidates
            or reference_position not in unmatched_references
        ):
            continue
        candidate = candidate_by_index[candidate_index]
        reference = reference_by_position[reference_position]
        matches.append(
            IngredientMatch(
                candidate_index=candidate_index,
                reference_position=reference_position,
                method=MatchMethod.CONSERVATIVE_FUZZY,
                score=score,
                candidate_evidence=candidate.raw,
                reference_evidence=reference.ingredient_text,
            )
        )
        unmatched_candidates.remove(candidate_index)
        unmatched_references.remove(reference_position)

    for candidate_index in sorted(unmatched_candidates):
        candidate = candidate_by_index[candidate_index]
        method = (
            MatchMethod.AMBIGUOUS
            if candidate_index in ambiguous_candidates
            else MatchMethod.UNMATCHED
        )
        matches.append(
            IngredientMatch(
                candidate_index=candidate_index,
                reference_position=None,
                method=method,
                score=0.0,
                candidate_evidence=candidate.raw,
                reference_evidence=None,
                reason=candidate.ambiguous_reason,
            )
        )
    for reference_position in sorted(unmatched_references):
        reference = reference_by_position[reference_position]
        matches.append(
            IngredientMatch(
                candidate_index=None,
                reference_position=reference_position,
                method=MatchMethod.UNMATCHED,
                score=0.0,
                candidate_evidence=None,
                reference_evidence=reference.ingredient_text,
            )
        )

    matches.sort(
        key=lambda match: (
            match.candidate_index is None,
            match.candidate_index if match.candidate_index is not None else 10**9,
            match.reference_position if match.reference_position is not None else 10**9,
        )
    )
    return MatchResult(matches=tuple(matches), review_queue=tuple(reviews))
