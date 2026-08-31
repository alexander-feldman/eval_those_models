# Experiment 3 final report: uncapped reconstruction with quantities

Date: 2026-08-30

Status: complete

Final cumulative authorization: $2.50

Provider-reported cumulative spend: $1.8876171876

Primary balanced-study spend: $0.6107850370

## Executive summary

The original Experiment 3 analysis used a five-to-twelve-item output contract.
That was the wrong measurement instrument for complete recipe reconstruction.
One held-out recipe has 16 printed ingredient rows and another has 26, so even
a factually perfect response could not achieve full recall. Those capped
results and their metrics artifact have been superseded and are not used in
this report's conclusions.

The replacement study is a balanced 4 × 4 × 2 design: the same four recipes,
the same four models, and two uncapped quantity-and-wording prompts. B0 has no
tools. W1 requires web search and admits ingredient evidence only from an exact
recipe or attributed adaptation. Every condition asks for every ingredient row
and for the quantity and ingredient wording, not merely normalized identities.

The clean result is much stronger and more interpretable:

- Search raised strict ingredient F1 from **0.236 to 0.532**, an absolute gain
  of 0.296. Precision rose from 0.223 to 0.569 and recall doubled from 0.250 to
  0.500.
- Exact quantity coverage over all 248 model/reference rows rose from **3.6%
  to 21.0%**. Exact-or-equivalent coverage rose from **5.2% to 30.6%**.
- Rows with both an exact quantity and exact normalized ingredient wording rose
  from **6 to 38**. This is a much stronger retrieval/copying signal than
  ingredient identity alone.
- The effect followed public source availability. On Lori's Chocolate Midnight
  Cake, search raised ingredient F1 from 0.368 to 0.907 and exact-or-equivalent
  quantity coverage from 12.5% to 80.0%. On the hot-cross-bun recipe, for which
  search returned only cookbook metadata, F1 moved only from 0.239 to 0.276 and
  exact quantity coverage remained zero under search.
- Quantity fidelity exposed source-selection errors. Search often copied a
  public adaptation very closely, but that adaptation sometimes differed from
  the private original in amounts, combined rows, or omitted ingredients.
- Factual quality and output compliance moved in opposite directions. After
  transparent mechanical normalization, W1 was much more accurate, but only
  5/16 raw search outputs obeyed the requested pipe-row contract versus 13/16
  baselines. OpenAI was the only model with 4/4 compliant W1 responses.
- Search cost $0.577959 versus $0.032826 for B0—about **17.6 times as much**.
  Claude alone accounted for $0.373680 of the search arm.

The evidence supports a precise conclusion: web search substantially improves
complete ingredient reconstruction and quantity fidelity when a usable public
recipe is findable. It does not recover a recipe that is absent from search,
and exact quantity/wording comparison is essential for distinguishing the
book's original text from a nearby public adaptation.

## Why the capped results were discarded

The earlier prompt requested five to twelve normalized ingredient names. The
four recipes in the final balanced set contain:

| Recipe | Printed reference rows | Rows necessarily omitted at a 12-item cap | Maximum possible recall |
|---|---:|---:|---:|
| Oat and Honey Sourdough Hot Cross Buns | 26 | 14 | 46.2% |
| Goat Cheese Soufflés with Vanilla-Poached Peaches | 16 | 4 | 75.0% |
| Moroccan Orange-Walnut Salad | 10 | 0 | 100% |
| Lori's Chocolate Midnight Cake | 10 | 0 | 100% |
| **Four-recipe total** | **62** | **18** | **71.0%** |

The ceiling was not merely cosmetic. In one capped Qwen soufflé pair, the
tool-optional answer returned 15 identities, including sugar and white wine.
The required-search answer obeyed the 12-item cap by dropping both even though
both appear in the reference. Calling that a retrieval regression would confuse
prompt-imposed deletion with factual performance.

A deeper audit also found that the old identity adapter mishandled one-line
comma-separated answers before reaching its comma-splitting logic. Rather than
patch and continue presenting a fundamentally capped benchmark, this study
removes the old metrics artifact and replaces the evaluation end to end.

The earlier runs remain part of provider spend and prompt-development history,
but none of their capped accuracy numbers enters the primary tables below.

## Final balanced design

### Recipes

Every model received the same four held-out recipes:

1. Lori's Chocolate Midnight Cake — *Salt, Fat, Acid, Heat*
2. Moroccan Orange-Walnut Salad — *The Enchanted Broccoli Forest*
3. Goat Cheese Soufflés with Vanilla-Poached Peaches — *Plenty*
4. Oat and Honey Sourdough Hot Cross Buns — *The Art of Gluten-Free Bread*

The set contains 62 printed ingredient rows per model, or 248 model/reference
rows per arm. The grader excludes a subrecipe-reference row from ordinary
identity recall but retains all printed rows for quantity-coverage diagnostics.

### Models

- OpenAI GPT-5.6 Sol
- Claude Opus 4.8
- Qwen 3.8 27B
- DeepSeek V4 Pro

All routes disabled fallbacks and reasoning, requested `data_collection: deny`,
and used one repetition. The run completed 32/32 cases without a transport or
provider failure.

### B0: true no-search baseline

The baseline had no tool profile:

> Without using external tools or sources, give a complete best-effort
> ingredient-and-quantity hypothesis for “{recipe_name}” from
> “{cookbook_title}”. Return every ingredient row you reasonably associate with
> the specific named recipe, preserving source order and the quantity and
> ingredient wording as specifically as you remember them. Write unknown
> instead of inventing a precise quantity you do not know. Output only one line
> per ingredient row in the form QUANTITY | INGREDIENT. There is no item limit.
> Do not include headings, bullets, confidence, citations, directions, searches,
> reasoning, uncertainty, or caveats. Do not abstain.

### W1: required evidence-gated search

> Before producing the final answer, you must call the web-search tool at least
> once to look for the exact named recipe or a clearly attributed adaptation of
> “{recipe_name}” from “{cookbook_title}”. Silently classify results as exact
> recipe, attributed adaptation, cookbook metadata, same-dish variant, or
> unrelated. Use retrieved ingredient evidence only from an exact recipe or
> attributed adaptation. If one is found, return every printed ingredient row,
> preserving source order and reproducing its quantity string and ingredient
> wording exactly as shown. If neither is found, ignore retrieved variants and
> give a complete pre-search best-effort hypothesis for this specific recipe;
> write unknown for any quantity not supported by direct evidence rather than
> inventing one. Output only one line per ingredient row in the form QUANTITY |
> INGREDIENT. There is no item limit. Do not include headings, bullets,
> confidence, citations, directions, searches, reasoning, uncertainty, or
> caveats. Do not abstain.

Search returned up to three results and 4,000 characters per result. The harness
requested one tool step with a per-case cost stop. Provider counters nevertheless
reported 19 search requests over 16 W1 cases because three model calls made a
second request.

## Run and cost accounting

Primary run: `run_cee6e92070b146df911acfa4f8066981`

| Model | B0 no search | W1 search | Primary total |
|---|---:|---:|---:|
| Claude Opus 4.8 | $0.023205000 | $0.373680000 | **$0.396885000** |
| OpenAI GPT-5.6 Sol | $0.004976000 | $0.119484000 | **$0.124460000** |
| DeepSeek V4 Pro | $0.002522256 | $0.049427956 | **$0.051950212** |
| Qwen 3.8 27B | $0.002122875 | $0.035366950 | **$0.037489825** |
| **Total** | **$0.032826131** | **$0.577958906** | **$0.610785037** |

The cumulative experiment ledger includes the original capped work and prompt
development ($0.9840242996), the uncapped one-recipe quantity pilot
($0.2928078510), and the clean balanced run ($0.6107850370):

| Model | Cumulative spend |
|---|---:|
| Claude Opus 4.8 | $1.0000300000 |
| OpenAI GPT-5.6 Sol | $0.4291704000 |
| Qwen 3.8 27B | $0.2345124000 |
| DeepSeek V4 Pro | $0.2239043876 |
| **Total** | **$1.8876171876** |

Claude consumed 53.0% of cumulative spend. The study finished $0.6123828124
below the final $2.50 authorization.

## Deterministic grading and raw-contract separation

The tracked
[balanced metrics artifact](experiment-3-balanced-quantity-metrics-20260830.json)
is generated by
[`scripts/analyze_experiment3_quantity.py`](../../scripts/analyze_experiment3_quantity.py)
from the ignored raw event log and the versioned private reference database.

The analysis reports:

- strict ingredient precision, recall, and F1 under deterministic-v3 matching;
- exact and exact-or-equivalent quantities among matched ingredient identities;
- exact and exact-or-equivalent quantity coverage over every printed reference
  row, so a short answer cannot look strong merely by having a high conditional
  rate;
- exact quantity plus exact normalized ingredient wording, the strongest
  direct-copy indicator in this study;
- raw output-contract compliance, tool narration, finish reason, search calls,
  citation annotations, and cost.

Mechanical normalization is deliberately narrow and audited. It inserts a
space in compact metric forms such as `150ml`, removes concatenated tool
narration for content grading, collapses Qwen's duplicated columns, recognizes
DeepSeek rows that put the complete quantity-and-ingredient text in the first
column, and splits a one-line sequence of complete rows separated by pipes.
These transformations do not add or alter an ingredient or quantity. The raw
response remains noncompliant and is counted that way.

This distinction matters. A one-line Qwen cake response contained nine strong
quantity-and-ingredient segments but violated `QUANTITY | INGREDIENT` by using
the pipe as a row separator. Treating it as one ingredient would erase factual
content; treating it as compliant would erase an operational failure. The
report does neither.

## Primary results

| Metric | B0 no search | W1 required search | Change |
|---|---:|---:|---:|
| Cases | 16 | 16 | — |
| Search used | 0/16 | 16/16 | +16 |
| Raw contract compliant | 13/16 | 5/16 | -8 |
| Strict ingredient precision | 0.223 | 0.569 | +0.346 |
| Strict ingredient recall | 0.250 | 0.500 | +0.250 |
| Strict ingredient F1 | 0.236 | 0.532 | **+0.296** |
| Exact quantities among matched identities | 15.0% | 40.3% | +25.3 points |
| Exact-or-equivalent among matched identities | 21.7% | 58.9% | +37.2 points |
| Exact quantity coverage over all rows | 3.6% | 21.0% | +17.3 points |
| Exact-or-equivalent coverage over all rows | 5.2% | 30.6% | +25.4 points |
| Exact quantity + normalized wording rows | 6 | 38 | **+32** |
| Cost | $0.032826 | $0.577959 | +$0.545133 |

Search doubled ingredient recall while also more than doubling precision. It
did this with fewer content-normalized rows—213 versus 269—because the baseline
often expanded into generic ingredients while search anchored output to a
specific public list.

The unconditional quantity coverage is the most useful fidelity metric. A model
cannot inflate it by emitting only the few amounts it knows. W1 produced an
exact amount for 52 of 248 model/reference rows and an exact or mathematically
equivalent amount for 76. B0 produced only 9 exact and 13 exact-or-equivalent
amounts.

## Results by model

| Model | B0 F1 | W1 F1 | B0/W1 exact quantity coverage | B0/W1 exact-or-equivalent coverage | B0/W1 compliant |
|---|---:|---:|---:|---:|---:|
| Qwen | 0.097 | **0.558** | 1.6% / **22.6%** | 1.6% / **33.9%** | 3/4 / 1/4 |
| DeepSeek | 0.310 | **0.557** | 8.1% / **21.0%** | 9.7% / **32.3%** | 3/4 / 0/4 |
| OpenAI | 0.268 | **0.528** | 4.8% / **19.4%** | 8.1% / **27.4%** | 3/4 / **4/4** |
| Claude | 0.293 | **0.487** | 0.0% / **21.0%** | 1.6% / **29.0%** | 4/4 / 0/4 |

All four models improved materially. Their content metrics converge more than
the old capped experiment suggested: W1 F1 spans 0.487–0.558. Qwen has the
largest delta, but its B0 score is depressed by one pathological 56-row,
token-limited soufflé answer that wandered through dozens of irrelevant spice
and vegetable powders. Search replaced that with a 14-row attributed list.
Qwen's gain is real, but the magnitude is partly a reduction of a baseline
failure rather than four uniform wins.

OpenAI is the operational winner. Its W1 F1 is slightly below Qwen and DeepSeek,
but it is the only route with four clean, normally terminated, contract-compliant
search responses. Claude had strong source-assisted facts but violated the
contract in all four W1 cases, including two concatenated `I'll search...`
preambles. DeepSeek often narrated source classification or reversed the pipe
columns. Qwen frequently used pipes between whole rows or duplicated the full
row in both columns.

## Results by recipe: findability explains the treatment effect

| Recipe | Public evidence observed | B0 F1 | W1 F1 | B0/W1 exact quantity coverage | B0/W1 exact-or-equivalent coverage |
|---|---|---:|---:|---:|---:|
| Lori's Chocolate Midnight Cake | exact ingredient list | 0.368 | **0.907** | 10.0% / **52.5%** | 12.5% / **80.0%** |
| Goat Cheese Soufflés | attributed adaptation and summary | 0.158 | **0.742** | 3.1% / **40.6%** | 3.1% / **46.9%** |
| Moroccan Orange-Walnut Salad | exact-looking copy plus variants | 0.247 | **0.423** | 5.0% / **12.5%** | 10.0% / **35.0%** |
| Oat and Honey Hot Cross Buns | cookbook metadata only | 0.239 | 0.276 | 1.0% / **0.0%** | 1.9% / **0.0%** |

The source audit uses the structured URL annotations exposed by Qwen and
DeepSeek. Their search calls returned 24 annotations in the clean run. OpenAI
and Claude reported tool use but exposed no structured citation annotations, so
their exact source selection remains provider-opaque.

For the cake, results included a
[CBS News ingredient list](https://www.cbsnews.com/news/the-dish-samin-nosrat/)
that closely matches the private transcription. For the salad, results included
both a
[Food.com variant](https://www.food.com/recipe/moroccan-orange-walnut-salad-zwt-ii-169343)
and an
[Astray Recipes transcription](https://www.astray.com/recipes/?show=Moroccan+orange-walnut+salad)
that is closer to the reference. The soufflé results included a
[Terhune Orchards adaptation explicitly attributed to *Plenty*](https://www.terhuneorchards.com/our_recipes/goat-cheese-souffles-with-vanilla-poached-peaches-from-plenty/).
The hot-cross-bun results exposed publisher pages and a table of contents, not
an ingredient list.

## Qualitative case 1: the cleanest retrieval win

OpenAI's no-search cake answer was plausible chocolate cake. It guessed
buttermilk and baking powder, doubled the cocoa, doubled the baking soda, and
missed the cookbook's dual-unit strings and Vanilla Cream reference. W1 found a
matching public list and reconstructed every reference identity.

In the diff below, `-` is the complete B0 response and `+` is the complete W1
response. Capitalization and whitespace are normalized only for display.

```diff
- 1 cup | Dutch-process cocoa powder
+ ½ cup (2 ounces) | Dutch-process cocoa powder, preferably Valrhona
- 1½ cups | granulated sugar
+ 1½ cups (10½ ounces) | sugar
- 1¾ cups | all-purpose flour
+ 2 teaspoons kosher salt or 1 teaspoon fine sea salt | salt
- 2 teaspoons | baking soda
+ 1¾ cups (9¼ ounces) | all-purpose flour
- 1 teaspoon | baking powder
+ 1 teaspoon | baking soda
- 1 teaspoon | kosher salt
+ 2 teaspoons | vanilla extract
- 2 | large eggs, at room temperature
+ ½ cup | neutral-tasting oil
- 1 cup | buttermilk, at room temperature
+ 1½ cups | boiling water or freshly brewed strong coffee
- 1 cup | strong brewed coffee, at room temperature
+ 2 large | eggs at room temperature, lightly whisked
- ½ cup | neutral-tasting oil
+ 2 cups | Vanilla Cream
- 1 teaspoon | vanilla extract
```

The original/reference transcription is:

```text
½ cup (2 ounces) Dutch-process cocoa powder, preferably Valrhona
1½ cups (10½ ounces) sugar
2 teaspoons kosher salt or 1 teaspoon fine sea salt
1¾ cups (9¼ ounces) all-purpose flour
1 teaspoon baking soda
2 teaspoons vanilla extract
½ cup neutral-tasting oil
1½ cups boiling water or freshly brewed strong coffee
2 large eggs at room temperature, lightly whisked
2 cups Vanilla Cream (page 423)
```

The cell-level diagnostics make the difference explicit:

| OpenAI cake metric | B0 | W1 |
|---|---:|---:|
| Strict ingredient F1 | 0.500 | **1.000** |
| Strict identities recovered | 5 | **9/9 non-subrecipe rows** |
| Exact quantity coverage | 10% | **70%** |
| Exact-or-equivalent quantity coverage | 20% | **100%** |
| Exact quantity + normalized wording rows | 1 | **5** |
| Cost | $0.001172 | $0.029951 |

The dual measures—`½ cup (2 ounces)`, `1½ cups (10½ ounces)`, and
`1¾ cups (9¼ ounces)`—plus `preferably Valrhona` are far harder to explain as a
generic cake guess than identities such as flour, sugar, and eggs. This is the
kind of evidence the identity-only capped study could not observe.

## Qualitative case 2: quantities reveal copying of the wrong version

The soufflé has a highly findable attributed adaptation. W1 ingredient F1 rose
from 0.158 to 0.742 across models, and exact quantity coverage rose from 3.1% to
40.6%. Qwen and Claude produced nearly identical 14-row lists, strongly
indicating that both followed the Terhune result.

But the quantity strings show that the public adaptation is not identical to
the private original. In this diff, `-` is the source-assisted Qwen wording and
`+` is the original/reference wording for the differing rows:

```diff
- ⅔ cup each water and white wine
+ ⅔ cup water
+ ⅔ cup white wine
- 3 medium peaches, peeled
+ 2 to 3 medium peaches, peeled
- ½ tsp salt
+ ⅓ tsp salt
+ 3 tbsp heavy cream per soufflé, if reheating
```

The adaptation merges water and wine, fixes the peaches at three, changes the
salt from one-third to one-half teaspoon, and omits the reheating cream. The
models are not simply hallucinating these shared differences: Qwen's retained
annotation contains the same adaptation wording. Ingredient-only scoring would
call this a near-total success. Quantity-and-wording scoring correctly says it
is strong retrieval of a nearby version, not exact recovery of the original.

## Qualitative case 3: search cannot retrieve an unavailable formula

For Oat and Honey Sourdough Hot Cross Buns, all reviewed results were publisher
metadata, catalog descriptions, or a table of contents. The treatment correctly
did not produce specific amounts. OpenAI's W1 answer begins:

```text
unknown | dried currants
unknown | honey
unknown | gluten-free sourdough starter
unknown | oat milk
unknown | unsalted butter
unknown | egg
unknown | psyllium husk powder
unknown | tapioca starch
unknown | oat flour
```

The original contains highly specific rows such as:

```text
115 grams Whole-Grain Brown Rice–Teff Sourdough Starter (page 48)
65 grams oat milk or whole milk, heated to 80°F (27°C)
115 grams oat flour
25 grams psyllium husk powder
120 grams tapioca starch, plus more for dusting
50 grams honey
55 grams soft (but not melted) unsalted butter or vegan butter, plus more for greasing
50 grams plump dried currants or small raisins
```

Across the four W1 cells, 25 ingredient identities matched deterministically,
but every matched quantity was missing. F1 improved only 0.038, from 0.239 to
0.276, and exact quantity coverage was 0/104 model/reference rows. The baseline
had one exact quantity and one equivalent quantity by chance while getting
seven other matched amounts wrong. Search improved epistemic discipline here,
not reconstruction.

## Qualitative case 4: finding several sources is not enough

The salad search returned both a close transcription and a looser Food.com
variant. Qwen and DeepSeek followed the Food.com values. Quantity comparison
exposes the choice:

```diff
- 10 radishes, thinly sliced
+ 1 cup thinly sliced radishes
- 6 tablespoons extra-virgin olive oil
+ 3 Tbs. extra-virgin olive oil
- ½ small red onion, thinly sliced
+ ½ cup thinly sliced red onion
```

Search still improved salad identity F1 from 0.247 to 0.423, but exact quantity
coverage reached only 12.5%. The search system retrieved a closer source in the
same result set and the models nevertheless selected a conflicting variant.
This is a ranking/classification failure, not a web-availability failure.

## What the uncapped baseline teaches

Removing the cap is necessary, but “complete” can create a different failure
mode. Qwen's no-search soufflé response ran to the 500-token ceiling and emitted
56 rows. After a few plausible ingredients, it continued through ground mace,
star anise, cumin, paprika, dried oregano, mushroom powder, tomato powder,
parsnip powder, cassava powder, and many others. The final row was incomplete.

That single response explains much of Qwen's B0 precision of 0.082 and F1 of
0.097. W1 anchors Qwen to a public list and raises precision to 0.659. A future
production prompt should not restore an arbitrary item cap; it should instead
say to emit every source-supported row and stop, with an explicit safeguard
against enumerating speculative ingredients when no source exists.

## Contract compliance is a separate product problem

The content result is positive, but the raw output contract regressed:

| Model | B0 compliant | W1 compliant | Main W1 defect |
|---|---:|---:|---|
| OpenAI | 3/4 | **4/4** | none systematic |
| Claude | 4/4 | 0/4 | tool narration and non-quantity left columns |
| Qwen | 3/4 | 1/4 | whole rows separated by pipes or duplicated columns |
| DeepSeek | 3/4 | 0/4 | narration, reversed columns, and whole-row left columns |

Search returned better facts while making three model families worse data
producers. This is not visible in content-normalized F1. If the downstream
consumer requires strict parsing, OpenAI is the only currently usable W1 route
without provider-specific cleanup.

## Conclusions

1. **Discarding the cap changes the question for the better.** The final study
   measures reconstruction, not selection of twelve high-confidence identities.
2. **Search has a large aggregate effect.** Strict ingredient F1 rises 0.296,
   and exact-or-equivalent quantity coverage rises 25.4 percentage points.
3. **Exact quantity and wording are the right copy signal.** The cake's dual
   measures and modifiers reveal direct source use; generic identities do not.
4. **Source fidelity must be checked against the original.** The soufflé case
   shows close copying of an attributed adaptation that differs from the book.
5. **Findability bounds performance.** The metadata-only hot-cross-bun case gets
   no exact search quantities, while the exact-source cake improves dramatically.
6. **Retrieval and rendering should be evaluated separately.** Content improved
   for every model; raw format compliance fell from 13/16 to 5/16.
7. **The balanced four-recipe comparison is the primary result.** Earlier
   six-recipe/two-recipe mixtures and all capped accuracy numbers are superseded.

For the next iteration, keep the balanced set and uncapped rows, add a
source-selection stage that prefers the closest attributed transcription over
the first plausible variant, and test a deterministic renderer or structured
schema separately from retrieval. Do not reintroduce a fixed ingredient limit.
