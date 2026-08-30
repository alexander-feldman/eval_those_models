"""Build and validate the private recipe-evaluation SQLite database."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlparse

IMPORTER_VERSION = "1.0"
RATING_DIMENSIONS = {
    "author_popularity": (
        "Author popularity",
        "author_popularity_score",
        "human_annotation",
    ),
    "book_popularity": (
        "Book popularity",
        "book_popularity_score",
        "human_annotation",
    ),
    "recipe_popularity_within_book": (
        "Recipe popularity within book",
        "recipe_popularity_within_book_score",
        "human_annotation",
    ),
    "ingredient_complexity": (
        "Ingredient-count complexity",
        "ingredient_complexity_score",
        "derived",
    ),
    "recipe_obscurity_unusualness": (
        "Recipe obscurity or unusualness",
        "recipe_obscurity_unusualness_score",
        "human_annotation",
    ),
}
REQUIRED_COLUMNS = {
    "schema_version",
    "recipe_id",
    "cookbook_id",
    "cookbook_title_exact",
    "cookbook_author",
    "recipe_name_exact",
    "recipe_subtitle_exact",
    "recipe_family",
    "source_images_json",
    "source_pages_json",
    "source_transcription_file",
    "rights_context",
    "transcription_status",
    "ingredient_list_complete",
    "completeness_note",
    "ingredient_count",
    "section_count",
    "ingredient_sections_json",
    "reference_text_exact",
    "reference_text_sha256",
    "ingredient_lines_exact_json",
    "ingredient_records_json",
    "primary_ingredients_json",
    "secondary_ingredients_json",
    "tertiary_ingredients_json",
    "ingredient_order_json",
    "optional_ingredient_count",
    "has_subrecipe_references",
    "quantity_annotation_status",
    "tier_annotation_status",
    "tier_rubric_version",
    "normalization_profile_id",
    "human_review_status",
    "review_notes",
    "popularity_rubric_version",
    "popularity_sources_json",
    "ratings_review_status",
    "ratings_notes",
    *(column for _, column, _ in RATING_DIMENSIONS.values()),
}


class ValidationError(ValueError):
    """Raised when source or imported data violates a benchmark invariant."""


def build_parser(
    project_root: Path | None = None,
    *,
    include_operation: bool = True,
) -> argparse.ArgumentParser:
    """Create the dataset command parser with project-relative defaults."""
    root = project_root or Path.cwd()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=root / "data/private/recipe_eval_metadata.csv",
        help="wide private source CSV",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "data/private/cookbook_eval.sqlite",
        help="private SQLite database to build or validate",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path(__file__).with_name("schema.sql"),
        help="tracked SQLite DDL",
    )
    if include_operation:
        parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--expected-cookbooks", type=int, default=5)
    parser.add_argument("--expected-recipes", type=int, default=27)
    parser.add_argument("--expected-ingredients", type=int, default=362)
    parser.add_argument("--expected-ratings", type=int, default=135)
    parser.add_argument("--expected-rating-sources", type=int, default=71)
    return parser


def parse_args(
    argv: list[str] | None = None,
    *,
    project_root: Path | None = None,
) -> argparse.Namespace:
    return build_parser(project_root).parse_args(argv)


def parse_bool(value: str, field: str, recipe_id: str) -> int:
    normalized = value.strip().lower()
    if normalized not in {"true", "false"}:
        raise ValidationError(f"{recipe_id}: {field} must be true or false")
    return int(normalized == "true")


def parse_json_list(row: dict[str, str], field: str) -> list:
    try:
        value = json.loads(row[field])
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{row['recipe_id']}: invalid JSON in {field}: {exc}") from exc
    if not isinstance(value, list):
        raise ValidationError(f"{row['recipe_id']}: {field} must contain a JSON list")
    return value


def complexity_score(ingredient_count: int) -> int:
    if ingredient_count <= 7:
        return 1
    if ingredient_count <= 10:
        return 2
    if ingredient_count <= 14:
        return 3
    if ingredient_count <= 18:
        return 4
    return 5


def read_and_validate_source(path: Path) -> tuple[list[dict[str, str]], dict[str, dict]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or ())
        if missing:
            raise ValidationError(f"source CSV is missing columns: {sorted(missing)}")
        rows = list(reader)

    recipe_ids: set[str] = set()
    cookbooks: dict[str, dict] = {}
    parsed: dict[str, dict] = {}

    for row in rows:
        recipe_id = row["recipe_id"]
        if not recipe_id or recipe_id in recipe_ids:
            raise ValidationError(f"missing or duplicate recipe_id: {recipe_id!r}")
        recipe_ids.add(recipe_id)

        cookbook = {
            "title_exact": row["cookbook_title_exact"],
            "author": row["cookbook_author"],
            "rights_context": row["rights_context"],
        }
        existing = cookbooks.setdefault(row["cookbook_id"], cookbook)
        if existing != cookbook:
            raise ValidationError(
                f"{recipe_id}: inconsistent cookbook metadata for {row['cookbook_id']}"
            )

        ingredient_count = int(row["ingredient_count"])
        section_count = int(row["section_count"])
        optional_count = int(row["optional_ingredient_count"])
        has_subrecipe = parse_bool(
            row["has_subrecipe_references"], "has_subrecipe_references", recipe_id
        )
        is_complete = parse_bool(
            row["ingredient_list_complete"], "ingredient_list_complete", recipe_id
        )

        images = parse_json_list(row, "source_images_json")
        pages = parse_json_list(row, "source_pages_json")
        sections = parse_json_list(row, "ingredient_sections_json")
        lines = parse_json_list(row, "ingredient_lines_exact_json")
        records = parse_json_list(row, "ingredient_records_json")
        order = parse_json_list(row, "ingredient_order_json")
        sources = parse_json_list(row, "popularity_sources_json")
        tiers = {
            tier: parse_json_list(row, f"{tier}_ingredients_json")
            for tier in ("primary", "secondary", "tertiary")
        }

        expected_positions = list(range(1, ingredient_count + 1))
        positions = [record.get("position") for record in records]
        if positions != expected_positions:
            raise ValidationError(f"{recipe_id}: ingredient positions are not contiguous")
        if not ingredient_count == len(records) == len(lines) == len(order):
            raise ValidationError(f"{recipe_id}: ingredient counts and arrays disagree")
        if [record.get("text_exact") for record in records] != lines:
            raise ValidationError(f"{recipe_id}: exact ingredient lines disagree")
        if [record.get("ingredient_key") for record in records] != order:
            raise ValidationError(f"{recipe_id}: ingredient order disagrees")
        if len(sections) != section_count:
            raise ValidationError(f"{recipe_id}: section count disagrees")
        if sum(bool(record.get("optional")) for record in records) != optional_count:
            raise ValidationError(f"{recipe_id}: optional ingredient count disagrees")
        if int(any(record.get("subrecipe_reference") for record in records)) != has_subrecipe:
            raise ValidationError(f"{recipe_id}: subrecipe-reference flag disagrees")
        for tier, keys in tiers.items():
            actual = [
                record.get("ingredient_key") for record in records if record.get("tier") == tier
            ]
            if actual != keys:
                raise ValidationError(f"{recipe_id}: {tier} ingredient array disagrees")

        required_record_keys = {
            "position",
            "section",
            "text_exact",
            "quantity_text_exact",
            "ingredient_text",
            "ingredient_key",
            "tier",
            "optional",
            "subrecipe_reference",
        }
        for record in records:
            if set(record) != required_record_keys:
                raise ValidationError(f"{recipe_id}: unexpected ingredient record shape")
            if record["tier"] not in tiers:
                raise ValidationError(f"{recipe_id}: invalid ingredient tier")
            if not isinstance(record["optional"], bool):
                raise ValidationError(f"{recipe_id}: ingredient optional flag must be boolean")
            if not isinstance(record["subrecipe_reference"], bool):
                raise ValidationError(f"{recipe_id}: subrecipe-reference flag must be boolean")

        digest = hashlib.sha256(row["reference_text_exact"].encode("utf-8")).hexdigest()
        if digest != row["reference_text_sha256"]:
            raise ValidationError(f"{recipe_id}: reference text SHA-256 disagrees")
        if is_complete != int(row["transcription_status"] == "complete"):
            raise ValidationError(f"{recipe_id}: completeness fields disagree")

        ratings = {}
        for dimension, (_, column, value_kind) in RATING_DIMENSIONS.items():
            score = int(row[column])
            if score not in range(1, 6):
                raise ValidationError(f"{recipe_id}: {column} is outside 1..5")
            if dimension == "ingredient_complexity" and score != complexity_score(ingredient_count):
                raise ValidationError(
                    f"{recipe_id}: ingredient complexity does not match its fixed bin"
                )
            ratings[dimension] = {
                "score": score,
                "column": column,
                "value_kind": value_kind,
            }

        if not all(
            isinstance(source, str)
            and urlparse(source).scheme in {"http", "https"}
            and urlparse(source).hostname
            for source in sources
        ):
            raise ValidationError(f"{recipe_id}: rating sources must be valid HTTP(S) URLs")
        if len(sources) != len(set(sources)):
            raise ValidationError(f"{recipe_id}: rating sources must be unique within a recipe")

        parsed[recipe_id] = {
            "images": images,
            "pages": pages,
            "sections": sections,
            "records": records,
            "ratings": ratings,
            "rating_sources": sources,
            "ingredient_list_complete": is_complete,
            "has_subrecipe_references": has_subrecipe,
        }

    return rows, parsed


def check_expected_source_counts(
    rows: list[dict[str, str]], parsed: dict[str, dict], args: argparse.Namespace
) -> None:
    actual = {
        "cookbooks": len({row["cookbook_id"] for row in rows}),
        "recipes": len(rows),
        "ingredients": sum(len(item["records"]) for item in parsed.values()),
        "ratings": sum(len(item["ratings"]) for item in parsed.values()),
        "rating_sources": sum(len(item["rating_sources"]) for item in parsed.values()),
    }
    expected = {
        "cookbooks": args.expected_cookbooks,
        "recipes": args.expected_recipes,
        "ingredients": args.expected_ingredients,
        "ratings": args.expected_ratings,
        "rating_sources": args.expected_rating_sources,
    }
    if actual != expected:
        raise ValidationError(f"source reconciliation failed: expected {expected}, got {actual}")


def insert_all(
    connection: sqlite3.Connection,
    rows: list[dict[str, str]],
    parsed: dict[str, dict],
    source_sha256: str,
) -> None:
    connection.executemany(
        "INSERT INTO schema_metadata(key, value) VALUES (?, ?)",
        [
            ("database_schema_version", "1"),
            ("importer_version", IMPORTER_VERSION),
            ("source_csv_sha256", source_sha256),
        ],
    )
    connection.executemany(
        "INSERT INTO rating_dimensions(dimension, display_name, value_kind) VALUES (?, ?, ?)",
        [
            (dimension, display_name, value_kind)
            for dimension, (display_name, _, value_kind) in RATING_DIMENSIONS.items()
        ],
    )

    cookbook_rows = {}
    for row in rows:
        cookbook_rows[row["cookbook_id"]] = (
            row["cookbook_id"],
            row["cookbook_title_exact"],
            row["cookbook_author"],
            row["rights_context"],
        )
    connection.executemany(
        """
        INSERT INTO cookbooks(cookbook_id, title_exact, author, rights_context)
        VALUES (?, ?, ?, ?)
        """,
        cookbook_rows.values(),
    )

    for row in rows:
        recipe_id = row["recipe_id"]
        item = parsed[recipe_id]
        connection.execute(
            """
            INSERT INTO recipes(
                recipe_id, cookbook_id, source_schema_version, name_exact,
                subtitle_exact, recipe_family, source_transcription_file,
                transcription_status, ingredient_list_complete, completeness_note,
                ingredient_count, section_count, optional_ingredient_count,
                has_subrecipe_references, reference_text_exact, reference_text_sha256,
                normalization_profile_id, human_review_status, review_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                recipe_id,
                row["cookbook_id"],
                row["schema_version"],
                row["recipe_name_exact"],
                row["recipe_subtitle_exact"] or None,
                row["recipe_family"],
                row["source_transcription_file"],
                row["transcription_status"],
                item["ingredient_list_complete"],
                row["completeness_note"] or None,
                int(row["ingredient_count"]),
                int(row["section_count"]),
                int(row["optional_ingredient_count"]),
                item["has_subrecipe_references"],
                row["reference_text_exact"],
                row["reference_text_sha256"],
                row["normalization_profile_id"],
                row["human_review_status"],
                row["review_notes"] or None,
            ),
        )
        connection.executemany(
            """
            INSERT INTO recipe_annotation_provenance(
                recipe_id, annotation_kind, status, rubric_version,
                annotation_method, source_status_column, source_rubric_column
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    recipe_id,
                    "quantity",
                    row["quantity_annotation_status"],
                    None,
                    "machine_parsed",
                    "quantity_annotation_status",
                    None,
                ),
                (
                    recipe_id,
                    "tier",
                    row["tier_annotation_status"],
                    row["tier_rubric_version"],
                    "proposed_annotation",
                    "tier_annotation_status",
                    "tier_rubric_version",
                ),
            ],
        )

        for source_kind, values in (("image", item["images"]), ("page", item["pages"])):
            connection.executemany(
                """
                INSERT INTO recipe_sources(recipe_id, source_kind, position, source_value)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (recipe_id, source_kind, position, str(value))
                    for position, value in enumerate(values, 1)
                ],
            )
        connection.executemany(
            "INSERT INTO recipe_sections(recipe_id, position, heading_exact) VALUES (?, ?, ?)",
            [
                (recipe_id, position, heading)
                for position, heading in enumerate(item["sections"], 1)
            ],
        )
        connection.executemany(
            """
            INSERT INTO ingredients(
                recipe_id, position, section, text_exact, quantity_text_exact,
                ingredient_text, ingredient_key, tier, optional, subrecipe_reference
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    recipe_id,
                    record["position"],
                    record["section"],
                    record["text_exact"],
                    record["quantity_text_exact"],
                    record["ingredient_text"],
                    record["ingredient_key"],
                    record["tier"],
                    int(bool(record["optional"])),
                    int(bool(record["subrecipe_reference"])),
                )
                for record in item["records"]
            ],
        )

        rubric_version = row["popularity_rubric_version"]
        for dimension, rating in item["ratings"].items():
            connection.execute(
                """
                INSERT INTO recipe_ratings(
                    recipe_id, dimension, score, rubric_version, annotator,
                    review_status, rated_at, notes, source_column
                ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?)
                """,
                (
                    recipe_id,
                    dimension,
                    rating["score"],
                    rubric_version,
                    "derived"
                    if rating["value_kind"] == "derived"
                    else "provisional_human_annotation",
                    row["ratings_review_status"],
                    row["ratings_notes"] or None,
                    rating["column"],
                ),
            )

        source_ids = []
        for position, url in enumerate(item["rating_sources"], 1):
            hostname = urlparse(url).hostname
            cursor = connection.execute(
                """
                INSERT INTO rating_sources(
                    recipe_id, source_position, url, source_type, source_domain,
                    accessed_at, evidence_note
                ) VALUES (?, ?, ?, 'web', ?, NULL, NULL)
                """,
                (recipe_id, position, url, hostname),
            )
            source_ids.append(cursor.lastrowid)

        # The source CSV stores one undifferentiated popularity source list.
        # Preserve that provenance by linking each source to every non-derived
        # rating rather than inventing unsupported source-to-dimension claims.
        for dimension, rating in item["ratings"].items():
            if rating["value_kind"] == "derived":
                continue
            connection.executemany(
                """
                INSERT INTO recipe_rating_sources(
                    recipe_id, dimension, rubric_version, source_id
                ) VALUES (?, ?, ?, ?)
                """,
                [(recipe_id, dimension, rubric_version, source_id) for source_id in source_ids],
            )


def table_count(connection: sqlite3.Connection, table: str) -> int:
    return connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def validate_database(connection: sqlite3.Connection, args: argparse.Namespace) -> dict[str, int]:
    connection.execute("PRAGMA foreign_keys = ON")
    foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_key_errors:
        raise ValidationError(f"foreign-key check failed: {foreign_key_errors}")
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise ValidationError(f"SQLite integrity check failed: {integrity}")

    counts = {
        "cookbooks": table_count(connection, "cookbooks"),
        "recipes": table_count(connection, "recipes"),
        "ingredients": table_count(connection, "ingredients"),
        "ratings": table_count(connection, "recipe_ratings"),
        "rating_sources": table_count(connection, "rating_sources"),
    }
    expected = {
        "cookbooks": args.expected_cookbooks,
        "recipes": args.expected_recipes,
        "ingredients": args.expected_ingredients,
        "ratings": args.expected_ratings,
        "rating_sources": args.expected_rating_sources,
    }
    if counts != expected:
        raise ValidationError(f"database reconciliation failed: expected {expected}, got {counts}")

    stored_source_hash = connection.execute(
        "SELECT value FROM schema_metadata WHERE key = 'source_csv_sha256'"
    ).fetchone()
    actual_source_hash = hashlib.sha256(args.source.read_bytes()).hexdigest()
    if stored_source_hash is None or stored_source_hash[0] != actual_source_hash:
        raise ValidationError("database source hash does not match the private CSV")

    count_mismatches = connection.execute(
        """
        SELECT recipe_id FROM recipe_ingredient_counts
        WHERE declared_ingredient_count != actual_ingredient_count
           OR declared_optional_ingredient_count != actual_optional_ingredient_count
           OR declared_has_subrecipe_references != actual_has_subrecipe_references
        """
    ).fetchall()
    if count_mismatches:
        raise ValidationError(f"recipe count reconciliation failed: {count_mismatches}")

    section_mismatches = connection.execute(
        """
        SELECT r.recipe_id
        FROM recipes AS r
        LEFT JOIN recipe_sections AS s USING (recipe_id)
        GROUP BY r.recipe_id
        HAVING r.section_count != COUNT(s.position)
        """
    ).fetchall()
    if section_mismatches:
        raise ValidationError(f"recipe section reconciliation failed: {section_mismatches}")

    incomplete = connection.execute(
        """
        SELECT COUNT(*) FROM recipes
        WHERE ingredient_list_complete = 0 AND transcription_status = 'partial'
        """
    ).fetchone()[0]
    inconsistent_completeness = connection.execute(
        """
        SELECT COUNT(*) FROM recipes
        WHERE ingredient_list_complete != (transcription_status = 'complete')
        """
    ).fetchone()[0]
    if incomplete != 1 or inconsistent_completeness:
        raise ValidationError(
            "expected one consistent partial recipe; "
            f"got partial={incomplete}, inconsistent={inconsistent_completeness}"
        )

    ratings_per_recipe = connection.execute(
        "SELECT MIN(n), MAX(n) FROM (SELECT COUNT(*) AS n FROM recipe_ratings GROUP BY recipe_id)"
    ).fetchone()
    if ratings_per_recipe != (5, 5):
        raise ValidationError(f"expected five ratings per recipe; got range {ratings_per_recipe}")
    if table_count(connection, "rating_dimensions") != 5:
        raise ValidationError("expected exactly five rating dimensions")

    annotation_rows = table_count(connection, "recipe_annotation_provenance")
    annotation_range = connection.execute(
        """
        SELECT MIN(n), MAX(n)
        FROM (
            SELECT COUNT(*) AS n
            FROM recipe_annotation_provenance
            GROUP BY recipe_id
        )
        """
    ).fetchone()
    if annotation_rows != args.expected_recipes * 2 or annotation_range != (2, 2):
        raise ValidationError(
            "expected quantity and tier provenance for every recipe; "
            f"got rows={annotation_rows}, range={annotation_range}"
        )

    bad_rating_provenance = connection.execute(
        """
        SELECT COUNT(*)
        FROM recipe_ratings AS r
        JOIN rating_dimensions AS d USING (dimension)
        WHERE (d.value_kind = 'derived' AND r.annotator != 'derived')
           OR (d.value_kind = 'human_annotation'
               AND r.annotator != 'provisional_human_annotation')
        """
    ).fetchone()[0]
    if bad_rating_provenance:
        raise ValidationError(f"{bad_rating_provenance} ratings have inconsistent provenance")

    bad_reference_hashes = []
    for recipe_id, exact_text, stored_hash in connection.execute(
        "SELECT recipe_id, reference_text_exact, reference_text_sha256 FROM recipes"
    ):
        actual_hash = hashlib.sha256(exact_text.encode("utf-8")).hexdigest()
        if actual_hash != stored_hash:
            bad_reference_hashes.append(recipe_id)
    if bad_reference_hashes:
        raise ValidationError(
            f"stored exact-text hash check failed for {len(bad_reference_hashes)} recipes"
        )

    source_link_range = connection.execute(
        """
        SELECT MIN(n), MAX(n)
        FROM (
            SELECT s.source_id, COUNT(rs.source_id) AS n
            FROM rating_sources AS s
            LEFT JOIN recipe_rating_sources AS rs USING (source_id)
            GROUP BY s.source_id
        )
        """
    ).fetchone()
    if source_link_range != (4, 4):
        raise ValidationError(
            f"each bundled source must link to four non-derived ratings; got {source_link_range}"
        )
    complexity_source_links = connection.execute(
        "SELECT COUNT(*) FROM recipe_rating_sources WHERE dimension = 'ingredient_complexity'"
    ).fetchone()[0]
    if complexity_source_links:
        raise ValidationError("derived ingredient-complexity ratings must not have source links")
    return counts | {
        "partial_recipes": incomplete,
        "annotation_provenance": annotation_rows,
    }


def build_database(args: argparse.Namespace) -> dict[str, int]:
    rows, parsed = read_and_validate_source(args.source)
    check_expected_source_counts(rows, parsed, args)
    source_sha256 = hashlib.sha256(args.source.read_bytes()).hexdigest()
    schema_sql = args.schema.read_text(encoding="utf-8")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(f".{args.output.name}.tmp")
    temporary.unlink(missing_ok=True)
    connection = sqlite3.connect(temporary)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(schema_sql)
        with connection:
            insert_all(connection, rows, parsed, source_sha256)
        counts = validate_database(connection, args)
        connection.execute("VACUUM")
        connection.close()
        os.replace(temporary, args.output)
        return counts
    except Exception:
        connection.close()
        temporary.unlink(missing_ok=True)
        raise


def run(args: argparse.Namespace) -> int:
    """Execute one parsed dataset operation."""
    try:
        if args.validate_only:
            connection = sqlite3.connect(f"file:{args.output}?mode=ro", uri=True)
            try:
                counts = validate_database(connection, args)
            finally:
                connection.close()
        else:
            counts = build_database(args)
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    operation = "validated" if args.validate_only else "built and validated"
    summary = ", ".join(f"{key}={value}" for key, value in counts.items())
    print(f"{operation} {args.output}: {summary}, foreign_keys=ok, integrity=ok")
    return 0


def main(
    argv: list[str] | None = None,
    *,
    project_root: Path | None = None,
) -> int:
    return run(parse_args(argv, project_root=project_root))


if __name__ == "__main__":
    raise SystemExit(main())
