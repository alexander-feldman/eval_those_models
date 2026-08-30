"""Read the minimum private reference data needed to plan safe cases."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


class ReferenceError(ValueError):
    """Raised when reference metadata cannot be loaded."""


@dataclass(frozen=True)
class Reference:
    recipe_id: str
    recipe_name: str
    cookbook_title: str
    rights_context: str
    ingredient_list_complete: bool
    reference_text_exact: str
    ingredient_lines: tuple[str, ...]


def load_references(database: Path, recipe_ids: tuple[str, ...]) -> dict[str, Reference]:
    """Load selected references without ever returning them in plan serialization."""
    if not database.is_file():
        raise ReferenceError(
            f"private reference database not found: {database}; run 'dataset build' first"
        )
    try:
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        placeholders = ",".join("?" for _ in recipe_ids)
        rows = connection.execute(
            f"""
            SELECT r.recipe_id, r.name_exact, c.title_exact, c.rights_context,
                   r.ingredient_list_complete, r.reference_text_exact
            FROM recipes AS r
            JOIN cookbooks AS c USING (cookbook_id)
            WHERE r.recipe_id IN ({placeholders})
            """,
            recipe_ids,
        ).fetchall()
        ingredients = connection.execute(
            f"""
            SELECT recipe_id, text_exact
            FROM ingredients
            WHERE recipe_id IN ({placeholders})
            ORDER BY recipe_id, position
            """,
            recipe_ids,
        ).fetchall()
    except sqlite3.Error as exc:
        raise ReferenceError(
            f"could not read private reference database {database}: {exc}"
        ) from exc
    finally:
        if "connection" in locals():
            connection.close()

    lines_by_recipe: dict[str, list[str]] = {recipe_id: [] for recipe_id in recipe_ids}
    for ingredient in ingredients:
        lines_by_recipe[ingredient["recipe_id"]].append(ingredient["text_exact"])
    references = {
        row["recipe_id"]: Reference(
            recipe_id=row["recipe_id"],
            recipe_name=row["name_exact"],
            cookbook_title=row["title_exact"],
            rights_context=row["rights_context"],
            ingredient_list_complete=bool(row["ingredient_list_complete"]),
            reference_text_exact=row["reference_text_exact"],
            ingredient_lines=tuple(lines_by_recipe[row["recipe_id"]]),
        )
        for row in rows
    }
    missing = set(recipe_ids) - references.keys()
    if missing:
        raise ReferenceError(f"unknown recipe IDs: {sorted(missing)}")
    return references
