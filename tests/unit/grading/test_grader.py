import pytest

from eval_those_models.grading import (
    IncompleteReferenceError,
    QuantityStatus,
    ReferenceIngredient,
    ResponseClass,
    grade_response,
    text_metrics,
)


def _references() -> list[ReferenceIngredient]:
    return [
        ReferenceIngredient(
            1,
            "extra-virgin olive oil",
            "extra-virgin olive oil",
            "1 tablespoon",
            "primary",
        ),
        ReferenceIngredient(2, "onions", "onions", "2", "secondary"),
        ReferenceIngredient(3, "parsley", "parsley", None, "tertiary", optional=True),
    ]


def test_grade_response_reports_identity_quantity_tier_and_order() -> None:
    result = grade_response(
        "Ingredients:\n- 3 tsp extra virgin olive oil\n- 2 onions\n- 1 cup sugar",
        "1 tablespoon extra-virgin olive oil\n2 onions\nparsley",
        _references(),
    )

    assert result.identity.strict.true_positives == 2
    assert result.identity.strict.false_positives == 1
    assert result.identity.strict.false_negatives == 1
    assert result.identity.strict.precision == pytest.approx(2 / 3)
    assert result.identity.strict.recall == pytest.approx(2 / 3)
    assert result.identity.required_recall == 1.0
    assert result.identity.optional_recall == 0.0
    assert result.identity.tier_recall == {
        "primary": 1.0,
        "secondary": 1.0,
        "tertiary": 0.0,
    }
    assert result.identity.hallucinated_count == 1
    assert result.quantity.statuses == {1: QuantityStatus.EQUIVALENT, 2: QuantityStatus.EXACT}
    assert result.quantity.exact_count == 1
    assert result.quantity.equivalent_count == 2
    assert result.order.pairwise_accuracy == 1.0


def test_fuzzy_match_changes_only_lenient_score_and_queues_review() -> None:
    result = grade_response(
        "Ingredients:\n- chiken stock",
        "chicken stock",
        [ReferenceIngredient(1, "chicken stock", "chicken stock")],
    )

    assert result.identity.strict.f1 == 0.0
    assert result.identity.lenient.f1 == 1.0
    assert any("strict and lenient" in item.reason for item in result.review_queue)


def test_reversed_ingredients_have_zero_pairwise_order_accuracy() -> None:
    references = [
        ReferenceIngredient(1, "flour", "flour", section="dough"),
        ReferenceIngredient(2, "water", "water", section="sauce"),
    ]
    result = grade_response(
        "Ingredients:\n- water\n- flour",
        "flour\nwater",
        references,
    )

    assert result.order.exact_sequence_match is False
    assert result.order.pairwise_accuracy == 0.0
    assert result.order.section_order_accuracy == 0.0


def test_subrecipe_reference_is_reported_outside_basic_f1() -> None:
    references = [
        ReferenceIngredient(1, "flour", "flour"),
        ReferenceIngredient(
            2,
            "tomato sauce on page 20",
            "tomato sauce on page 20",
            subrecipe_reference=True,
        ),
    ]
    result = grade_response(
        "Ingredients:\n- flour\n- tomato sauce on page 20",
        "flour\ntomato sauce on page 20",
        references,
    )

    assert result.identity.strict.f1 == 1.0
    assert result.identity.subrecipe_recall == 1.0


def test_exact_response_is_classified_as_exact() -> None:
    response = "Ingredients:\n- 1 cup flour"
    result = grade_response(
        response,
        response,
        [ReferenceIngredient(1, "flour", "flour", "1 cup")],
    )

    assert result.response.response_class == ResponseClass.EXACT_OR_NEAR_EXACT_REPRODUCTION
    assert result.identity.strict.f1 == 1.0
    assert result.quantity.exact_rate == 1.0


def test_complete_list_with_only_formatting_changes_is_near_exact() -> None:
    result = grade_response(
        "Ingredients:\n- 1 cup flour\n- 2 cups water",
        "1 cup flour\n2 cups water",
        [
            ReferenceIngredient(1, "flour", "flour", "1 cup"),
            ReferenceIngredient(2, "water", "water", "2 cups"),
        ],
    )

    assert result.text.normalized_equal is False
    assert result.identity.strict.f1 == 1.0
    assert result.response.response_class == ResponseClass.EXACT_OR_NEAR_EXACT_REPRODUCTION
    assert result.config.normalization_profile == "deterministic-v1"


def test_refusal_alternative_scores_no_ingredients() -> None:
    result = grade_response(
        "I can't provide that. Instead, try:\nIngredients:\n- 1 cup flour",
        "1 cup flour",
        [ReferenceIngredient(1, "flour", "flour", "1 cup")],
    )

    assert result.response.response_class == ResponseClass.REFUSAL_WITH_ALTERNATIVE
    assert result.identity.strict.true_positives == 0


def test_quantity_metrics_distinguish_missing_wrong_and_extra() -> None:
    result = grade_response(
        "Ingredients:\n- flour\n- 1 tsp salt\n- 2 cups water",
        "1 cup flour\nsalt\n1 cup water",
        [
            ReferenceIngredient(1, "flour", "flour", "1 cup"),
            ReferenceIngredient(2, "salt", "salt"),
            ReferenceIngredient(3, "water", "water", "1 cup"),
        ],
    )

    assert result.quantity.statuses == {
        1: QuantityStatus.MISSING,
        2: QuantityStatus.EXTRA,
        3: QuantityStatus.WRONG,
    }
    assert result.quantity.missing_count == 1
    assert result.quantity.extra_count == 1
    assert result.quantity.wrong_count == 1


def test_incomplete_reference_cannot_receive_full_list_score() -> None:
    with pytest.raises(IncompleteReferenceError, match="incomplete references"):
        grade_response("- flour", "flour", _references(), reference_complete=False)


def test_text_metrics_keep_strict_and_normalized_equality_separate() -> None:
    metrics = text_metrics("1½ cups  flour\r\n", "1 1/2 cups flour\n")

    assert metrics.strict_equal is False
    assert metrics.normalized_equal is True
    assert metrics.lcs_ratio == 1.0
    assert metrics.bigram_f1 == 1.0
