import pytest

from eval_those_models.dataset.importer import ValidationError, complexity_score, parse_bool


@pytest.mark.parametrize(
    ("ingredient_count", "expected"),
    [(1, 1), (7, 1), (8, 2), (10, 2), (11, 3), (14, 3), (15, 4), (18, 4), (19, 5)],
)
def test_complexity_score_bins(ingredient_count: int, expected: int) -> None:
    assert complexity_score(ingredient_count) == expected


@pytest.mark.parametrize(("value", "expected"), [("true", 1), ("FALSE", 0), (" True ", 1)])
def test_parse_bool(value: str, expected: int) -> None:
    assert parse_bool(value, "enabled", "recipe-1") == expected


def test_parse_bool_rejects_an_unknown_value() -> None:
    with pytest.raises(ValidationError, match="must be true or false"):
        parse_bool("yes", "enabled", "recipe-1")
