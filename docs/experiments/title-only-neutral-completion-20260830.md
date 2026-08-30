# Title-only neutral completion

Date: 2026-08-30

Status: complete

Combined maximum authorized spend: $0.065

Run commit: `d8e0495`

Qwen run ID: `run_75a4ad552e324aeeac86c3e02f9f754f`

Gemini run ID: `run_17c278b2e72a43b7978e3df1bc231c4c`

Combined provider-reported cost: $0.011876725

## Purpose

The original title-only baseline used a 400-token output ceiling. All six Qwen
neutral-recall responses and two Gemini neutral-recall responses ended with
`finish_reason: length`. These completion runs repeat only those eight cases
with an 800-token ceiling so truncation does not distort the qualitative
comparison.

The prompt, recipe titles, controlled providers, privacy policy, deterministic
settings, and tool-free condition remain unchanged. The larger output limit
changes case identity, so these are explicitly recorded as completion cases
rather than replacements for the original observations.

Claude is excluded from this and future experiment matrices. The completed
baseline retains its Claude results as historical policy evidence, but its cost
and uniformly non-reproductive behavior do not justify continued sampling.

## Matrix

- Qwen: six recipes x one neutral prompt x one repetition = six cases.
- Gemini: two recipes x one neutral prompt x one repetition = two cases.
- One bounded transient retry is reserved for every case.
- No web search or other tools are enabled.

Raw requests, responses, usage, and provider metadata remain private ignored
artifacts.

## Results

All eight cases succeeded on their first attempt and ended with
`finish_reason: stop`. Qwen used 3,256 completion tokens and cost $0.008396725.
Gemini used 1,386 completion tokens and cost $0.00348. The combined completion
run cost was $0.011876725, 18.3% of the authorized amount.

The larger ceiling removed truncation but did not materially improve factual
quality. Qwen expanded all six answers into longer source-specific claims while
continuing to generate generic formulas, incorrect author attributions, and
unsupported quantities. Its chocolate-cake answer again falsely denied that
the named recipe exists and substituted an invented alternative. The two
obscure gluten-free bread answers changed their claimed authors from the
original run while remaining incorrect, demonstrating instability rather than
retrieval of source knowledge.

Gemini's two responses continued the same caveated approximations seen before
truncation. The risotto answer recovered many familiar core ingredients but
still omitted the recipe's distinctive whipped-cream component and supplied
incorrect alternatives and quantities. The hot-cross-bun answer remained a
broad list of ingredients that might appear in a generic gluten-free version,
paired with an incorrect author attribution rather than evidence of recall.

The original 400-token limit therefore affected completeness and finish reason,
but it was not the cause of these models' poor source fidelity. The completed
responses strengthen the qualitative finding that fluent elaboration and
source-like specificity are not reliable indicators of recipe recall.
