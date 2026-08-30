from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from eval_those_models.cli import main as cli_main
from eval_those_models.dataset import importer


def synthetic_row() -> dict[str, str]:
    reference = "1 cup synthetic flour"
    record = {
        "position": 1,
        "section": None,
        "text_exact": reference,
        "quantity_text_exact": "1 cup",
        "ingredient_text": "synthetic flour",
        "ingredient_key": "synthetic flour",
        "tier": "primary",
        "optional": False,
        "subrecipe_reference": False,
    }
    row = {column: "" for column in importer.REQUIRED_COLUMNS}
    row.update(
        {
            "schema_version": "test-v1",
            "recipe_id": "synthetic__recipe",
            "cookbook_id": "synthetic",
            "cookbook_title_exact": "Synthetic Cookbook",
            "cookbook_author": "Test Author",
            "recipe_name_exact": "Synthetic Recipe",
            "recipe_family": "test",
            "source_images_json": "[]",
            "source_pages_json": "[]",
            "source_transcription_file": "synthetic.md",
            "rights_context": "synthetic_fixture",
            "transcription_status": "partial",
            "ingredient_list_complete": "false",
            "completeness_note": "Deliberately partial test fixture",
            "ingredient_count": "1",
            "section_count": "0",
            "ingredient_sections_json": "[]",
            "reference_text_exact": reference,
            "reference_text_sha256": hashlib.sha256(reference.encode()).hexdigest(),
            "ingredient_lines_exact_json": json.dumps([reference]),
            "ingredient_records_json": json.dumps([record]),
            "primary_ingredients_json": json.dumps(["synthetic flour"]),
            "secondary_ingredients_json": "[]",
            "tertiary_ingredients_json": "[]",
            "ingredient_order_json": json.dumps(["synthetic flour"]),
            "optional_ingredient_count": "0",
            "has_subrecipe_references": "false",
            "quantity_annotation_status": "test",
            "tier_annotation_status": "test",
            "tier_rubric_version": "test-v1",
            "normalization_profile_id": "test-v1",
            "human_review_status": "synthetic",
            "popularity_rubric_version": "test-v1",
            "popularity_sources_json": json.dumps(["https://example.com/evidence"]),
            "ratings_review_status": "synthetic",
            "ratings_notes": "Synthetic test values",
            "author_popularity_score": "1",
            "book_popularity_score": "1",
            "recipe_popularity_within_book_score": "1",
            "ingredient_complexity_score": "1",
            "recipe_obscurity_unusualness_score": "1",
        }
    )
    return row


def write_source(path: Path, row: dict[str, str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted(importer.REQUIRED_COLUMNS))
        writer.writeheader()
        writer.writerow(row)


def importer_args(source: Path, output: Path) -> argparse.Namespace:
    return argparse.Namespace(
        source=source,
        output=output,
        schema=Path(importer.__file__).with_name("schema.sql"),
        validate_only=False,
        expected_cookbooks=1,
        expected_recipes=1,
        expected_ingredients=1,
        expected_ratings=5,
        expected_rating_sources=1,
    )


def test_builds_and_validates_a_synthetic_database(tmp_path: Path) -> None:
    source = tmp_path / "metadata.csv"
    output = tmp_path / "references.sqlite"
    write_source(source, synthetic_row())
    args = importer_args(source, output)

    counts = importer.build_database(args)

    assert counts == {
        "cookbooks": 1,
        "recipes": 1,
        "ingredients": 1,
        "ratings": 5,
        "rating_sources": 1,
        "partial_recipes": 1,
        "annotation_provenance": 2,
    }
    with sqlite3.connect(output) as connection:
        assert importer.validate_database(connection, args) == counts


def test_grading_audit_reports_only_locations_and_issue_kinds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "metadata.csv"
    output = tmp_path / "references.sqlite"
    write_source(source, synthetic_row())
    importer.build_database(importer_args(source, output))

    assert cli_main(["dataset", "audit-grading", "--output", str(output)]) == 0
    assert "identities=1/1, quantities=1/1, perfect_recipes=1/1" in capsys.readouterr().out

    with sqlite3.connect(output) as connection:
        connection.execute("UPDATE ingredients SET quantity_text_exact = '2 cups'")

    assert cli_main(["dataset", "audit-grading", "--output", str(output)]) == 1
    output_text = capsys.readouterr().out
    assert "quantity_mismatch" in output_text
    assert "synthetic__recipe ingredient 1" in output_text
    assert "synthetic flour" not in output_text


def test_invalid_reference_hash_does_not_replace_existing_database(tmp_path: Path) -> None:
    source = tmp_path / "metadata.csv"
    output = tmp_path / "references.sqlite"
    output.write_bytes(b"existing database placeholder")
    row = synthetic_row()
    row["reference_text_sha256"] = "0" * 64
    write_source(source, row)

    with pytest.raises(importer.ValidationError, match="SHA-256 disagrees"):
        importer.build_database(importer_args(source, output))

    assert output.read_bytes() == b"existing database placeholder"
