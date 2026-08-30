from fractions import Fraction

from eval_those_models.grading import (
    normalize_ingredient_key,
    parse_quantity_text,
    quantities_equivalent,
)


def test_ingredient_normalization_is_conservative() -> None:
    assert normalize_ingredient_key("Extra-Virgin Olive Oils") == "extra virgin olive oil"
    assert normalize_ingredient_key("olive oil") != normalize_ingredient_key("vegetable oil")
    assert normalize_ingredient_key("salt") != normalize_ingredient_key("kosher salt")
    assert normalize_ingredient_key("peaches") == "peach"
    assert normalize_ingredient_key("bay leaves") == "bay leaf"
    assert normalize_ingredient_key("cheeses") == "cheese"


def test_parse_mixed_unicode_fraction_and_unit() -> None:
    quantity = parse_quantity_text("1½ tablespoons")

    assert quantity is not None
    assert quantity.value == Fraction(3, 2)
    assert quantity.unit == "tablespoon"


def test_parse_numeric_range() -> None:
    quantity = parse_quantity_text("1–2 cups")

    assert quantity is not None
    assert quantity.value == (Fraction(1), Fraction(2))
    assert quantity.unit == "cup"


def test_scalar_quantity_within_reference_range_is_equivalent() -> None:
    assert quantities_equivalent(parse_quantity_text("3"), parse_quantity_text("2 to 3"))
    assert not quantities_equivalent(parse_quantity_text("4"), parse_quantity_text("2 to 3"))


def test_safe_units_are_numerically_equivalent() -> None:
    assert quantities_equivalent(parse_quantity_text("3 tsp"), parse_quantity_text("1 tbsp"))
    assert not quantities_equivalent(parse_quantity_text("1 cup"), parse_quantity_text("1 gram"))


def test_categorical_quantities_are_not_forced_to_numbers() -> None:
    first = parse_quantity_text("to taste")
    second = parse_quantity_text("to taste")

    assert first is not None
    assert first.value is None
    assert first.category == "to taste"
    assert quantities_equivalent(first, second)


def test_packaged_quantity_preserves_container_size() -> None:
    first = parse_quantity_text("One 14½-ounce can")
    same = parse_quantity_text("1 14 1/2-oz can")
    different = parse_quantity_text("One 28-ounce can")
    different_count = parse_quantity_text("2 14½-ounce cans")

    assert first is not None
    assert first.unit == "can"
    assert quantities_equivalent(first, same)
    assert not quantities_equivalent(first, different)
    assert not quantities_equivalent(first, different_count)
