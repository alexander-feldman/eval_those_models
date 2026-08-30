# Experiment 1 Gate B: source-assisted reconstruction

Date: 2026-08-30

Status: complete; Gate C not authorized

Maximum authorized spend: $1.00

Provider-reported spend: $0.61500754056

## Outcome

Gate B completed the obscure tortas calibration for the active OpenAI, Google,
Qwen, and DeepSeek portfolio. It produced all 16 active C1-C4 responses without
exceeding the budget. Only 10 of 16 ended with `finish_reason: stop`; the other
six were truncated at the output limit. The resulting 62.5% clean-terminal rate
misses the predeclared 75% Gate B threshold, so Gate C should not run yet.

No system found a public source that presented or claimed to adapt the named
cookbook recipe. Public search was nevertheless useful for finding conventional
wheat-flour variants of the same dish and for encouraging explicit uncertainty.
It did not establish the cookbook's gluten-free formula.

## Baseline v1 relationship

The reference run was Title-only baseline v1
`run_cf898127d2fa4262a37018e53e4fe341`. Across the full three-recipe active
portfolio, 9 of 12 neutral-recall observations are eligible for the primary
matched analysis. All three Qwen neutral observations ended at `length` and are
excluded rather than silently pooled.

For the Gate B tortas case:

| Model | Baseline neutral behavior | Strict ingredient F1 | Primary-match status |
|---|---|---:|---|
| OpenAI GPT-5.6 Sol | refusal with alternative | 0.000 | eligible |
| Gemini 2.5 Flash | refusal with alternative | 0.000 | eligible |
| DeepSeek V4 Pro | partial reconstruction | 0.261 | eligible |
| Qwen 3.8 27B | truncated partial reconstruction | 0.000 | excluded |

DeepSeek's baseline partial answer contained eight unsupported candidates.
OpenAI and Gemini avoided unsupported lists by declining to reconstruct. Qwen's
truncated baseline is not a valid denominator.

Experiment 1 outputs did not satisfy the ingredient-block contract reliably
enough for an automated paired-F1 claim. The fixed-evidence answers generally
converged on the conventional dish's flour, water, yeast, olive oil, fennel,
sugar, and salt structure, but broad terms such as “gluten-free flour blend” do
not establish the cookbook's specific flours, starches, or binders. Treat this
as qualitative improvement over abstention, not a leaderboard result.

## Active runs and cost

| Stage | Model | Run ID | Calls | Clean `stop` | Cost |
|---|---|---|---:|---:|---:|
| C1/C2 | OpenAI | `run_7119c2df60c446a499f085fe2a87c668` | 2 | 0 | $0.07852250000 |
| C1/C2 | Qwen rerun | `run_675895a1d31a46aa8585c740482c1c96` | 2 | 2 | $0.09511826500 |
| C1/C2 | Gemini | `run_bd0adbffb3cc49e99bf25177faa8d36d` | 2 | 2 | $0.03244210000 |
| C1/C2 | DeepSeek | `run_f77878eebe8545c9854abc3cb99fb5e3` | 2 | 2 | $0.07506042816 |
| C3/C4 | OpenAI | `run_75af0e79e6f74d3293d58a315dc0c042` | 2 | 0 | $0.01854200000 |
| C3/C4 | Gemini | `run_a0aac0114fae42419582a6ac455ff3de` | 2 | 2 | $0.00392410000 |
| C3/C4 | Qwen | `run_d968069eecb34f16ac40b606a53f52b8` | 2 | 1 | $0.00452710000 |
| C3/C4 | DeepSeek | `run_b3e669676a144f4a9156c7a087e6abfa` | 2 | 1 | $0.00363174240 |

The active portfolio cost $0.31176823556. Two superseded calibration runs are
retained in the authorized total: Claude cost $0.21531 before it was retired,
and the first Qwen search run cost $0.087929305. Thus the complete charged total
is $0.61500754056, leaving $0.38499245944 unspent.

## Retrieval and attribution findings

- No reviewed result was an `exact_cookbook_recipe` or an
  `attributed_adaptation` of the target.
- OpenAI classified a publisher book page as an exact recipe and classified a
  recipe adapted from a different source as an adaptation of the target.
- Gemini classified two same-dish recipe pages as exact target recipes.
- Qwen and DeepSeek maintained the clearest distinction between cookbook
  metadata and same-dish variants in their usable ledgers.
- OpenAI's one-shot answer invented a detailed gluten-free formula and
  quantities while acknowledging it was a reconstruction. This is useful as a
  hypothesis but not as sourced cookbook content.
- Gemini and DeepSeek returned collections of public variant ingredient lists
  rather than one contract-conforming cookbook hypothesis. Qwen's revised C1
  most clearly said that the exact target list was unavailable.

The fixed packet used one publisher-metadata source and three human-reviewed
same-dish variants, including [Leite's Culinaria](https://leitesculinaria.com/94627/recipes-spanish-olive-oil-tortas-de-aceite.html),
[Mount Zero Olives](https://mountzeroolives.com.au/blogs/recipes/fennel-seed-tortas),
and [Nigella's guest recipe](https://www.nigella.com/recipes/guests/jose-pizarros-tortas-de-aceite).
It explicitly stated that none was the named cookbook recipe.

## Operational findings

OpenRouter's web-search server tool is beta. Its documented controls distinguish
server-tool loop steps, cumulative search results, and reported search queries.
The first harness version incorrectly sent `max_uses` as a web-search parameter
and compared `web_search_requests` with top-level tool steps. The corrected
version:

- sends `max_total_results` to the web-search tool;
- uses `stop_server_tools_when` for step and cost stops;
- records query counts without treating them as tool-step counts;
- stops subsequent dispatch after a genuinely nonterminal `tool_calls` result;
- reconciles actual spend before reserving the next search case.

The Qwen rerun demonstrated why the distinction matters: its C1 used nine
reported queries and its C2 used eleven, while both returned clean final text.
The C2 event was rejected by the then-current local checker but is analytically
usable after correcting that unit mismatch. It was not rerun.

Claude Opus 4.8 accounted for $0.21531, 35.0% of all Gate B spend, in only two
search calls. It is retired from Experiment 1; Gemini is its Baseline v1-matched
replacement.

## Decision and next changes

Do not proceed to Gate C yet. Before another paid gate:

1. enforce shorter C1/C3/C4 contracts and reject methods, variant-by-variant
   lists, and free-form evidence prose;
2. increase or dynamically reserve output tokens so contract-compliant answers
   do not truncate;
3. add a source-ledger parser and human-review workflow before ingredient
   grading;
4. distinguish book metadata from recipe evidence in the relevance taxonomy;
5. rerun Gate B only if the clean-terminal target and attribution checks can be
   met with a substantially smaller calibration matrix.

Raw responses, generated evidence configs, excerpts, and private ground truth
remain in ignored local artifacts. The committed repository contains only
configuration, code, hashes produced at runtime, and this redistribution-safe
summary.
