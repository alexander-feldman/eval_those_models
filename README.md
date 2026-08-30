# eval_those_models

A reproducible harness for comparing model behavior and response quality across
controlled prompt, reference, model, and inference-setting variations.

See [the evaluation plan](docs/evaluation-plan.md) for the proposed experiment
design, grading framework, OpenRouter execution architecture, data model, and
implementation phases. See [the metadata schema](docs/metadata-schema.md) for
the normalized private SQLite schema, reproducible CSV import, and metric
definitions. [The architecture guide](docs/architecture.md) explains the
repository boundaries.

User-supplied ground truth is kept locally under `data/transcriptions/` and
`data/private/`; both are excluded from Git to avoid redistributing source text.

Current local dataset: 27 recipes, 362 structured ingredients, 26 complete
ingredient lists, and 1 explicitly partial list. The next implementation phase
is the 24-call OpenRouter smoke-test harness described in the plan.

## Development setup

The project is pinned to Python 3.11 and uses `uv` for Python installation,
virtual environments, and locked dependencies. After installing `uv`, run:

```bash
make setup
make check
```

This creates `.venv` with Python 3.11 without changing macOS's system Python.
Common commands are listed by `make help`. The default test suite uses only
synthetic fixtures and does not require private data, network access, or an API
key.

## Private dataset

The canonical local store is `data/private/cookbook_eval.sqlite`. Rebuild and
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

Both database and source CSV stay ignored and private. The tracked importer and
DDL make the normalization reproducible without publishing cookbook text.

The private recipe metadata also contains provisional, versioned 1–5 ratings
for author popularity, book popularity, recipe popularity within the book,
ingredient-count complexity, and recipe obscurity/unusualness. These fields are
intended for stratified evaluation analysis and include evidence URLs and
annotation notes.
