from eval_those_models.grading import (
    ReferenceAuditIssueKind,
    ReferenceAuditRecord,
    audit_reference_records,
)


def _record(**overrides: object) -> ReferenceAuditRecord:
    values = {
        "recipe_id": "recipe-1",
        "position": 1,
        "text_exact": "1 cup synthetic flour",
        "quantity_text_exact": "1 cup",
        "ingredient_text": "synthetic flour",
        "ingredient_key": "synthetic flour",
    }
    values.update(overrides)
    return ReferenceAuditRecord(**values)  # type: ignore[arg-type]


def test_reference_audit_accepts_a_consistent_round_trip() -> None:
    report = audit_reference_records([_record()])

    assert report.passed
    assert report.identity_match_count == 1
    assert report.quantity_match_count == 1
    assert report.perfect_recipe_count == 1


def test_reference_audit_reports_locations_without_reference_evidence() -> None:
    report = audit_reference_records(
        [
            _record(
                ingredient_key="different ingredient",
                ingredient_text="different ingredient",
            ),
            _record(
                recipe_id="recipe-2",
                quantity_text_exact="2 cups",
            ),
        ]
    )

    assert not report.passed
    assert report.issue_counts() == {"identity_mismatch": 1, "quantity_mismatch": 1}
    assert [(issue.recipe_id, issue.position, issue.kind) for issue in report.issues] == [
        ("recipe-1", 1, ReferenceAuditIssueKind.IDENTITY_MISMATCH),
        ("recipe-2", 1, ReferenceAuditIssueKind.QUANTITY_MISMATCH),
    ]
    assert all(not hasattr(issue, "reference_evidence") for issue in report.issues)
