from eval_those_models.grading import (
    AliasTable,
    CandidateIngredient,
    MatchMethod,
    ReferenceIngredient,
    match_ingredients,
    parse_ingredient_line,
)


def _candidate(line: str, index: int) -> CandidateIngredient:
    candidate = parse_ingredient_line(line, index)
    assert candidate is not None
    return candidate


def test_repeated_ingredients_are_matched_as_a_multiset() -> None:
    references = [
        ReferenceIngredient(1, "salt", "salt"),
        ReferenceIngredient(2, "salt", "salt"),
    ]
    candidates = [_candidate("- salt", 0), _candidate("- salt", 1)]

    result = match_ingredients(candidates, references)
    accepted = [match for match in result.matches if match.method == MatchMethod.EXACT_KEY]

    assert [(match.candidate_index, match.reference_position) for match in accepted] == [
        (0, 1),
        (1, 2),
    ]


def test_approved_alias_is_a_strict_match() -> None:
    references = [ReferenceIngredient(1, "garbanzo beans", "garbanzo beans")]
    aliases = AliasTable(version="v1", aliases={"garbanzo beans": {"chickpeas"}})

    result = match_ingredients([_candidate("- chickpeas", 0)], references, alias_table=aliases)

    assert result.matches[0].method == MatchMethod.KNOWN_ALIAS
    assert result.matches[0].reference_position == 1


def test_reference_modifier_variant_is_an_exact_identity_match() -> None:
    references = [
        ReferenceIngredient(
            1,
            "medium yellow onion diced",
            "medium yellow onion, diced",
        )
    ]

    result = match_ingredients([_candidate("- medium yellow onion", 0)], references)

    assert result.matches[0].method == MatchMethod.EXACT_KEY


def test_conservative_fuzzy_match_is_lenient_only() -> None:
    references = [ReferenceIngredient(1, "chicken stock", "chicken stock")]

    result = match_ingredients([_candidate("- chiken stock", 0)], references)

    assert result.matches[0].method == MatchMethod.CONSERVATIVE_FUZZY
    assert result.matches[0].score >= 0.9


def test_competing_fuzzy_matches_are_queued_for_review() -> None:
    references = [
        ReferenceIngredient(1, "black pepper", "black pepper"),
        ReferenceIngredient(2, "white pepper", "white pepper"),
    ]

    result = match_ingredients(
        [_candidate("- pepper", 0)],
        references,
        fuzzy_threshold=0.9,
        ambiguity_threshold=0.5,
    )

    assert result.matches[0].method == MatchMethod.AMBIGUOUS
    assert result.review_queue[0].reason == "fuzzy match has competing references"


def test_negated_ingredient_does_not_match() -> None:
    references = [ReferenceIngredient(1, "garlic", "garlic")]

    result = match_ingredients([_candidate("- No garlic", 0)], references)

    assert result.matches[0].method == MatchMethod.UNMATCHED
    assert result.matches[0].reference_position is None
    assert result.review_queue[0].reason == "negated ingredient mention"


def test_combined_line_does_not_receive_credit_for_two_reference_rows() -> None:
    references = [
        ReferenceIngredient(1, "salt", "salt"),
        ReferenceIngredient(2, "black pepper", "black pepper"),
    ]

    result = match_ingredients([_candidate("- salt and black pepper", 0)], references)

    accepted = {
        match.reference_position
        for match in result.matches
        if match.method in {MatchMethod.EXACT_KEY, MatchMethod.KNOWN_ALIAS}
    }
    assert accepted == set()


def test_reference_surface_form_is_parsed_into_an_exact_variant() -> None:
    references = [ReferenceIngredient(1, "fresh thyme", "4 sprigs fresh thyme")]

    result = match_ingredients([_candidate("- fresh thyme", 0)], references)

    assert result.matches[0].method == MatchMethod.EXACT_KEY


def test_missing_size_qualifier_does_not_block_identity_match() -> None:
    references = [ReferenceIngredient(1, "medium peaches", "medium peaches")]

    result = match_ingredients([_candidate("- 3 peaches", 0)], references)

    assert result.matches[0].method == MatchMethod.EXACT_KEY
    assert result.review_queue[0].reason == "ingredient qualifier missing"


def test_matching_size_qualifier_needs_no_review() -> None:
    references = [ReferenceIngredient(1, "medium peaches", "medium peaches")]

    result = match_ingredients([_candidate("- 3 medium peaches", 0)], references)

    assert result.matches[0].method == MatchMethod.EXACT_KEY
    assert result.review_queue == ()


def test_conflicting_size_qualifiers_match_identity_and_queue_review() -> None:
    references = [ReferenceIngredient(1, "medium peaches", "medium peaches")]

    result = match_ingredients([_candidate("- 3 large peaches", 0)], references)

    assert result.matches[0].method == MatchMethod.EXACT_KEY
    assert result.review_queue[0].reason == "ingredient qualifiers conflict"


def test_added_size_qualifier_matches_identity_and_queues_review() -> None:
    references = [ReferenceIngredient(1, "peaches", "peaches")]

    result = match_ingredients([_candidate("- 3 large peaches", 0)], references)

    assert result.matches[0].method == MatchMethod.EXACT_KEY
    assert result.review_queue[0].reason == "ingredient qualifier added"
