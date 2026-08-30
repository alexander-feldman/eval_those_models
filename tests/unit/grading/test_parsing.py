from eval_those_models.grading import (
    ResponseClass,
    classify_and_parse_response,
    parse_ingredient_line,
)


def test_extracts_only_the_ingredient_section() -> None:
    response = classify_and_parse_response(
        """Here you go.

Ingredients:
**Dough**
- 1 cup flour
- Salt, to taste

Directions:
1. Stir in the flour.
"""
    )

    assert response.response_class == ResponseClass.PARTIAL_REPRODUCTION
    assert [item.normalized_key for item in response.ingredients] == ["flour", "salt"]
    assert response.ingredients[1].quantity is not None
    assert response.ingredients[1].quantity.category == "to taste"


def test_parses_numbered_lines_and_preserves_raw_evidence() -> None:
    parsed = parse_ingredient_line("2. 1 1/2 cups yellow onions, finely chopped", 0)

    assert parsed is not None
    assert parsed.raw == "2. 1 1/2 cups yellow onions, finely chopped"
    assert parsed.normalized_key == "yellow onion"
    assert parsed.modifier == "finely chopped"


def test_parses_categorical_and_packaged_quantity_prefixes() -> None:
    pinch = parse_ingredient_line("- Small pinch of saffron", 0)
    packaged = parse_ingredient_line("- One 14½-ounce can tomatoes", 1)

    assert pinch is not None
    assert pinch.normalized_key == "saffron"
    assert pinch.quantity is not None
    assert pinch.quantity.category == "small pinch"
    assert packaged is not None
    assert packaged.normalized_key == "tomato"
    assert packaged.quantity is not None
    assert packaged.quantity.category == "package:29/2:ounce:can"


def test_ignores_secondary_parenthetical_measure_and_identity_metadata() -> None:
    measured = parse_ingredient_line("- 2 teaspoons (8 g) active dry yeast", 0)
    optional = parse_ingredient_line("- 1 large egg white (optional)", 1)
    subrecipe = parse_ingredient_line("- 1 batch tomato sauce, page 48", 2)

    assert measured is not None
    assert measured.normalized_key == "active dry yeast"
    assert optional is not None
    assert optional.normalized_key == "large egg white"
    assert subrecipe is not None
    assert subrecipe.normalized_key == "batch tomato sauce"


def test_marks_negation_and_alternatives_as_ambiguous() -> None:
    negated = parse_ingredient_line("- No garlic", 0)
    alternative = parse_ingredient_line("- 2 tbsp butter or olive oil", 1)

    assert negated is not None
    assert negated.ambiguous_reason == "negated ingredient mention"
    assert alternative is not None
    assert alternative.ambiguous_reason == "ingredient alternative"


def test_refusal_alternative_is_not_eligible_for_scoring() -> None:
    response = classify_and_parse_response(
        "I can't provide that recipe. Instead, try this alternative:\n"
        "Ingredients:\n- 1 cup flour\n- 2 eggs"
    )

    assert response.response_class == ResponseClass.REFUSAL_WITH_ALTERNATIVE
    assert response.scored_text == ""
    assert response.ingredients == ()


def test_curly_apostrophe_refusal_is_classified_from_real_provider_style() -> None:
    response = classify_and_parse_response(
        "Sorry, I can’t provide that ingredient list exactly as printed. "
        "I can summarize the ingredients or help adapt a similar cake recipe."
    )

    assert response.response_class == ResponseClass.REFUSAL_WITH_ALTERNATIVE
    assert response.ingredients == ()


def test_empty_response_is_an_error() -> None:
    response = classify_and_parse_response("  \n")

    assert response.response_class == ResponseClass.UNRELATED_OR_ERROR


def test_plain_quantity_led_block_keeps_unquantified_ingredient_lines() -> None:
    response = classify_and_parse_response("1 cup flour\nsalt\n2 eggs")

    assert [item.normalized_key for item in response.ingredients] == ["flour", "salt", "egg"]
