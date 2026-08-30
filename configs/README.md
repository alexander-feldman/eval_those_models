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

`experiments/qwen-neutral-completion-v1.yaml` and
`experiments/gemini-neutral-completion-v1.yaml` repeat only the eight neutral
baseline cases truncated by the original 400-token ceiling. They use an
800-token ceiling and exclude Claude.

Tool-enabled experiments define immutable `tool_profiles`. Web-search profiles
record the engine, call and result caps, content limit, conservative input-token
allowance, and per-model search-price ceiling so search participates in both
case identity and budget authorization.

Experiment 1 Gate B splits the four auto-search model routes into separate
`experiment-1-gate-b-search-*.yaml` configurations. Their caps sum to $0.76 of
the $1.00 Gate B authorization, leave $0.24 for the evidence-only stage, and
permit the differing native/fallback query counts observed in the pilot.

Do not put API keys or private reference text in these files.
