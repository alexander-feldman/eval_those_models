# Recipe evaluation metadata schema

The canonical file is `data/private/recipe_eval_metadata.csv`. It uses one row
per recipe. Fields that naturally repeat per ingredient are stored as compact
JSON arrays inside CSV cells; this avoids a brittle `ingredient_1`,
`ingredient_2`, … column layout while preserving a single-file format.

## Evaluation model

Keep these outcomes separate instead of collapsing them immediately into one
score:

1. **Exact text fidelity** — compare the candidate with `reference_text_exact`
   strictly, then with the named normalization profile. Use
   `reference_text_sha256` to verify that ground truth has not changed.
2. **Ingredient presence** — match candidate ingredient identities against
   `ingredient_key` in `ingredient_records_json`, ignoring quantities during
   this step. Report precision, recall, and F1.
3. **Quantity accuracy** — for matched ingredients, compare the candidate
   quantity with `quantity_text_exact`. Report exact quantity agreement
   separately from ingredient presence, so a complete list with wrong amounts
   is recognizable as such.
4. **Ingredient importance** — compute recall separately for `primary`,
   `secondary`, and `tertiary` ingredients. If one aggregate is required, use
   proposed weights of 5, 2, and 1 respectively. The tiers in version 1 are
   proposed annotations and should receive a human review before becoming
   frozen benchmark labels.
5. **Ingredient order** — use `position` in `ingredient_records_json` or the
   convenience field `ingredient_order_json`. Report exact sequence agreement
   plus pairwise order accuracy among ingredients found in both lists. Pairwise
   accuracy avoids over-penalizing one omitted ingredient.

Do not give incomplete recipes a full-list recall score. Filter on
`ingredient_list_complete` or use `transcription_status` first.

## Ingredient tier definitions

- **Primary:** defines the identity of the dish or forms its physical base.
- **Secondary:** materially affects structure or characteristic flavor.
- **Tertiary:** seasoning, garnish, processing aid, optional addition, or minor
  accent.

Tier is based on culinary role, not quantity alone. A small amount of saffron
can be primary when it appears in the recipe name, while a larger amount of
generic cooking oil can be tertiary.

## Ingredient record JSON

Each object in `ingredient_records_json` contains:

| Field | Meaning |
|---|---|
| `position` | One-based printed ingredient order across the whole recipe. |
| `section` | Exact printed ingredient-section heading, or `null`. |
| `text_exact` | Complete printed ingredient line, with wrapped lines joined. |
| `quantity_text_exact` | Leading printed quantity/measure, or `null` when none is stated. |
| `ingredient_text` | Ingredient line with the leading quantity removed. |
| `ingredient_key` | Normalized identity string used for matching. |
| `tier` | `primary`, `secondary`, or `tertiary`. |
| `optional` | Whether the printed line marks the ingredient optional. |
| `subrecipe_reference` | Whether the line points to another recipe/page. |

## Recipe-level CSV columns

### Identity and provenance

- `schema_version`
- `recipe_id`
- `cookbook_id`
- `cookbook_title_exact`
- `cookbook_author`
- `recipe_name_exact`
- `recipe_subtitle_exact`
- `recipe_family`
- `source_images_json`
- `source_pages_json`
- `source_transcription_file`
- `rights_context`

### Completeness and structure

- `transcription_status`
- `ingredient_list_complete`
- `completeness_note`
- `ingredient_count`
- `section_count`
- `ingredient_sections_json`
- `optional_ingredient_count`
- `has_subrecipe_references`

### Exact-text ground truth

- `reference_text_exact`
- `reference_text_sha256`
- `ingredient_lines_exact_json`

### Structured scoring ground truth

- `ingredient_records_json`
- `primary_ingredients_json`
- `secondary_ingredients_json`
- `tertiary_ingredients_json`
- `ingredient_order_json`

### Annotation/version control

- `quantity_annotation_status`
- `tier_annotation_status`
- `tier_rubric_version`
- `normalization_profile_id`
- `human_review_status`
- `review_notes`

## Recommended score outputs

These belong in a separate run/results table, not in the ground-truth recipe
CSV: `strict_exact_match`, `normalized_exact_match`, `character_similarity`,
`ingredient_precision`, `ingredient_recall`, `ingredient_f1`,
`quantity_exact_rate`, `primary_recall`, `secondary_recall`,
`tertiary_recall`, `weighted_ingredient_recall`, `exact_order_match`, and
`pairwise_order_accuracy`.
