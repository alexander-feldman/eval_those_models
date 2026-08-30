# eval_those_models

A reproducible harness for comparing model behavior and response quality across
controlled prompt, reference, model, and inference-setting variations.

See [the evaluation plan](docs/evaluation-plan.md) for the proposed experiment
design, grading framework, OpenRouter execution architecture, data model, and
implementation phases. See [the metadata schema](docs/metadata-schema.md) for
the normalized SQLite schema, reproducible CSV import, and metric
definitions. [The architecture guide](docs/architecture.md) explains the
repository boundaries.

The versioned ground-truth corpus lives under `data/transcriptions/` and
`data/private/`. It is committed with the project so benchmark inputs, grading,
and dataset revisions remain reproducible.

Current local dataset: 27 recipes, 362 structured ingredients, 26 complete
ingredient lists, and 1 explicitly partial list. The OpenRouter smoke-test
harness and deterministic grader are implemented; calibration against the
recorded pilot and blinded human labels is the next phase.

The first broader title-only baseline is specified in
[`configs/experiments/title-only-baseline-v1.yaml`](configs/experiments/title-only-baseline-v1.yaml),
with its stratification and review protocol documented in
[`docs/experiments/title-only-baseline-v1-20260830.md`](docs/experiments/title-only-baseline-v1-20260830.md).

## Development setup

The project is pinned to Python 3.11 and uses `uv` for Python installation,
virtual environments, and locked dependencies. After installing `uv`, run:

```bash
make setup
make check
```

This creates `.venv` with Python 3.11 without changing macOS's system Python.
Common commands are listed by `make help`. The default test suite uses only
synthetic fixtures and does not require network access or an API key.

## Ground-truth dataset

The canonical store is `data/private/cookbook_eval.sqlite`. Rebuild and
validate it from the preserved wide CSV source with:

```bash
make build-data
make validate-data
```

The equivalent CLI commands are:

```bash
uv run python -m eval_those_models dataset build
uv run python -m eval_those_models dataset validate
```

The source CSV, generated database, importer, and DDL are all versioned so the
normalized dataset can be reproduced and reviewed at any commit.

The recipe metadata also contains provisional, versioned 1–5 ratings
for author popularity, book popularity, recipe popularity within the book,
ingredient-count complexity, and recipe obscurity/unusualness. These fields are
intended for stratified evaluation analysis and include evidence URLs and
annotation notes.

## Deterministic grading

`eval_those_models.grading` exposes the offline phase-2 grader. Call
`grade_response` with untouched model text, the exact reference text, and
ordered `ReferenceIngredient` rows. The result keeps canonical strict ingredient
F1 separate from lenient fuzzy diagnostics, quantities, tier recall, optional
and subrecipe recall, order, text fidelity, response classification, and an
evidence-bearing review queue.

The canonical score accepts normalized-key and versioned-alias matches only.
Conservative fuzzy matches affect the lenient diagnostic score and queue a
strict-versus-lenient disagreement for review. Full-list grading raises
`IncompleteReferenceError` for a reference marked incomplete; callers should
instead construct an explicitly bounded excerpt case.

The default tests use synthetic recipe rows. The tracked ground truth is used
only for explicit integration checks; raw run artifacts remain ignored.

Before calibrating or running the grader, audit that every exact private
reference line parses back to its structured identity and quantity fields:

```bash
uv run python -m eval_those_models dataset audit-grading
```

The command reports only recipe IDs, ingredient positions, and issue kinds; it
does not print protected reference text.

## Experiment harness

Inspect a complete experiment matrix without contacting OpenRouter:

```bash
uv run python -m eval_those_models plan configs/experiments/smoke-test.yaml
```

The planner loads recipe titles from the reference database, excludes incomplete
references, checks title-only prompts for protected-text leakage, generates
content-addressed case IDs, and prints conservative token and cost ceilings.

Execution requires both a configured budget and an explicit paid-request
acknowledgement:

```bash
export OPENROUTER_API_KEY=...
uv run python -m eval_those_models run configs/experiments/smoke-test.yaml --execute
```

Before dispatch, the runner freezes the live model and endpoint catalogs and
refuses unavailable routes, unsupported parameters, or provider-specific prices
above the configured ceilings. The checkout must be clean, and the configured
budget reserves the maximum number of retries at conservative token ceilings.
Requests run with bounded concurrency. Every start, failure, retry, and untouched
successful response is appended durably to private JSONL under `artifacts/runs/`;
API credentials are never serialized.

Optional tool profiles can make tool availability part of the case identity.
The initial implementation supports bounded OpenRouter server-side web search
and fails closed unless its per-request price can be verified during preflight.
See the [auto web-search pilot](docs/experiments/web-search-auto-pilot-20260830.md)
for the first cross-model findings and the resulting budget-safety changes.
The next planned study is
[Experiment 1: source-assisted recipe reconstruction](docs/experiments/experiment-1-source-assisted-reconstruction-plan.md).
Its first [Gate B calibration report](docs/experiments/experiment-1-gate-b-20260830.md)
compares source-assisted behavior with Title-only baseline v1.
