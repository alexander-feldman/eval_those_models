from eval_those_models.cases import canonical_case_json, case_id


def test_case_id_is_independent_of_mapping_order() -> None:
    first = {"model": "example/model", "temperature": 0, "prompt": "hello"}
    reordered = {"prompt": "hello", "temperature": 0, "model": "example/model"}

    assert canonical_case_json(first) == canonical_case_json(reordered)
    assert case_id(first) == case_id(reordered)
    assert case_id(first).startswith("case_")


def test_case_id_changes_when_a_case_field_changes() -> None:
    baseline = {"model": "example/model", "repetition": 1}
    repeated = {"model": "example/model", "repetition": 2}

    assert case_id(baseline) != case_id(repeated)
