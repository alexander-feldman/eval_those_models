# Configuration

Configurations are grouped by purpose:

- `experiments/` defines versioned evaluation matrices and budgets.
- `models/` defines frozen model and provider-routing settings.
- `prompts/` defines immutable, versioned prompt templates.

The first validated configuration is `experiments/smoke-test.yaml`. It expands
to 24 title-only calls (2 recipes x 2 prompts x 3 models x 2 repetitions).
Pricing values are authorization ceilings: execution checks the live catalog
and stops if a selected model is absent or more expensive.

`experiments/title-only-baseline-v1.yaml` expands the first broader controlled
baseline: 6 stratified recipes x 3 prompts x 5 model families x 1 repetition,
with no tools and a $0.95 maximum budget including one reserved retry.

Tool-enabled experiments define immutable `tool_profiles`. Web-search profiles
record the engine, call and result caps, content limit, conservative input-token
allowance, and per-model search-price ceiling so search participates in both
case identity and budget authorization.

Do not put API keys or private reference text in these files.
