# Data boundaries

`private/` contains the canonical CSV and SQLite reference data.
`transcriptions/` contains user-supplied source transcriptions. Both directories
are versioned with the repository to keep the evaluation corpus reproducible.

Default tests use only synthetic fixtures under `tests/fixtures/`; dataset
integration checks explicitly load the tracked reference corpus.
