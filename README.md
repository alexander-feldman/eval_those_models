# eval_those_models

A reproducible harness for comparing model behavior and response quality across
controlled prompt, reference, model, and inference-setting variations.

See [EVAL_PLAN.md](EVAL_PLAN.md) for the proposed experiment design, grading
framework, OpenRouter execution architecture, data model, and implementation
phases. See [RECIPE_EVAL_METADATA_SCHEMA.md](RECIPE_EVAL_METADATA_SCHEMA.md) for
the private ground-truth CSV format and metric definitions.

User-supplied ground truth is kept locally under `data/transcriptions/` and
`data/private/`; both are excluded from Git to avoid redistributing source text.

Current local dataset: 27 recipes, 362 structured ingredients, 26 complete
ingredient lists, and 1 explicitly partial list. The next implementation phase
is the 24-call OpenRouter smoke-test harness described in the plan.

The private recipe metadata also contains provisional, versioned 1–5 ratings
for author popularity, book popularity, recipe popularity within the book,
ingredient-count complexity, and recipe obscurity/unusualness. These fields are
intended for stratified evaluation analysis and include evidence URLs and
annotation notes.
