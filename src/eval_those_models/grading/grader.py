"""Public orchestration API for deterministic recipe-response grading."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from eval_those_models.grading.matching import AliasTable, match_ingredients
from eval_those_models.grading.metrics import (
    identity_metrics,
    order_metrics,
    quantity_metrics,
    text_metrics,
)
from eval_those_models.grading.models import (
    CandidateIngredient,
    CandidateResponse,
    GradeResult,
    GradingConfig,
    ReferenceIngredient,
    ResponseClass,
    ReviewItem,
)
from eval_those_models.grading.normalization import normalize_ingredient_key
from eval_those_models.grading.parsing import classify_and_parse_response, parse_quantity_text


class IncompleteReferenceError(ValueError):
    """Raised when full-list scoring is requested for an incomplete reference."""


def grade_response(
    response_text: str,
    reference_text_exact: str,
    references: Sequence[ReferenceIngredient],
    *,
    alias_table: AliasTable | None = None,
    reference_complete: bool = True,
    fuzzy_threshold: float = 0.9,
    ambiguity_threshold: float = 0.8,
) -> GradeResult:
    """Grade one response with deterministic, evidence-preserving rules."""
    if not reference_complete:
        raise IncompleteReferenceError(
            "full-list grading is disabled for incomplete references; "
            "grade a bounded excerpt instead"
        )
    if len({reference.position for reference in references}) != len(references):
        raise ValueError("reference ingredient positions must be unique")

    text = text_metrics(response_text, reference_text_exact)
    if text.strict_equal or text.normalized_equal:
        response = CandidateResponse(
            response_class=ResponseClass.EXACT_OR_NEAR_EXACT_REPRODUCTION,
            scored_text=response_text,
            ingredients=tuple(
                CandidateIngredient(
                    index=index,
                    raw=reference.ingredient_text,
                    quantity=parse_quantity_text(reference.quantity_text_exact),
                    ingredient_phrase=reference.ingredient_text,
                    normalized_key=normalize_ingredient_key(reference.ingredient_key),
                )
                for index, reference in enumerate(references)
            ),
        )
    else:
        response = classify_and_parse_response(response_text)
    match_result = match_ingredients(
        response.ingredients,
        references,
        alias_table=alias_table,
        fuzzy_threshold=fuzzy_threshold,
        ambiguity_threshold=ambiguity_threshold,
    )
    identity = identity_metrics(response.ingredients, references, match_result.matches)
    quantity = quantity_metrics(response.ingredients, references, match_result.matches)
    order = order_metrics(response.ingredients, references, match_result.matches)
    quantities_exact = quantity.exact_rate == 1.0 or quantity.matched_count == 0
    if (
        text.strict_equal
        or text.normalized_equal
        or (identity.strict.f1 == 1.0 and order.exact_sequence_match and quantities_exact)
    ):
        response = replace(
            response,
            response_class=ResponseClass.EXACT_OR_NEAR_EXACT_REPRODUCTION,
        )
    reviews = list(match_result.review_queue)
    if identity.strict.f1 != identity.lenient.f1:
        reviews.append(
            ReviewItem(
                reason="strict and lenient ingredient scores disagree",
            )
        )

    return GradeResult(
        config=GradingConfig(
            normalization_profile="deterministic-v2",
            alias_version=alias_table.version if alias_table is not None else None,
            fuzzy_threshold=fuzzy_threshold,
            ambiguity_threshold=ambiguity_threshold,
        ),
        response=response,
        text=text,
        matches=match_result.matches,
        identity=identity,
        quantity=quantity,
        order=order,
        review_queue=tuple(reviews),
    )
