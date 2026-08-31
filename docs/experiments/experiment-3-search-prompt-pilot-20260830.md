# Experiment 3 web-search prompt pilot

Date: 2026-08-30

Status: superseded

> **Superseded:** The final study rejected this pilot's five-to-twelve-item
> contract because it mechanically capped recall on 16- and 26-row recipes.
> Its prompt-development history and spend remain valid, but its proposed
> capped evaluation and scale-up criteria must not be used. See the
> [balanced uncapped final report](experiment-3-web-search-final-20260830.md).

Maximum authorized spend: $0.20

Provider-reported spend: $0.1439934018

## Question

This pilot combined the main lessons of Experiments 1 and 2 before scaling a
third experiment. It retained Experiment 2's concise, identity-only hypothesis
format while testing whether web search could improve factual ingredient recall
without reintroducing Experiment 1's verbose output, false attribution, and
same-dish-variant problems.

The recorded Experiment 2 no-search results remain the control. They were run
immediately before this pilot and will not be repeated. The exact winning prompt
was preserved without any wording change in the first search-enabled condition.

## Development cases and models

Two deliberately contrasting recipes were used:

- `BASIC ALMOST-NO-STIR RISOTTO`, for which search reliably finds an exact or
  explicitly attributed public ingredient list; and
- `Fennel Seed and Olive Oil Tortas (Tortas de Aceite y Anís)`, for which prior
  work found cookbook metadata and conventional wheat-flour variants but no
  exact or attributed public source for the named gluten-free recipe.

Qwen was used for broad prompt exploration because of its lower price. DeepSeek
then checked whether the strongest behaviors generalized across model families.
All requests used controlled Alibaba inference routes, disabled fallbacks and
reasoning, requested `data_collection: deny`, and used bounded auto search.

## Prompt progression

Round 1 compared three qualitatively different strategies:

1. the exact Experiment 2 winner with search merely available;
2. an explicit search-first instruction; and
3. a source-skeptical instruction that distinguished exact sources from
   metadata and variants.

Round 2 tested three responses to the source-skeptical prompt's recall collapse
on the no-source case:

1. use only exact or attributed evidence, otherwise fall back to an ordinary
   hypothesis;
2. form a hypothesis first and use search to check it; and
3. prioritize quoted-title extraction, otherwise ignore variants and fall back.

The cross-model rounds then separated tool use from output-shape compliance. A
silent evidence gate produced clean output but caused DeepSeek to skip search.
Making a search-tool call explicitly mandatory retained search while also
producing a clean list-only answer.

## Runs and spend

| Round | Run ID | Cases | Result | Cost |
|---|---|---:|---|---:|
| 1 | `run_e808a9aaf944426192775cab80d90f8f` | 6 | 6 succeeded | $0.0426925000 |
| 2 | `run_d25acc1d11cf432fb5ef751d12b0951d` | 6 | 6 succeeded | $0.0516479250 |
| 3a | `run_b6d3520057254c33bb6a01d4cac4ca08` | 2 | 1 succeeded; 1 transient 429 | $0.0093086800 |
| 3b | `run_6595aa4ef08f414589fe603d5b7db386` | 1 | succeeded | $0.0088411360 |
| 3c | `run_962abc88ad87430f9e942852ec8b8cfa` | 1 | bounded retry succeeded | $0.0092372416 |
| 4 | `run_85f251e33e794027bc6dbfbd8d8ee156` | 2 | 2 succeeded; neither searched | $0.0010245312 |
| 5 | `run_1a88465272a04fe9bad4e1af0aa7ac77` | 2 | 2 succeeded and searched | $0.0212413880 |
| **Total** | | **20** | **19 successes; 1 transient failure** | **$0.1439934018** |

The one failed call was a zero-cost DeepSeek/Alibaba HTTP 429. Its single-case
retry succeeded. Raw requests, responses, citations, usage, and search excerpts
remain in ignored private artifacts.

## Findings

### Search availability is not the same as search use

With the untouched Experiment 2 prompt and a search tool available, Qwen
searched once for risotto but did not search for tortas. A search-enabled arm
that does not require tool use therefore measures model-managed tool uptake as
well as retrieval quality. That remains a useful product-behavior condition,
but it is not a reliable search treatment.

### Exact public evidence produced a large qualitative improvement

For risotto, search repeatedly found the Washington Post adaptation from *The
Food Lab*, the corresponding Serious Eats page, and an Eat Your Books index.
Search-assisted Qwen answers consistently recovered the distinctive whipped
heavy cream plus garlic, shallots, olive oil, wine, butter, stock, rice, cheese,
and seasonings. The final DeepSeek answer contained nine clean, recipe-specific
identities and omitted only the seasoning/garnish tail under the twelve-item
cap.

This is visibly stronger than the recorded no-search hypotheses, which tended
toward a generic risotto and sometimes added onion, mushrooms, or saffron while
missing heavy cream. The current strict matcher substantially undercounts this
gain because it does not automatically equate such forms as `chicken broth`
with the longer reference stock key or split salt and pepper with their combined
reference row. Human identity adjudication is required in the scaled run.

### Variants did not reveal the obscure recipe's specific formula

No prompt found an exact or attributed source for the gluten-free tortas. Search
returned cookbook descriptions or conventional variants using wheat flour.
Answers converged on fennel, olive oil, salt, sugar, water, and yeast, but did
not recover the named recipe's brown-rice flour, millet flour, potato starch,
and psyllium system. DeepSeek also imported aniseed from variants. The final
prompt recovered xanthan gum, but its generic `gluten-free all-purpose flour`
still concealed the important flour identities.

Search is therefore likely to help strongly when an exact or attributed source
exists and help little, or cause variant anchoring, when it does not. Source
findability must be a reported effect modifier rather than an incidental note.

### Prompt constraints trade off against one another

- Source-skeptical wording reduced Qwen's tortas answer to two ingredients,
  violating the five-to-twelve contract.
- Explicit fallback wording restored the requested list length.
- DeepSeek narrated its search and source classification despite ordinary
  `no preamble` instructions.
- Requiring silent classification and list-only output removed the prose, but
  DeepSeek then skipped search entirely.
- Explicitly requiring at least one tool call before the final answer achieved
  both tool use and clean list-only output in the final two cases.

## Frozen search prompt candidate

The recommended deliberately search-using condition is:

> Before producing the final answer, you must call the web-search tool at least
> once to look for the exact named recipe or a clearly attributed adaptation of
> “{recipe_name}” from “{cookbook_title}”. After the tool returns, silently
> classify results as exact recipe, attributed adaptation, cookbook metadata,
> same-dish variant, or unrelated. Use ingredient evidence only from an exact
> recipe or attributed adaptation. If neither is found, ignore the retrieved
> variants and use your pre-search best-effort hypothesis for this specific
> recipe. Your entire final answer must be exactly five to twelve normalized
> ingredient names in alphabetical order, one per line. Begin immediately with
> the first ingredient and end after the last. Do not reveal searches, sources,
> classification, reasoning, uncertainty, or caveats; do not include quantities,
> prose, directions, citations, headings, or bullets. Do not abstain.

This is not proven optimal. It is the first tested wording that made DeepSeek
both search and obey the concise output contract on the two contrasting cases.
Its evidence gate did not fully eliminate implicit variant anchoring, so source
review remains essential.

## Recommended Experiment 3 design

Use the recorded Experiment 2 concise-identity results as the no-search control;
do not rerun them. Compare two new search conditions:

| Condition | Prompt | Intended measurement |
|---|---|---|
| E2-N0 | recorded no-search result | frozen control |
| E3-S0 | exact Experiment 2 winning prompt, unchanged, with search available | ordinary model-managed search uptake |
| E3-S1 | frozen required-search prompt above | deliberate evidence-gated search |

Gate A should use the same six recipes and four model families from the
Experiment 2 universal-prompt runs. That gives 48 new paid cases: 6 recipes x 4
models x 2 search conditions. The two development recipes remain in the matrix
for continuity; the other four recipes serve as immediate prompt-generalization
checks. Run one model configuration at a time and reconcile spend before the
next route, especially for Claude.

Advance to the 17-recipe unseen set only if Gate A meets all of these thresholds:

1. at least 90% of E3-S1 cases actually invoke search;
2. at least 90% return a clean five-to-twelve-item list;
3. no more than 5% make a false exact-or-attributed source claim on human review;
4. normally terminated responses in at least 90% of cases; and
5. human-adjudicated ingredient F1 does not fall relative to E2-N0 overall.

The primary accuracy contrast is E3-S1 minus the recorded E2-N0 ingredient F1
within model and recipe. E3-S0 measures whether merely offering the tool helps
and how often each model chooses to use it. Report precision, recall, F1,
unsupported candidates, primary-ingredient recall, tool-use rate, output-shape
compliance, search cost, latency, and normal completion separately.

Every retrieved URL should receive one blinded human relevance label: `exact`,
`attributed_adaptation`, `cookbook_metadata`, `same_dish_variant`, or
`unrelated`. Report accuracy separately for cases with exact/attributed evidence
and cases with variants or metadata only. Do not pool those regimes into a
single conclusion about whether search works.
