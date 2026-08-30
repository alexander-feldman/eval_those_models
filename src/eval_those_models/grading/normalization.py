"""Conservative text, ingredient, unit, and quantity normalization."""

from __future__ import annotations

import re
import unicodedata
from fractions import Fraction

from eval_those_models.grading.models import ParsedQuantity

_UNICODE_FRACTIONS = {
    "¼": "1/4",
    "½": "1/2",
    "¾": "3/4",
    "⅐": "1/7",
    "⅑": "1/9",
    "⅒": "1/10",
    "⅓": "1/3",
    "⅔": "2/3",
    "⅕": "1/5",
    "⅖": "2/5",
    "⅗": "3/5",
    "⅘": "4/5",
    "⅙": "1/6",
    "⅚": "5/6",
    "⅛": "1/8",
    "⅜": "3/8",
    "⅝": "5/8",
    "⅞": "7/8",
}

_UNIT_ALIASES = {
    "t": "teaspoon",
    "tsp": "teaspoon",
    "tsp.": "teaspoon",
    "teaspoon": "teaspoon",
    "teaspoons": "teaspoon",
    "tbsp": "tablespoon",
    "tbsp.": "tablespoon",
    "tbs": "tablespoon",
    "tbs.": "tablespoon",
    "tablespoon": "tablespoon",
    "tablespoons": "tablespoon",
    "c": "cup",
    "c.": "cup",
    "cup": "cup",
    "cups": "cup",
    "ml": "milliliter",
    "milliliter": "milliliter",
    "milliliters": "milliliter",
    "l": "liter",
    "liter": "liter",
    "liters": "liter",
    "g": "gram",
    "gram": "gram",
    "grams": "gram",
    "kg": "kilogram",
    "kilogram": "kilogram",
    "kilograms": "kilogram",
    "oz": "ounce",
    "oz.": "ounce",
    "ounce": "ounce",
    "ounces": "ounce",
    "lb": "pound",
    "lb.": "pound",
    "lbs": "pound",
    "lbs.": "pound",
    "pound": "pound",
    "pounds": "pound",
    "clove": "clove",
    "cloves": "clove",
    "can": "can",
    "cans": "can",
    "package": "package",
    "packages": "package",
    "stick": "stick",
    "sticks": "stick",
    "pinch": "pinch",
    "pinches": "pinch",
    "bottle": "bottle",
    "bottles": "bottle",
    "bunch": "bunch",
    "bunches": "bunch",
    "head": "head",
    "heads": "head",
    "jar": "jar",
    "jars": "jar",
    "packet": "packet",
    "packets": "packet",
    "piece": "piece",
    "pieces": "piece",
    "slice": "slice",
    "slices": "slice",
    "sprig": "sprig",
    "sprigs": "sprig",
    "stalk": "stalk",
    "stalks": "stalk",
}

_UNIT_FACTORS: dict[str, tuple[str, Fraction]] = {
    "teaspoon": ("us_volume", Fraction(1)),
    "tablespoon": ("us_volume", Fraction(3)),
    "cup": ("us_volume", Fraction(48)),
    "milliliter": ("metric_volume", Fraction(1)),
    "liter": ("metric_volume", Fraction(1000)),
    "gram": ("metric_mass", Fraction(1)),
    "kilogram": ("metric_mass", Fraction(1000)),
    "ounce": ("imperial_mass", Fraction(1)),
    "pound": ("imperial_mass", Fraction(16)),
}


def normalize_unicode_fractions(text: str) -> str:
    output: list[str] = []
    for character in text:
        replacement = _UNICODE_FRACTIONS.get(character)
        if replacement is None:
            output.append(character)
        else:
            if output and output[-1][-1:].isdigit():
                output.append(" ")
            output.append(replacement)
    return "".join(output).replace("⁄", "/")


def normalize_text(text: str) -> str:
    """Normalize layout without erasing quantity or ingredient differences."""
    text = normalize_unicode_fractions(text)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(lines).strip()


def _singularize_token(token: str) -> str:
    irregular = {
        "cheeses": "cheese",
        "halves": "half",
        "knives": "knife",
        "leaves": "leaf",
        "loaves": "loaf",
    }
    if token in irregular:
        return irregular[token]
    if len(token) > 4 and token.endswith("ies"):
        return f"{token[:-3]}y"
    if len(token) > 4 and token.endswith("oes"):
        return token[:-2]
    if len(token) > 4 and token.endswith(("ches", "shes", "xes", "zes")):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is")):
        return token[:-1]
    return token


def normalize_ingredient_key(text: str) -> str:
    text = normalize_text(text).casefold()
    text = text.replace("&", " and ")
    text = re.sub(r"[\u2010-\u2015-]", " ", text)
    text = re.sub(r"[^\w\s']", " ", text)
    tokens = (_singularize_token(token) for token in text.split())
    return " ".join(tokens)


def normalize_unit(unit: str | None) -> str | None:
    if unit is None:
        return None
    return _UNIT_ALIASES.get(unit.casefold().strip())


def parse_number(text: str) -> Fraction:
    parts = normalize_unicode_fractions(text).strip().split()
    if len(parts) == 2:
        return Fraction(parts[0]) + Fraction(parts[1])
    return Fraction(parts[0])


def quantities_equivalent(first: ParsedQuantity | None, second: ParsedQuantity | None) -> bool:
    if first is None or second is None:
        return first is second
    if first.category is not None or second.category is not None:
        return first.category == second.category and first.value == second.value
    if first.value is None or second.value is None:
        return False

    first_unit = normalize_unit(first.unit)
    second_unit = normalize_unit(second.unit)
    if first_unit == second_unit:
        return _quantity_values_equivalent(first.value, second.value)
    if first_unit is None or second_unit is None:
        return False
    if first_unit not in _UNIT_FACTORS or second_unit not in _UNIT_FACTORS:
        return False

    first_dimension, first_factor = _UNIT_FACTORS[first_unit]
    second_dimension, second_factor = _UNIT_FACTORS[second_unit]
    if first_dimension != second_dimension:
        return False

    def scaled(
        value: Fraction | tuple[Fraction, Fraction], factor: Fraction
    ) -> Fraction | tuple[Fraction, Fraction]:
        if isinstance(value, tuple):
            return (value[0] * factor, value[1] * factor)
        return value * factor

    return _quantity_values_equivalent(
        scaled(first.value, first_factor), scaled(second.value, second_factor)
    )


def _quantity_values_equivalent(
    first: Fraction | tuple[Fraction, Fraction],
    second: Fraction | tuple[Fraction, Fraction],
) -> bool:
    if isinstance(first, tuple) and not isinstance(second, tuple):
        return first[0] <= second <= first[1]
    if isinstance(second, tuple) and not isinstance(first, tuple):
        return second[0] <= first <= second[1]
    return first == second
