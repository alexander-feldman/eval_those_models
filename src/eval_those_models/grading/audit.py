"""Reference round-trip checks for deterministic grading readiness."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from eval_those_models.grading.matching import match_ingredients
from eval_those_models.grading.models import CandidateIngredient, MatchMethod, ReferenceIngredient
from eval_those_models.grading.normalization import quantities_equivalent
from eval_those_models.grading.parsing import parse_ingredient_line, parse_quantity_text


class ReferenceAuditIssueKind(StrEnum):
    UNPARSEABLE_LINE = "unparseable_line"
    IDENTITY_MISMATCH = "identity_mismatch"
    QUANTITY_MISMATCH = "quantity_mismatch"


@dataclass(frozen=True)
class ReferenceAuditRecord:
    """The exact and structured fields needed to audit one private reference row."""

    recipe_id: str
    position: int
    text_exact: str
    quantity_text_exact: str | None
    ingredient_text: str
    ingredient_key: str
    tier: Literal["primary", "secondary", "tertiary"] = "tertiary"
    optional: bool = False
    subrecipe_reference: bool = False
    section: str | None = None


@dataclass(frozen=True)
class ReferenceAuditIssue:
    """A location-only diagnostic that does not disclose protected reference text."""

    recipe_id: str
    position: int
    kind: ReferenceAuditIssueKind


@dataclass(frozen=True)
class ReferenceAuditReport:
    recipe_count: int
    ingredient_count: int
    identity_match_count: int
    populated_quantity_count: int
    quantity_match_count: int
    perfect_recipe_count: int
    issues: tuple[ReferenceAuditIssue, ...]

    @property
    def passed(self) -> bool:
        return not self.issues

    def issue_counts(self) -> dict[str, int]:
        return dict(Counter(issue.kind.value for issue in self.issues))


def audit_reference_records(records: Sequence[ReferenceAuditRecord]) -> ReferenceAuditReport:
    """Round-trip exact lines through the production parser and matcher."""
    grouped: dict[str, list[ReferenceAuditRecord]] = defaultdict(list)
    for record in records:
        grouped[record.recipe_id].append(record)

    issues: list[ReferenceAuditIssue] = []
    identity_matches = 0
    populated_quantities = sum(
        record.quantity_text_exact is not None and bool(record.quantity_text_exact.strip())
        for record in records
    )
    quantity_matches = 0
    perfect_recipes = 0

    for recipe_id, recipe_records in grouped.items():
        ordered = sorted(recipe_records, key=lambda record: record.position)
        references = [
            ReferenceIngredient(
                position=record.position,
                ingredient_key=record.ingredient_key,
                ingredient_text=record.ingredient_text,
                quantity_text_exact=record.quantity_text_exact,
                tier=record.tier,
                optional=record.optional,
                subrecipe_reference=record.subrecipe_reference,
                section=record.section,
            )
            for record in ordered
        ]
        candidates: list[CandidateIngredient] = []
        expected_position_by_index: dict[int, int] = {}
        quantity_by_index = {}
        recipe_issue_start = len(issues)

        for record in ordered:
            candidate = parse_ingredient_line(record.text_exact, len(candidates))
            if candidate is None:
                issues.append(
                    ReferenceAuditIssue(
                        recipe_id,
                        record.position,
                        ReferenceAuditIssueKind.UNPARSEABLE_LINE,
                    )
                )
                continue
            candidates.append(candidate)
            expected_position_by_index[candidate.index] = record.position
            quantity_by_index[candidate.index] = record.quantity_text_exact

        matches = match_ingredients(candidates, references).matches
        for match in matches:
            if match.candidate_index is None:
                continue
            expected_position = expected_position_by_index[match.candidate_index]
            identity_matches_self = (
                match.reference_position == expected_position
                and match.method in {MatchMethod.EXACT_KEY, MatchMethod.KNOWN_ALIAS}
            )
            if identity_matches_self:
                identity_matches += 1
            else:
                issues.append(
                    ReferenceAuditIssue(
                        recipe_id,
                        expected_position,
                        ReferenceAuditIssueKind.IDENTITY_MISMATCH,
                    )
                )

            quantity_text = quantity_by_index[match.candidate_index]
            if quantity_text is None or not quantity_text.strip():
                continue
            candidate = candidates[match.candidate_index]
            if quantities_equivalent(candidate.quantity, parse_quantity_text(quantity_text)):
                quantity_matches += 1
            else:
                issues.append(
                    ReferenceAuditIssue(
                        recipe_id,
                        expected_position,
                        ReferenceAuditIssueKind.QUANTITY_MISMATCH,
                    )
                )

        if len(issues) == recipe_issue_start:
            perfect_recipes += 1

    return ReferenceAuditReport(
        recipe_count=len(grouped),
        ingredient_count=len(records),
        identity_match_count=identity_matches,
        populated_quantity_count=populated_quantities,
        quantity_match_count=quantity_matches,
        perfect_recipe_count=perfect_recipes,
        issues=tuple(issues),
    )
