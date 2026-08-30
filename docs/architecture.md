# Project architecture

The repository is a Python 3.11 application using a `src` package layout.

- `configs/` contains versioned experiment inputs without secrets or reference text.
- `data/` contains local private inputs and a tracked description of their boundaries.
- `src/eval_those_models/` contains all reusable application code and the CLI.
- `tests/` contains offline unit, integration, and provider-contract tests.
- `artifacts/` contains ignored generated catalogs, runs, reports, and reviews.
- `scripts/` contains compatibility wrappers only; application logic belongs in `src/`.

The default test suite must not require private cookbook data, credentials, network
access, or paid API calls. Private-data validation and live-provider checks are
explicit operations.
