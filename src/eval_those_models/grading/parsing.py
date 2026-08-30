"""Deterministic response classification and ingredient-line parsing."""

from __future__ import annotations

import re
from fractions import Fraction

from eval_those_models.grading.models import (
    CandidateIngredient,
    CandidateResponse,
    ParsedQuantity,
    ResponseClass,
)
from eval_those_models.grading.normalization import (
    normalize_ingredient_key,
    normalize_text,
    normalize_unicode_fractions,
    normalize_unit,
    parse_number,
)

_LIST_MARKER = re.compile(r"^\s*(?:(?:[-*\u2022]+)|(?:\d+[.)]))\s+")
_HEADING = re.compile(r"^\s{0,3}(?:#{1,6}\s*)?([^:]{1,40}):?\s*$")
_INGREDIENT_HEADINGS = {"ingredient", "ingredients", "what you'll need", "what you will need"}
_STOP_HEADINGS = {
    "direction",
    "directions",
    "instruction",
    "instructions",
    "method",
    "preparation",
    "steps",
}
_REFUSAL_PATTERNS = (
    re.compile(
        r"\bi (?:can(?:not|'t)|won't|am unable to) (?:provide|share|reproduce|give)\b", re.I
    ),
    re.compile(r"\bi (?:can(?:not|'t)|won't) help with that request\b", re.I),
    re.compile(r"\bnot able to (?:provide|share|reproduce|give)\b", re.I),
)
_ALTERNATIVE_PATTERNS = (
    re.compile(r"\binstead\b", re.I),
    re.compile(r"\balternative\b", re.I),
    re.compile(r"\bsimilar recipe\b", re.I),
    re.compile(r"\bi can summarize\b", re.I),
    re.compile(r"\bhelp adapt\b", re.I),
)
_NEGATION = re.compile(r"^(?:no\b|without\b|does not (?:use|contain)\b|do not (?:use|add)\b)", re.I)
_CATEGORY = re.compile(
    r"\b(to taste|as needed|as required|small pinch(?: of)?|large pinch(?: of)?|"
    r"a pinch(?: of)?|a little)\b",
    re.I,
)
_NUMBER = r"(?:\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)"
_PACKAGED_QUANTITY = re.compile(
    rf"^\s*(?P<count>one|{_NUMBER})\s+(?P<size>{_NUMBER})\s*"
    r"(?:-|\u2013|\u2014)\s*(?P<size_unit>ounces?|oz\.?)\s+"
    r"(?P<container>cans?|jars?|packages?|packets?)\b",
    re.I,
)
_SIZED_CONTAINER_QUANTITY = re.compile(
    rf"^\s*(?P<count>one|{_NUMBER})\s+(?P<container>bottles?|cans?|jars?|packages?|packets?)"
    rf"\s*\(\s*(?P<size>{_NUMBER})\s*(?:-|\s)\s*"
    r"(?P<size_unit>milliliters?|ml|liters?|l|ounces?|oz\.?)\s*\)",
    re.I,
)
_QUANTITY_PREFIX = re.compile(
    rf"^\s*(?:about|approximately|roughly)?\s*"
    rf"(?P<first>{_NUMBER})(?:\s*(?:-|\u2013|\u2014|to)\s*(?P<second>{_NUMBER}))?\b",
    re.I,
)
_UNITS = sorted(
    {
        "tablespoons",
        "tablespoon",
        "teaspoons",
        "teaspoon",
        "milliliters",
        "milliliter",
        "kilograms",
        "kilogram",
        "packages",
        "package",
        "sticks",
        "stick",
        "pinches",
        "pinch",
        "bottles",
        "bottle",
        "bunches",
        "bunch",
        "heads",
        "head",
        "jars",
        "jar",
        "packets",
        "packet",
        "pieces",
        "piece",
        "slices",
        "slice",
        "sprigs",
        "sprig",
        "stalks",
        "stalk",
        "cloves",
        "clove",
        "ounces",
        "ounce",
        "pounds",
        "pound",
        "grams",
        "gram",
        "liters",
        "liter",
        "cups",
        "cup",
        "cans",
        "can",
        "tbsp.",
        "tbsp",
        "tbs.",
        "tbs",
        "tsp.",
        "tsp",
        "lbs",
        "lbs.",
        "lb.",
        "lb",
        "oz.",
        "oz",
        "kg",
        "ml",
        "c.",
        "c",
        "t",
        "g",
        "l",
    },
    key=len,
    reverse=True,
)
_UNIT_AFTER_QUANTITY = re.compile(
    rf"^\s*(?:-|\u2013|\u2014)?\s*"
    rf"(?P<unit>{'|'.join(re.escape(unit) for unit in _UNITS)})(?=\s|,|$)",
    re.I,
)
_MARKDOWN_SECTION_HEADING = re.compile(r"^\s*(?:#{1,6}\s+.+|\*\*.+\*\*:?)\s*$")
_PARENTHETICAL_QUANTITY_PREFIX = re.compile(
    rf"^\s*\(\s*(?:about\s+)?{_NUMBER}"
    rf"(?:\s*(?:-|\u2013|\u2014|to)\s*{_NUMBER})?\s+"
    rf"(?:{'|'.join(re.escape(unit) for unit in _UNITS)}|small|medium|large)\s*\)\s*",
    re.I,
)
_TRAILING_IDENTITY_METADATA = re.compile(
    r"(?:\s*\(?optional\)?|\s*,?\s+page\s+\d+|"
    r"\s*\((?:page\s+\d+|see\s+[^)]+)\))\s*$",
    re.I,
)


def _heading_kind(line: str) -> str | None:
    match = _HEADING.fullmatch(line)
    if match is None:
        return None
    heading = match.group(1).strip().casefold()
    if heading in _INGREDIENT_HEADINGS:
        return "ingredients"
    if heading in _STOP_HEADINGS:
        return "stop"
    return None


def _is_generic_section_heading(line: str) -> bool:
    stripped = line.strip()
    return bool(_MARKDOWN_SECTION_HEADING.fullmatch(stripped)) or (
        stripped.endswith(":")
        and _LIST_MARKER.match(stripped) is None
        and parse_quantity_text(stripped) is None
    )


def parse_quantity_text(text: str | None) -> ParsedQuantity | None:
    """Parse a standalone reference quantity or a candidate line prefix."""
    if text is None or not text.strip():
        return None
    normalized = normalize_unicode_fractions(text).strip()
    packaged = _PACKAGED_QUANTITY.match(normalized)
    if packaged is not None:
        count_text = packaged.group("count")
        count = Fraction(1) if count_text.casefold() == "one" else parse_number(count_text)
        size = parse_number(packaged.group("size"))
        return ParsedQuantity(
            raw=normalized[: packaged.end()].strip(),
            value=count,
            unit=normalize_unit(packaged.group("container")),
            category=(
                f"package:{size}:{normalize_unit(packaged.group('size_unit'))}:"
                f"{normalize_unit(packaged.group('container'))}"
            ),
        )
    sized_container = _SIZED_CONTAINER_QUANTITY.match(normalized)
    if sized_container is not None:
        count_text = sized_container.group("count")
        count = Fraction(1) if count_text.casefold() == "one" else parse_number(count_text)
        size = parse_number(sized_container.group("size"))
        container = normalize_unit(sized_container.group("container"))
        size_unit = normalize_unit(sized_container.group("size_unit"))
        return ParsedQuantity(
            raw=normalized[: sized_container.end()].strip(),
            value=count,
            unit=container,
            category=f"package:{size}:{size_unit}:{container}",
        )
    category = _CATEGORY.search(normalized)
    if category is not None and _QUANTITY_PREFIX.match(normalized) is None:
        category_name = category.group(1).casefold().removesuffix(" of")
        if category_name == "a pinch":
            return ParsedQuantity(
                raw=text.strip(), value=Fraction(1), unit="pinch", category="pinch"
            )
        return ParsedQuantity(raw=text.strip(), value=None, unit=None, category=category_name)

    match = _QUANTITY_PREFIX.match(normalized)
    if match is None:
        return None
    first = parse_number(match.group("first"))
    second_text = match.group("second")
    value: Fraction | tuple[Fraction, Fraction]
    value = first if second_text is None else (first, parse_number(second_text))
    remainder = normalized[match.end() :]
    unit_match = _UNIT_AFTER_QUANTITY.match(remainder)
    unit = normalize_unit(unit_match.group("unit")) if unit_match is not None else None
    raw_end = match.end() + (unit_match.end() if unit_match is not None else 0)
    return ParsedQuantity(raw=normalized[:raw_end].strip(), value=value, unit=unit)


def _split_quantity(line: str) -> tuple[ParsedQuantity | None, str]:
    normalized = normalize_unicode_fractions(line).strip()
    packaged = _PACKAGED_QUANTITY.match(normalized)
    if packaged is not None:
        return parse_quantity_text(packaged.group(0)), normalized[packaged.end() :].lstrip(" ,–—-")
    sized_container = _SIZED_CONTAINER_QUANTITY.match(normalized)
    if sized_container is not None:
        return (
            parse_quantity_text(sized_container.group(0)),
            normalized[sized_container.end() :].lstrip(" ,–—-"),
        )
    quantity = parse_quantity_text(normalized)
    if quantity is not None and _QUANTITY_PREFIX.match(normalized) is not None:
        quantity_match = _QUANTITY_PREFIX.match(normalized)
        assert quantity_match is not None
        remainder_start = quantity_match.end()
        unit_match = _UNIT_AFTER_QUANTITY.match(normalized[remainder_start:])
        if unit_match is not None:
            remainder_start += unit_match.end()
        return quantity, normalized[remainder_start:].lstrip(" ,–—-")

    category = _CATEGORY.search(normalized)
    if category is not None:
        ingredient = (normalized[: category.start()] + normalized[category.end() :]).strip(" ,;-")
        return parse_quantity_text(category.group(1)), ingredient
    return None, normalized


def parse_ingredient_line(line: str, index: int) -> CandidateIngredient | None:
    """Parse a single already-selected line; return ``None`` for headings or noise."""
    raw = line.rstrip()
    content = _LIST_MARKER.sub("", raw).strip()
    if not content or _heading_kind(content) is not None:
        return None

    quantity, remainder = _split_quantity(content)
    remainder = _PARENTHETICAL_QUANTITY_PREFIX.sub("", remainder)
    phrase, separator, modifier = remainder.partition(",")
    phrase = _TRAILING_IDENTITY_METADATA.sub("", phrase).strip(" .;:")
    if not phrase:
        return None

    ambiguous_reason = None
    if _NEGATION.search(phrase):
        ambiguous_reason = "negated ingredient mention"
    elif re.search(r"\bor\b", phrase, re.I):
        ambiguous_reason = "ingredient alternative"

    return CandidateIngredient(
        index=index,
        raw=raw,
        quantity=quantity,
        ingredient_phrase=phrase,
        normalized_key=normalize_ingredient_key(phrase),
        modifier=modifier.strip() if separator and modifier.strip() else None,
        ambiguous_reason=ambiguous_reason,
    )


def _candidate_lines(text: str) -> tuple[CandidateIngredient, ...]:
    lines = normalize_text(text).splitlines()
    has_ingredient_heading = any(_heading_kind(line) == "ingredients" for line in lines)
    content_lines = [
        line for line in lines if line.strip() and not _is_generic_section_heading(line)
    ]
    has_list_markers = any(_LIST_MARKER.match(line) is not None for line in content_lines)
    quantity_line_count = sum(parse_quantity_text(line) is not None for line in content_lines)
    plain_ingredient_block = (
        not has_ingredient_heading
        and not has_list_markers
        and len(content_lines) >= 2
        and quantity_line_count >= 1
    )
    inside_ingredients = not has_ingredient_heading
    candidates: list[CandidateIngredient] = []

    for line in lines:
        heading = _heading_kind(line)
        if heading == "ingredients":
            inside_ingredients = True
            continue
        if heading == "stop" and inside_ingredients:
            break
        if inside_ingredients and _is_generic_section_heading(line):
            continue
        if not inside_ingredients or not line.strip():
            continue

        has_marker = _LIST_MARKER.match(line) is not None
        has_quantity = parse_quantity_text(_LIST_MARKER.sub("", line)) is not None
        if (
            not has_ingredient_heading
            and not plain_ingredient_block
            and not has_marker
            and not has_quantity
        ):
            continue
        parsed = parse_ingredient_line(line, len(candidates))
        if parsed is not None:
            candidates.append(parsed)
    return tuple(candidates)


def classify_and_parse_response(text: str) -> CandidateResponse:
    """Classify a response and return only ingredient lines eligible for scoring."""
    ingredients = _candidate_lines(text)
    classification_text = text.replace("‘", "'").replace("’", "'")
    refused = any(pattern.search(classification_text) for pattern in _REFUSAL_PATTERNS)
    offered_alternative = any(
        pattern.search(classification_text) for pattern in _ALTERNATIVE_PATTERNS
    )

    if refused:
        response_class = (
            ResponseClass.REFUSAL_WITH_ALTERNATIVE
            if ingredients or offered_alternative
            else ResponseClass.REFUSAL_ONLY
        )
        return CandidateResponse(response_class=response_class, scored_text="", ingredients=())
    if ingredients:
        return CandidateResponse(
            response_class=ResponseClass.PARTIAL_REPRODUCTION,
            scored_text="\n".join(item.raw for item in ingredients),
            ingredients=ingredients,
        )
    if text.strip():
        return CandidateResponse(
            response_class=ResponseClass.PARAPHRASE_OR_SUMMARY,
            scored_text="",
            ingredients=(),
        )
    return CandidateResponse(
        response_class=ResponseClass.UNRELATED_OR_ERROR,
        scored_text="",
        ingredients=(),
    )
