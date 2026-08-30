# Title-only neutral completion

Date: 2026-08-30

Status: planned

Combined maximum authorized spend: $0.065

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
artifacts. Update this record with run IDs, costs, finish reasons, and a direct
comparison to the truncated responses after execution.
