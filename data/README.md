# Data boundaries

`private/` contains the canonical local CSV and SQLite reference data.
`transcriptions/` contains user-supplied source transcriptions. Both directories
are ignored and must not be committed.

Tracked tests use only synthetic fixtures under `tests/fixtures/`. A future
`references.manifest.yaml` may contain non-protected metadata and content hashes,
but not the reference text itself.
