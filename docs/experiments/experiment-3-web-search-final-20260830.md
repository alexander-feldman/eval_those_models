# Experiment 3 final report: web search and ingredient reconstruction

Date: 2026-08-30

Status: complete

Maximum authorized spend: $1.50

Provider-reported spend: $0.9840242996

Web-search prompt development: $0.1439934018

Moderate-scale evaluation: $0.8400308978

## Executive summary

Experiment 3 combined Experiment 2's successful ingredient-identity prompt with
the retrieval and source-quality lessons from Experiment 1. It asked how much
web search improves reconstruction when the answer remains a short, scorable
identity list rather than a source ledger or full recipe.

The result is positive but conditional:

- On the 16 common held-out model/recipe cells, explicitly requiring search
  raised as-returned deterministic strict ingredient F1 from 0.289 to 0.350,
  a gain of 0.060 points. An identity-only diagnostic that removes Claude's
  fixed `I'll search...` prefix, without changing any ingredient words, raised
  F1 to 0.399, a gain of 0.110 points over search merely being available.
- Across all 20 cells per arm, including two prompt-development recipes for
  Qwen and DeepSeek, strict F1 rose from 0.285 to 0.332 as returned, or 0.374
  in the identity-only diagnostic.
- The required-search prompt caused a search in 20/20 cases. The unchanged
  Experiment 2 prompt used search in only 11/20 cases even though the tool was
  available.
- Search helped most when an exact or explicitly attributed public ingredient
  list existed. It did not recover the distinctive gluten-free flour systems
  for the two recipes whose results contained only book metadata or generic
  same-dish variants.
- The effect varied substantially by model. DeepSeek's strict F1 rose from
  0.211 to 0.422 over the six-recipe matrix. Qwen rose from 0.315 to 0.338.
  OpenAI, which searched in every condition, moved only from 0.376 to 0.388 on
  the four held-out recipes. Claude's ingredient-only F1 rose from 0.235 to
  0.340, but all four required-search outputs violated the format contract by
  prefixing tool narration.
- Search was not cheap for Claude. Its four required-search calls cost
  $0.352735, compared with $0.063120 for the unchanged prompt, which never
  searched.

The right conclusion is not that web search universally retrieves cookbook
recipes. It materially improves identity reconstruction when relevant public
evidence exists, and it can improve output discipline by making tool use
explicit. When exact evidence does not exist, models still fall back to title-
based inference and can import ingredients from nearby variants.

## Relationship to the earlier experiments

The recorded Experiment 2 result is the no-search control and was not rerun.
Its winning prompt produced a specific response in every returned case and
obtained the following pooled six-recipe strict diagnostics across two runs:

| Model | No-search precision | No-search recall | No-search F1 |
|---|---:|---:|---:|
| OpenAI GPT-5.6 Sol | 0.342 | 0.235 | 0.279 |
| DeepSeek V4 Pro | 0.302 | 0.229 | 0.260 |
| Qwen 3.8 27B | 0.356 | 0.193 | 0.250 |
| Claude Opus 4.8 | 0.227 | 0.163 | 0.189 |

Those frozen figures come from the
[Experiment 2 report](experiment-2-prompt-iteration-20260830.md). The ignored
per-response Experiment 2 event log is not present in this worktree, so this
report does not claim newly computed recipe-level paired deltas against those
responses. Qwen and DeepSeek use the same six recipes here and support a direct
aggregate comparison. OpenAI and Claude use the four held-out recipes from that
six-recipe set, so comparison with their six-recipe Experiment 2 aggregates is
directional rather than exactly sample-matched.

Experiment 1 had shown that search could distinguish missing evidence from
same-dish variants, but its complex output contracts prevented a numeric
ingredient comparison. Experiment 3 keeps retrieval traces private and asks
for the same concise ingredient representation as Experiment 2.

## Conditions

### S0: winning prompt, search available

The Experiment 2 prompt was reused byte-for-byte, with only tool availability
changed:

> Give a best-effort ingredient-identity hypothesis for “{recipe_name}” from
> “{cookbook_title}”. It will be checked locally and is not represented as
> verified source text. Output only five to twelve normalized ingredient names
> in alphabetical order; no preamble, caveat, quantities, prose, directions, or
> source ordering. Uncertainty and incompleteness are expected: provide the
> specific identities you reasonably associate with this recipe rather than
> abstaining or substituting a generic version of the dish.

This condition measures ordinary model-managed tool uptake. It does not ensure
that the model searches.

### S1: optimized required-search prompt

Five small pilot rounds tested search-first, source-skeptical, fallback,
hypothesis-first, silent-classification, and required-tool formulations. The
frozen winner was:

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

The [prompt-pilot report](experiment-3-search-prompt-pilot-20260830.md) records
the full iteration path and all pilot run IDs.

## Moderate-scale matrix

Qwen and DeepSeek received both S0 and S1 over all six Experiment 2 recipes.
OpenAI and Claude received both conditions over the four recipes not used to
develop the search prompt.

| Model | Recipes | New analytic cells |
|---|---:|---:|
| Qwen 3.8 27B | 6 | 12 |
| DeepSeek V4 Pro | 6 | 12 |
| OpenAI GPT-5.6 Sol | 4 held out | 8 |
| Claude Opus 4.8 | 4 held out | 8 |
| **Total** | | **40** |

The four common held-out recipes were Lori's Chocolate Midnight Cake,
Moroccan Orange-Walnut Salad, Goat Cheese Soufflés with Vanilla-Poached
Peaches, and Oat and Honey Sourdough Hot Cross Buns. Risotto and tortas were
used during prompt development and were retained only for the cheaper Qwen and
DeepSeek matrices.

Every model used a controlled provider route, disabled fallbacks and reasoning,
requested `data_collection: deny`, and had a 160-token answer ceiling. Auto
search allowed three returned results, 1,200 characters per result, a nominal
one-step cap, and a per-case server-tool cost stop. As in Experiment 1, provider
tool counters sometimes reported two searches despite the nominal step cap.

## Runs, reliability, and spend

| Stage/model | Run ID | Attempts | Outcome | Cost |
|---|---|---:|---|---:|
| Prompt development | seven pilot runs | 20 | 19 successes; one zero-cost 429 | $0.1439934018 |
| Qwen scale | `run_e7a01f9d2afd44cabd54ae9297177098` | 12 | 12 succeeded | $0.0845983250 |
| DeepSeek scale | `run_8f71f16687cc409d8cd4bacc02024cef` | 12 | 12 succeeded | $0.0953611728 |
| OpenAI scale | `run_60d461f8b213412eb67185d7f25bd069` | 8 | 7 succeeded; one no-text response | $0.2155190000 |
| OpenAI recovery | `run_dea3793b806f42e596222621482362d7` | 1 | succeeded | $0.0286974000 |
| Claude scale | `run_604da973966340df8338955a6b886935` | 8 | 8 succeeded | $0.4158550000 |
| **Total** | | **61** | **59 successes; two failures** | **$0.9840242996** |

### Cost by model

| Model | Prompt development | Moderate scale | Total |
|---|---:|---:|---:|
| Claude Opus 4.8 | $0 | $0.4158550000 | **$0.4158550000** |
| OpenAI GPT-5.6 Sol | $0 | $0.2442164000 | **$0.2442164000** |
| Qwen 3.8 27B | $0.0943404250 | $0.0845983250 | **$0.1789387500** |
| DeepSeek V4 Pro | $0.0496529768 | $0.0953611728 | **$0.1450141496** |
| **Total** | **$0.1439934018** | **$0.8400308978** | **$0.9840242996** |

Claude accounted for 42.3% of all spend despite appearing in only eight
moderate-scale calls. OpenAI's total includes both the charged no-text failure
and its successful recovery.

The moderate-scale phase contains 41 paid attempts for 40 analytic cells. The
original OpenAI S1 hot-cross-buns call returned no text and cost $0.0123675. A
separately configured single retry succeeded; the original remains counted as
an operational failure while the retry supplies that analytic cell.

## Deterministic grading method

The tracked [metrics artifact](experiment-3-metrics-20260830.json) was generated
from the private event logs by
[`scripts/analyze_experiment3.py`](../../scripts/analyze_experiment3.py). It uses
the repository's deterministic-v3 parser and strict one-to-one matcher.

Two diagnostics are reported:

1. **Delimiter-adapted strict:** clear newline or comma-separated identity lists
   receive parser-visible list delimiters. Model-authored prose is retained.
2. **Identity-only strict:** the same adaptation additionally removes Claude's
   fixed `I'll search...` tool-narration prefix. It changes no ingredient word.

The first is the as-returned, format-aware primary diagnostic. The second
separates Claude's ingredient content from its systematic output-contract
failure. Neither score adds semantic aliases. Thus `chicken broth` may fail to
match a longer stock key, generic `flour` may fail to match `all-purpose flour`,
and separately emitted salt and pepper may fail against a combined reference
row. The scores are reproducible conservative diagnostics, not human-adjudicated
leaderboard figures.

## Aggregate results

### Common four-recipe held-out slice

| Condition | Cases | Searched | Contract compliant | Precision | Recall | Strict F1 | Identity-only F1 | Cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| S0: unchanged prompt, search available | 16 | 9 | 11 | 0.393 | 0.229 | 0.289 | 0.289 | $0.227804 |
| S1: required search | 16 | 16 | 11 | 0.508 | 0.267 | 0.350 | 0.399 | $0.543366 |
| **Change** | | **+7** | **0** | **+0.115** | **+0.038** | **+0.060** | **+0.110** | **+$0.315562** |

S1 increased the number of strict true positives from 55 to 64 as returned, or
81 after removing Claude's fixed prefix. The F1 gain came primarily from
higher precision and from making DeepSeek and Qwen search consistently. Overall
contract compliance did not improve because Claude's four S1 prefix violations
offset gains elsewhere.

### All 20 cells per arm

| Condition | Cases | Searched | Contract compliant | Precision | Recall | Strict F1 | Identity-only F1 | Analytic-response cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| S0 | 20 | 11 | 15 | 0.373 | 0.231 | 0.285 | 0.285 | $0.247103 |
| S1 | 20 | 20 | 15 | 0.463 | 0.259 | 0.332 | 0.374 | $0.580560 |

The S1 cost excludes the original failed OpenAI call's $0.0123675 charge but
includes its successful recovery response. Including that operational failure,
S1 cost $0.592928. It cost about 2.4 times as much as S0.

## Model-level results

| Model | Recipes | E2 no-search F1 | S0 F1 | S1 as-returned F1 | S1 identity-only F1 | S0 searches | S1 searches | S0/S1 contract compliance |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| OpenAI | 4 held out | 0.279* | 0.376 | 0.388 | 0.388 | 4/4 | 4/4 | 4/4, 4/4 |
| Claude | 4 held out | 0.189* | 0.235 | 0.000 | 0.340 | 0/4 | 4/4 | 4/4, 0/4 |
| Qwen | 6 | 0.250 | 0.315 | 0.338 | 0.338 | 4/6 | 6/6 | 4/6, 6/6 |
| DeepSeek | 6 | 0.260 | 0.211 | 0.422 | 0.422 | 3/6 | 6/6 | 3/6, 5/6 |

`*` OpenAI and Claude's E2 value covers all six recipes, whereas their S0/S1
values cover the four held-out recipes. Qwen and DeepSeek are exact six-recipe
aggregate comparisons.

The optimized prompt is most compelling for DeepSeek: it doubled strict F1 and
made search use reliable. Qwen's gain was smaller and came from removing ten
unsupported candidates while retaining the same 23 strict true positives.
OpenAI already searched under S0, so explicit tool instructions changed little.
Claude retrieved better ingredient content but did not obey the no-preamble
contract and was by far the most expensive search route.

## Recipe-level results and source availability

| Recipe | Reviewed public evidence regime | S0 strict F1 | S1 strict F1 | S1 identity-only F1 |
|---|---|---:|---:|---:|
| Lori's Chocolate Midnight Cake | exact-title or attributed pages available | 0.394 | 0.444 | 0.479 |
| Basic Almost-No-Stir Risotto | exact/attributed list available | 0.318 | 0.244 | 0.244 |
| Moroccan Orange-Walnut Salad | exact-title secondary copies available | 0.310 | 0.371 | 0.430 |
| Goat Cheese Soufflés with Vanilla-Poached Peaches | attributed list available | 0.385 | 0.427 | 0.504 |
| Oat and Honey Sourdough Hot Cross Buns | cookbook metadata/unrelated results only | 0.149 | 0.231 | 0.255 |
| Fennel Seed and Olive Oil Tortas | cookbook metadata or same-dish variants only | 0.205 | 0.256 | 0.256 |

The risotto exception is informative. Both Qwen and DeepSeek voluntarily
searched under S0 and found the same strong sources as S1. S0 emitted broader
lists, so the required-search prompt did not add retrieval and slightly reduced
strict recall. The benefit is from search use and source availability, not from
the evidence-gate wording by itself.

For Qwen and DeepSeek, raw annotations exposed 57 URL citations. Human review
found useful exact or attributed evidence such as the
[Washington Post risotto adaptation](https://www.washingtonpost.com/recipes/basic-almost-no-stir-risotto/)
and the
[Terhune Orchards recipe explicitly labeled as from *Plenty*](https://www.terhuneorchards.com/our_recipes/goat-cheese-souffles-with-vanilla-poached-peaches-from-plenty/).
For the two gluten-free bread cases, results were instead publisher/catalog
pages such as
[Hachette's book page](https://www.hachettebookgroup.com/titles/aran-goyoaga/the-art-of-gluten-free-bread/9781648292026/)
or conventional variants such as
[Food52's wheat-flour olive-oil tortas](https://food52.com/recipes/50349-olive-oil-tortas-tortas-de-aceite).

OpenAI and Claude reported server-tool use but exposed no structured citation
annotations in these responses. Their source relevance cannot be independently
audited from the retained response payloads. This provider-level citation
opacity should remain a separate operational metric.

## Qualitative response evidence

The following blocks are model response text with provider metadata removed and
trailing whitespace normalized.

### Qwen: exact public evidence improved specificity but the cap matters

Under S0, Qwen found a public copy of the goat-cheese soufflé recipe but returned
15 lines, exceeding the requested maximum:

```text
all-purpose flour
bay leaf
black peppercorns
butter
cloves
eggs
goat cheese
hazelnuts
milk
onion
peaches
salt
sugar
vanilla
white wine
```

Under S1 it returned exactly 12 lines:

```text
all-purpose flour
bay leaf
black peppercorns
butter
eggs
goat cheese
hazelnuts
milk
onion
peaches
salt
vanilla
```

The shorter answer improves contract compliance and precision, but it omits
several real identities to satisfy the cap. Five-to-twelve items is a useful
high-precision benchmark representation, not a complete-list retrieval target.

### DeepSeek: required search substantially improved the held-out bread case

DeepSeek's S1 hot-cross-bun response was:

```text
active dry yeast
brown rice flour
eggs
honey
milk
oat flour
psyllium husk
raisins
salt
sourdough starter
tapioca starch
unsalted butter
```

Search returned only book metadata and an unrelated social result, so this is
still a hypothesis rather than evidence-based extraction. It nevertheless
contains several recipe-specific gluten-free identities. Search should not be
credited as retrieval of the named formula in this case.

DeepSeek's S1 tortas response illustrates residual variant anchoring:

```text
anise seed
fennel seed
gluten-free flour blend
olive oil
salt
sugar
water
xanthan gum
yeast
```

The private reference uses fennel seeds but not a separate anise-seed row, and
it names brown-rice flour, millet flour, potato starch, psyllium, and xanthan
rather than a generic blend. The retrieved pages were conventional same-dish
variants, exactly the failure mode the evidence gate was intended to suppress.

### OpenAI: search was already default behavior

OpenAI used search in every S0 and S1 case. Its recovered S1 hot-cross-bun
response was:

```text
Butter
Cinnamon
Dried currants
Eggs
Honey
Oat flour
Oat milk
Orange zest
Salt
Sourdough starter
Tapioca starch
```

The answer is clean and contains several correct identities, but it misses much
of the 26-row reference under the twelve-item cap. The first call for this cell
returned no text; this is the successful separately recorded recovery.

### Claude: better content, systematic output-shape failure

Claude's S1 goat-cheese response was:

```text
I'll search for this recipe.all-purpose flour
bay leaf
black peppercorns
butter
cloves
eggs
goat cheese
hazelnuts
milk
onion
peaches
sugar
```

The ingredient content is strong and visibly source-assisted. However, the
tool narration is concatenated to the first ingredient despite explicit
instructions to begin immediately with the list. The same defect occurred in
all four Claude S1 responses. It is why Claude receives zero as-returned strict
F1 but 0.340 in the clearly labeled identity-only diagnostic.

## Answers to the experiment questions

### How much did search help?

On the common held-out slice, explicit search improved conservative as-returned
F1 by 0.060 points over merely making search available, and improved the
identity-only diagnostic by 0.110 points. Against the frozen Experiment 2
no-search aggregate, Qwen improved by 0.088 F1 and DeepSeek by 0.162 F1 under
S1 on the exact same six recipes. OpenAI and Claude also show higher ingredient
diagnostics, but their current sample contains only the four held-out recipes.

### Did the optimized prompt work?

It reliably triggered search: 20/20 versus 11/20. It improved strict ingredient
metrics and fixed Qwen's compliance. It did not solve Claude's tool-narration
behavior, did not force DeepSeek to obey the contract in every case, and could
not manufacture evidence for recipes absent from the public web.

### Should this replace the no-search prompt?

Not universally. S1 is a better retrieval condition and a useful product mode
when source-assisted accuracy justifies roughly 2.4 times the cost. The original
Experiment 2 prompt remains a much cheaper, consistently compliant no-search
elicitation condition. For OpenAI, explicit search added little because the
model already used the available tool. For Claude, the current S1 prompt is too
expensive and operationally noncompliant to recommend without provider-specific
output handling.

## Recommended next use

Freeze both prompts rather than continue optimizing on this dataset:

- Use the exact Experiment 2 prompt as the no-search or tool-optional control.
- Use S1 when deliberate search is the treatment of interest.
- Stratify conclusions by independently reviewed source availability.
- Keep output compliance separate from ingredient identity.
- Human-adjudicate strict-matcher misses before publishing a leaderboard.
- Do not infer exact-source support from model confidence; retain and audit tool
  traces, especially for models whose native routes expose no citations.

The experiment demonstrates a real web-search benefit, but mostly as a
findability-dependent gain in ingredient identity—not as universal recovery of
named cookbook recipes.
