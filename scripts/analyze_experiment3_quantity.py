#!/usr/bin/env python3
"""Build reproducible metrics for Experiment 3's uncapped quantity follow-up."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any

from eval_those_models.grading import grade_response
from eval_those_models.grading.models import MatchMethod, ReferenceIngredient
from eval_those_models.grading.normalization import normalize_text
from eval_those_models.grading.parsing import parse_ingredient_line, parse_quantity_text

_QUANTITY_START = re.compile(
    r"(?<!\w)(?:\d+\s*/\s*\d+|[¼½¾⅓⅔⅛⅜⅝⅞]|\d+(?:\.\d+)?)"
    r"\s*(?=(?:cups?|tsp|tbsp|tablespoons?|teaspoons?|ml|g|grams?|oz|ounces?|\|))",
    re.IGNORECASE,
)
_ACCEPTED_MATCHES = {MatchMethod.EXACT_KEY, MatchMethod.KNOWN_ALIAS}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", nargs="+", type=Path, help="attempts.jsonl files in order")
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data/private/cookbook_eval.sqlite"),
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def _load_successes(paths: list[Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    successes: list[dict[str, Any]] = []
    terminal_events: list[dict[str, Any]] = []
    for path in paths:
        started: dict[str, dict[str, Any]] = {}
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            event = json.loads(raw_line)
            if event.get("event") == "attempt_started":
                started[event["attempt_id"]] = event["case"]
            elif event.get("event") in {"attempt_succeeded", "attempt_failed"}:
                item = {
                    "case": started[event["attempt_id"]],
                    "event": event,
                    "run": str(path),
                }
                terminal_events.append(item)
                if event["event"] == "attempt_succeeded":
                    successes.append(item)
    return successes, terminal_events


def _reference_rows(
    connection: sqlite3.Connection, recipe_id: str
) -> tuple[str, list[ReferenceIngredient]]:
    recipe = connection.execute(
        "SELECT reference_text_exact FROM recipes WHERE recipe_id = ?", (recipe_id,)
    ).fetchone()
    if recipe is None:
        raise ValueError(f"unknown recipe: {recipe_id}")
    rows = connection.execute(
        """
        SELECT position, ingredient_key, ingredient_text, quantity_text_exact,
               tier, optional, subrecipe_reference, section
        FROM ingredients
        WHERE recipe_id = ?
        ORDER BY position
        """,
        (recipe_id,),
    ).fetchall()
    return recipe[0], [ReferenceIngredient(**dict(row)) for row in rows]


def _meaningful_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _strip_first_line_tool_narration(text: str) -> tuple[str, bool]:
    lines = _meaningful_lines(text)
    if not lines:
        return text, False
    first = lines[0]
    if "|" not in first:
        return text, False
    left = first.split("|", 1)[0]
    if parse_quantity_text(left) is not None:
        return "\n".join(lines), False
    match = _QUANTITY_START.search(left)
    if match is None or match.start() == 0:
        return "\n".join(lines), False
    lines[0] = first[match.start() :]
    return "\n".join(lines), True


def _adapt_quantity_rows(text: str) -> tuple[str, bool]:
    """Mechanically recover ingredient rows while retaining contract failures."""
    stripped, had_tool_narration = _strip_first_line_tool_narration(text)
    adapted: list[str] = []
    for line in _meaningful_lines(stripped):
        if line.count("|") > 1:
            adapted.extend(f"- {part.strip()}" for part in line.split("|") if part.strip())
            continue
        if "|" not in line:
            adapted.append(line)
            continue
        left, right = (part.strip() for part in line.split("|", 1))
        left = re.sub(r"^(\d+(?:\.\d+)?)(ml|g|oz)\b", r"\1 \2", left, flags=re.I)
        parsed_left = parse_ingredient_line(left, 0)
        right_normalized = normalize_text(right).casefold()
        if left.casefold() == "unknown":
            rendered = right
        elif (
            (right.casefold() == "unknown" and parse_quantity_text(left) is None)
            or normalize_text(left).casefold() == normalize_text(right).casefold()
            or (
                parsed_left is not None
                and parsed_left.quantity is not None
                and right_normalized in normalize_text(parsed_left.ingredient_phrase).casefold()
            )
        ):
            rendered = left
        else:
            rendered = f"{left} {right}"
        adapted.append(f"- {rendered}")
    return "\n".join(adapted), had_tool_narration


def _contract_compliant(text: str) -> bool:
    stripped, had_tool_narration = _strip_first_line_tool_narration(text)
    lines = _meaningful_lines(stripped)
    if had_tool_narration or not lines:
        return False
    for line in lines:
        if line.count("|") != 1:
            return False
        left, right = (part.strip() for part in line.split("|", 1))
        if not left or not right or right.casefold() == "unknown":
            return False
        if (
            left.casefold() != "unknown"
            and parse_quantity_text(left) is None
            and _QUANTITY_START.match(left) is None
        ):
            return False
        if parse_quantity_text(right) is not None:
            return False
    return True


def _cell_metrics(
    item: dict[str, Any], reference_text: str, references: list[ReferenceIngredient]
) -> dict[str, Any]:
    case = item["case"]
    event = item["event"]
    adapted, had_tool_narration = _adapt_quantity_rows(event["output_text"])
    grade = grade_response(adapted, reference_text, references)
    reference_by_position = {reference.position: reference for reference in references}
    candidate_by_index = {candidate.index: candidate for candidate in grade.response.ingredients}
    exact_wording = 0
    normalized_exact_wording = 0
    exact_quantity_and_wording = 0
    exact_quantity_and_normalized_wording = 0
    for match in grade.matches:
        if (
            match.method not in _ACCEPTED_MATCHES
            or match.candidate_index is None
            or match.reference_position is None
        ):
            continue
        candidate = candidate_by_index[match.candidate_index]
        reference = reference_by_position[match.reference_position]
        wording_exact = candidate.ingredient_phrase == reference.ingredient_text
        wording_normalized = (
            normalize_text(candidate.ingredient_phrase).casefold()
            == normalize_text(reference.ingredient_text).casefold()
        )
        exact_wording += wording_exact
        normalized_exact_wording += wording_normalized
        quantity_exact = grade.quantity.statuses.get(match.reference_position) == "exact"
        exact_quantity_and_wording += quantity_exact and wording_exact
        exact_quantity_and_normalized_wording += quantity_exact and wording_normalized

    usage = event.get("usage") or {}
    tool_details = usage.get("server_tool_use_details") or {}
    raw_response = event.get("raw_response") or {}
    choices = raw_response.get("choices") or []
    message = choices[0].get("message", {}) if choices else {}
    return {
        "model": case["model_requested"],
        "prompt": case["prompt_template_id"],
        "recipe_id": case["recipe_id"],
        "attempt_id": event["attempt_id"],
        "finish_reason": event.get("finish_reason"),
        "reported_cost_usd": float(event["reported_cost_usd"]),
        "searched": bool(tool_details.get("web_search_requests", 0)),
        "web_search_requests": tool_details.get("web_search_requests", 0),
        "citation_annotations": len(message.get("annotations") or []),
        "output_rows": len(_meaningful_lines(event["output_text"])),
        "content_normalized_rows": len(grade.response.ingredients),
        "output_contract_compliant": _contract_compliant(event["output_text"]),
        "had_tool_narration": had_tool_narration,
        "reference_rows": len(references),
        "strict_identity": asdict(grade.identity.strict),
        "quantity": {
            **asdict(grade.quantity),
            "statuses": Counter(status.value for status in grade.quantity.statuses.values()),
            "exact_reference_coverage": grade.quantity.exact_count / len(references),
            "equivalent_reference_coverage": (grade.quantity.equivalent_count / len(references)),
        },
        "exact_ingredient_wording": exact_wording,
        "normalized_exact_ingredient_wording": normalized_exact_wording,
        "exact_quantity_and_ingredient_wording": exact_quantity_and_wording,
        "exact_quantity_and_normalized_ingredient_wording": (exact_quantity_and_normalized_wording),
        "run": item["run"],
    }


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    true_positives = sum(row["strict_identity"]["true_positives"] for row in rows)
    false_positives = sum(row["strict_identity"]["false_positives"] for row in rows)
    false_negatives = sum(row["strict_identity"]["false_negatives"] for row in rows)
    precision = true_positives / (true_positives + false_positives)
    recall = true_positives / (true_positives + false_negatives)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    reference_rows = sum(row["reference_rows"] for row in rows)
    quantity_counts: Counter[str] = Counter()
    for row in rows:
        quantity_counts.update(row["quantity"]["statuses"])
    matched_quantities = sum(quantity_counts.values())
    return {
        "cases": len(rows),
        "searched": sum(row["searched"] for row in rows),
        "web_search_requests": sum(row["web_search_requests"] for row in rows),
        "citation_annotations": sum(row["citation_annotations"] for row in rows),
        "finish_reasons": Counter(row["finish_reason"] for row in rows),
        "output_contract_compliant": sum(row["output_contract_compliant"] for row in rows),
        "had_tool_narration": sum(row["had_tool_narration"] for row in rows),
        "output_rows": sum(row["output_rows"] for row in rows),
        "content_normalized_rows": sum(row["content_normalized_rows"] for row in rows),
        "reference_rows": reference_rows,
        "reported_cost_usd": sum(row["reported_cost_usd"] for row in rows),
        "strict_identity": {
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        },
        "quantity": {
            "matched_count": matched_quantities,
            "statuses": quantity_counts,
            "exact_rate_among_matched": (
                quantity_counts["exact"] / matched_quantities if matched_quantities else None
            ),
            "exact_or_equivalent_rate_among_matched": (
                (quantity_counts["exact"] + quantity_counts["equivalent"]) / matched_quantities
                if matched_quantities
                else None
            ),
            "exact_reference_coverage": quantity_counts["exact"] / reference_rows,
            "exact_or_equivalent_reference_coverage": (
                (quantity_counts["exact"] + quantity_counts["equivalent"]) / reference_rows
            ),
        },
        "exact_ingredient_wording": sum(row["exact_ingredient_wording"] for row in rows),
        "normalized_exact_ingredient_wording": sum(
            row["normalized_exact_ingredient_wording"] for row in rows
        ),
        "exact_quantity_and_ingredient_wording": sum(
            row["exact_quantity_and_ingredient_wording"] for row in rows
        ),
        "exact_quantity_and_normalized_ingredient_wording": sum(
            row["exact_quantity_and_normalized_ingredient_wording"] for row in rows
        ),
    }


def _group(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[str, Any]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[key] for key in keys)].append(row)
    return {" | ".join(key): _aggregate(value) for key, value in sorted(grouped.items())}


def build_report(database: Path, run_paths: list[Path]) -> dict[str, Any]:
    successes, terminal_events = _load_successes(run_paths)
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    rows: list[dict[str, Any]] = []
    try:
        for item in successes:
            reference_text, references = _reference_rows(connection, item["case"]["recipe_id"])
            rows.append(_cell_metrics(item, reference_text, references))
    finally:
        connection.close()
    failures = [item for item in terminal_events if item["event"]["event"] == "attempt_failed"]
    return {
        "analysis_version": 1,
        "description": (
            "Deterministic-v3 identity and quantity metrics for uncapped ingredient "
            "rows. Mechanical normalization handles compact metric units, duplicated "
            "columns, and one-line pipe-separated rows. Tool narration is removed only "
            "for grading. Every raw formatting defect remains a separate contract "
            "failure metric."
        ),
        "input_runs": [str(path) for path in run_paths],
        "operational": {
            "attempts": len(terminal_events),
            "succeeded": len(successes),
            "failed": len(failures),
            "reported_cost_usd": sum(
                float(item["event"].get("reported_cost_usd", 0)) for item in terminal_events
            ),
        },
        "overall_by_prompt": _group(rows, ("prompt",)),
        "by_model_and_prompt": _group(rows, ("model", "prompt")),
        "by_recipe_and_prompt": _group(rows, ("recipe_id", "prompt")),
        "by_model_recipe_and_prompt": _group(rows, ("model", "recipe_id", "prompt")),
        "cells": sorted(rows, key=lambda row: (row["model"], row["prompt"])),
    }


def main() -> int:
    args = _parse_args()
    report = build_report(args.database, args.runs)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
