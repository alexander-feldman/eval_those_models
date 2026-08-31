#!/usr/bin/env python3
"""Build reproducible, non-sensitive metrics for Experiment 3 run logs."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any

from eval_those_models.grading import grade_response
from eval_those_models.grading.models import ReferenceIngredient, ScoreSet

_PROSE_PREFIXES = (
    "based on",
    "i'll",
    "i’ll",
    "i have",
    "no result",
    "the results",
    "here ",
)
_LIST_MARKER = re.compile(r"^(?:[-*•]|\d+[.)])\s+")
_CLAUDE_TOOL_PREAMBLE = re.compile(r"^I['’]ll search[^.]*\.", re.IGNORECASE)


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


def _meaningful_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _identity_like(line: str) -> bool:
    folded = line.casefold()
    return not (
        folded.startswith(_PROSE_PREFIXES)
        or _LIST_MARKER.match(line)
        or "**" in line
        or line.endswith(":")
    )


def _output_contract_compliant(text: str) -> bool:
    lines = _meaningful_lines(text)
    return 5 <= len(lines) <= 12 and all(_identity_like(line) for line in lines)


def _adapt_delimiters(text: str) -> str:
    """Add parser-visible delimiters without removing model-authored prose."""
    lines = _meaningful_lines(text)
    if lines and all(_identity_like(line) for line in lines):
        return "\n".join(f"- {line}" for line in lines)
    if len(lines) == 1 and "." not in lines[0]:
        parts = [part.strip() for part in lines[0].split(",") if part.strip()]
        if 5 <= len(parts) <= 20:
            return "\n".join(f"- {part}" for part in parts)
    return text


def _adapt_identity_only(text: str) -> str:
    """Also remove Claude's fixed tool narration prefix, preserving ingredient words."""
    without_preamble = _CLAUDE_TOOL_PREAMBLE.sub("", text, count=1).lstrip()
    return _adapt_delimiters(without_preamble)


def _load_events(
    paths: list[Path],
) -> tuple[
    dict[tuple[str, str, str], dict[str, Any]],
    list[dict[str, Any]],
]:
    cells: dict[tuple[str, str, str], dict[str, Any]] = {}
    operational: list[dict[str, Any]] = []
    for path in paths:
        started: dict[str, dict[str, Any]] = {}
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            event = json.loads(raw_line)
            event_kind = event.get("event")
            if event_kind == "attempt_started":
                started[event["attempt_id"]] = event["case"]
            elif event_kind in {"attempt_succeeded", "attempt_failed"}:
                case = started[event["attempt_id"]]
                operational.append({"case": case, "event": event, "run": str(path)})
                if event_kind == "attempt_succeeded":
                    key = (
                        case["model_requested"],
                        case["prompt_template_id"],
                        case["recipe_id"],
                    )
                    cells[key] = {"case": case, "event": event, "run": str(path)}
    return cells, operational


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


def _score_dict(score: ScoreSet) -> dict[str, int | float]:
    return asdict(score)


def _micro_score(rows: list[dict[str, Any]], score_key: str) -> dict[str, int | float]:
    true_positives = sum(row[score_key]["true_positives"] for row in rows)
    false_positives = sum(row[score_key]["false_positives"] for row in rows)
    false_negatives = sum(row[score_key]["false_negatives"] for row in rows)
    precision = (
        true_positives / (true_positives + false_positives)
        if true_positives + false_positives
        else 0.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if true_positives + false_negatives
        else 0.0
    )
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "cases": len(rows),
        "output_contract_compliant": sum(row["output_contract_compliant"] for row in rows),
        "searched": sum(row["searched"] for row in rows),
        "citation_annotations": sum(row["citation_annotations"] for row in rows),
        "reported_cost_usd": sum(row["reported_cost_usd"] for row in rows),
        "delimiter_adapted_strict": _micro_score(rows, "delimiter_adapted_strict"),
        "identity_only_strict": _micro_score(rows, "identity_only_strict"),
    }


def _group(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[str, Any]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[key] for key in keys)].append(row)
    return {" | ".join(key): _aggregate(value) for key, value in sorted(grouped.items())}


def build_report(database: Path, run_paths: list[Path]) -> dict[str, Any]:
    cells, operational = _load_events(run_paths)
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    rows: list[dict[str, Any]] = []
    try:
        for (model, prompt, recipe_id), cell in sorted(cells.items()):
            case = cell["case"]
            event = cell["event"]
            reference_text, references = _reference_rows(connection, recipe_id)
            delimiter_grade = grade_response(
                _adapt_delimiters(event["output_text"]), reference_text, references
            )
            identity_grade = grade_response(
                _adapt_identity_only(event["output_text"]), reference_text, references
            )
            usage = event.get("usage") or {}
            tool_details = usage.get("server_tool_use_details") or {}
            raw_response = event.get("raw_response") or {}
            choices = raw_response.get("choices") or []
            message = choices[0].get("message", {}) if choices else {}
            rows.append(
                {
                    "model": model,
                    "prompt": prompt,
                    "recipe_id": recipe_id,
                    "attempt_id": event["attempt_id"],
                    "finish_reason": event.get("finish_reason"),
                    "output_contract_compliant": _output_contract_compliant(event["output_text"]),
                    "searched": bool(tool_details.get("web_search_requests", 0)),
                    "web_search_requests": tool_details.get("web_search_requests", 0),
                    "citation_annotations": len(message.get("annotations") or []),
                    "reported_cost_usd": float(event["reported_cost_usd"]),
                    "delimiter_adapted_strict": _score_dict(delimiter_grade.identity.strict),
                    "identity_only_strict": _score_dict(identity_grade.identity.strict),
                    "run": cell["run"],
                    "case_id": case["case_id"],
                }
            )
    finally:
        connection.close()

    failures = [item for item in operational if item["event"]["event"] == "attempt_failed"]
    models = {row["model"] for row in rows}
    prompts = {row["prompt"] for row in rows}
    cell_keys = {(row["model"], row["prompt"], row["recipe_id"]) for row in rows}
    common_recipe_ids = sorted(
        {
            row["recipe_id"]
            for row in rows
            if all(
                (model, prompt, row["recipe_id"]) in cell_keys
                for model in models
                for prompt in prompts
            )
        }
    )
    common_rows = [row for row in rows if row["recipe_id"] in common_recipe_ids]
    return {
        "analysis_version": 1,
        "description": (
            "Deterministic-v3 strict identity metrics. delimiter_adapted_strict adds only "
            "list delimiters; identity_only_strict additionally removes Claude's fixed "
            "search-narration prefix without changing ingredient words."
        ),
        "input_runs": [str(path) for path in run_paths],
        "operational": {
            "attempts": len(operational),
            "succeeded": len(operational) - len(failures),
            "failed": len(failures),
            "reported_cost_usd": sum(
                float(item["event"].get("reported_cost_usd", 0)) for item in operational
            ),
            "failures": [
                {
                    "model": item["case"]["model_requested"],
                    "prompt": item["case"]["prompt_template_id"],
                    "recipe_id": item["case"]["recipe_id"],
                    "attempt_id": item["event"]["attempt_id"],
                    "error": item["event"]["error"],
                    "reported_cost_usd": float(item["event"]["reported_cost_usd"]),
                }
                for item in failures
            ],
        },
        "analytic_cells": len(rows),
        "common_heldout_recipe_ids": common_recipe_ids,
        "common_heldout_by_prompt": _group(common_rows, ("prompt",)),
        "common_heldout_by_model_and_prompt": _group(common_rows, ("model", "prompt")),
        "overall_by_prompt": _group(rows, ("prompt",)),
        "by_model_and_prompt": _group(rows, ("model", "prompt")),
        "by_recipe_and_prompt": _group(rows, ("recipe_id", "prompt")),
        "cells": rows,
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
