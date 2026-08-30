PRAGMA foreign_keys = ON;

CREATE TABLE schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE cookbooks (
    cookbook_id TEXT PRIMARY KEY,
    title_exact TEXT NOT NULL,
    author TEXT NOT NULL,
    rights_context TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE recipes (
    recipe_id TEXT PRIMARY KEY,
    cookbook_id TEXT NOT NULL REFERENCES cookbooks(cookbook_id),
    source_schema_version TEXT NOT NULL,
    name_exact TEXT NOT NULL,
    subtitle_exact TEXT,
    recipe_family TEXT NOT NULL,
    source_transcription_file TEXT NOT NULL,
    transcription_status TEXT NOT NULL CHECK (transcription_status IN ('complete', 'partial')),
    ingredient_list_complete INTEGER NOT NULL CHECK (ingredient_list_complete IN (0, 1)),
    completeness_note TEXT,
    ingredient_count INTEGER NOT NULL CHECK (ingredient_count >= 0),
    section_count INTEGER NOT NULL CHECK (section_count >= 0),
    optional_ingredient_count INTEGER NOT NULL CHECK (optional_ingredient_count >= 0),
    has_subrecipe_references INTEGER NOT NULL CHECK (has_subrecipe_references IN (0, 1)),
    reference_text_exact TEXT NOT NULL,
    reference_text_sha256 TEXT NOT NULL CHECK (length(reference_text_sha256) = 64),
    normalization_profile_id TEXT NOT NULL,
    human_review_status TEXT NOT NULL,
    review_notes TEXT
) WITHOUT ROWID;

CREATE INDEX idx_recipes_cookbook_id ON recipes(cookbook_id);
CREATE INDEX idx_recipes_completeness ON recipes(ingredient_list_complete, transcription_status);

CREATE TABLE recipe_sources (
    recipe_id TEXT NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    source_kind TEXT NOT NULL CHECK (source_kind IN ('image', 'page')),
    position INTEGER NOT NULL CHECK (position >= 1),
    source_value TEXT NOT NULL,
    PRIMARY KEY (recipe_id, source_kind, position)
) WITHOUT ROWID;

CREATE TABLE recipe_sections (
    recipe_id TEXT NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK (position >= 1),
    heading_exact TEXT NOT NULL,
    PRIMARY KEY (recipe_id, position)
) WITHOUT ROWID;

CREATE TABLE ingredients (
    recipe_id TEXT NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK (position >= 1),
    section TEXT,
    text_exact TEXT NOT NULL,
    quantity_text_exact TEXT,
    ingredient_text TEXT NOT NULL,
    ingredient_key TEXT NOT NULL,
    tier TEXT NOT NULL CHECK (tier IN ('primary', 'secondary', 'tertiary')),
    optional INTEGER NOT NULL CHECK (optional IN (0, 1)),
    subrecipe_reference INTEGER NOT NULL CHECK (subrecipe_reference IN (0, 1)),
    PRIMARY KEY (recipe_id, position)
) WITHOUT ROWID;

CREATE INDEX idx_ingredients_key ON ingredients(ingredient_key);
CREATE INDEX idx_ingredients_tier ON ingredients(recipe_id, tier);

CREATE TABLE recipe_annotation_provenance (
    recipe_id TEXT NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    annotation_kind TEXT NOT NULL
        CHECK (annotation_kind IN ('quantity', 'tier')),
    status TEXT NOT NULL,
    rubric_version TEXT,
    annotation_method TEXT NOT NULL
        CHECK (annotation_method IN ('machine_parsed', 'proposed_annotation')),
    source_status_column TEXT NOT NULL,
    source_rubric_column TEXT,
    PRIMARY KEY (recipe_id, annotation_kind),
    CHECK (
        (annotation_kind = 'quantity' AND rubric_version IS NULL
            AND source_rubric_column IS NULL)
        OR
        (annotation_kind = 'tier' AND rubric_version IS NOT NULL
            AND source_rubric_column IS NOT NULL)
    )
) WITHOUT ROWID;

CREATE TABLE rating_dimensions (
    dimension TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    score_min INTEGER NOT NULL DEFAULT 1,
    score_max INTEGER NOT NULL DEFAULT 5,
    value_kind TEXT NOT NULL CHECK (value_kind IN ('human_annotation', 'derived')),
    CHECK (score_min <= score_max)
) WITHOUT ROWID;

CREATE TABLE recipe_ratings (
    recipe_id TEXT NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    dimension TEXT NOT NULL REFERENCES rating_dimensions(dimension),
    score INTEGER NOT NULL CHECK (score BETWEEN 1 AND 5),
    rubric_version TEXT NOT NULL,
    annotator TEXT NOT NULL,
    review_status TEXT NOT NULL,
    rated_at TEXT,
    notes TEXT,
    source_column TEXT NOT NULL,
    PRIMARY KEY (recipe_id, dimension, rubric_version)
) WITHOUT ROWID;

CREATE INDEX idx_recipe_ratings_dimension_score ON recipe_ratings(dimension, score);

CREATE TABLE rating_sources (
    source_id INTEGER PRIMARY KEY,
    recipe_id TEXT NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    source_position INTEGER NOT NULL CHECK (source_position >= 1),
    url TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_domain TEXT,
    accessed_at TEXT,
    evidence_note TEXT,
    UNIQUE (recipe_id, source_position),
    UNIQUE (recipe_id, url)
);

CREATE INDEX idx_rating_sources_recipe_id ON rating_sources(recipe_id);

CREATE TABLE recipe_rating_sources (
    recipe_id TEXT NOT NULL,
    dimension TEXT NOT NULL,
    rubric_version TEXT NOT NULL,
    source_id INTEGER NOT NULL REFERENCES rating_sources(source_id) ON DELETE CASCADE,
    PRIMARY KEY (recipe_id, dimension, rubric_version, source_id),
    FOREIGN KEY (recipe_id, dimension, rubric_version)
        REFERENCES recipe_ratings(recipe_id, dimension, rubric_version)
        ON DELETE CASCADE
) WITHOUT ROWID;

CREATE INDEX idx_recipe_rating_sources_source_id ON recipe_rating_sources(source_id);

CREATE VIEW recipe_ingredient_counts AS
SELECT
    r.recipe_id,
    r.ingredient_count AS declared_ingredient_count,
    COUNT(i.position) AS actual_ingredient_count,
    r.optional_ingredient_count AS declared_optional_ingredient_count,
    COALESCE(SUM(i.optional), 0) AS actual_optional_ingredient_count,
    r.has_subrecipe_references AS declared_has_subrecipe_references,
    CASE WHEN COALESCE(SUM(i.subrecipe_reference), 0) > 0 THEN 1 ELSE 0 END
        AS actual_has_subrecipe_references
FROM recipes AS r
LEFT JOIN ingredients AS i USING (recipe_id)
GROUP BY r.recipe_id;
