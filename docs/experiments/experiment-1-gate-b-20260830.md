# Experiment 1 final outbrief: source-assisted recipe reconstruction

Date: 2026-08-30

Status: paused after Gate B; no Gate C run planned

Maximum authorized spend: $1.00

Provider-reported spend: $0.61500754056

## Executive summary

Experiment 1 tested whether model-managed web search and public secondary
sources could improve reconstruction of a named cookbook recipe relative to
Title-only baseline v1. Gate B used one deliberately obscure recipe, Fennel
Seed and Olive Oil Tortas from *The Art of Gluten-Free Bread*, across OpenAI,
Google, Qwen, and DeepSeek. Claude was tested during calibration and then
retired because of cost.

The experiment produced a clear negative result for exact retrieval and a
useful mixed result for reconstruction:

- No model found a public page that presented the named cookbook recipe or an
  adaptation explicitly attributed to it.
- Search reliably found conventional wheat-flour variants of the same Spanish
  dish. Those variants supported a plausible generic ingredient core, but not
  the cookbook's specific gluten-free formula.
- Qwen and DeepSeek made the cleanest distinction between book metadata and
  same-dish variants. OpenAI and Gemini both upgraded variant or metadata pages
  into false `exact_cookbook_recipe` claims.
- Fixed public evidence moved answers toward a common, cautious reconstruction,
  but none of the reconstruction conditions followed the output contract well
  enough to support the planned automated paired-F1 analysis.
- Only 10 of the 16 active responses ended with `finish_reason: stop`. The
  62.5% clean-terminal rate missed the predeclared 75% Gate B threshold.
- Total spend was $0.61500754056. Claude alone cost $0.21531 for two truncated
  search responses and is excluded from future work.

Experiment 1 is therefore paused. The results should remain a qualitative study
of retrieval, attribution, and synthesis behavior rather than enter the primary
recipe-accuracy leaderboard.

## Experimental design

### Target case

Gate B used the complete private reference for:

`art_gluten_free_bread__fennel_seed_and_olive_oil_tortas_tortas_de_aceite_y_anis`

The case was selected before the run because the auto-search pilot found book
catalog pages and conventional tortas de aceite variants, but no exact public
recipe. Private ground truth was used only for local grading and was never
included in a search prompt or evidence packet.

### Active portfolio

| Model | Controlled inference provider | Search mode | Role |
|---|---|---|---|
| `openai/gpt-5.6-sol` | OpenAI | `auto` | active |
| `google/gemini-2.5-flash` | Google | `auto` | active; replaced Claude |
| `qwen/qwen3.8-27b` | Alibaba | `auto` | active |
| `deepseek/deepseek-v4-pro-0813` | Alibaba | `auto` | active |
| `anthropic/claude-opus-4.8` | Anthropic | `auto` | calibration only; retired |

All routes disabled provider fallbacks and requested `data_collection: deny`.
Retries were disabled. Search-enabled runs were dispatched sequentially so
reported spend could be reconciled before reserving the next case.

### Conditions

| ID | Web access | Input | Intended measurement |
|---|---|---|---|
| B0 | none | recipe and cookbook title | Baseline v1 parametric recall |
| C1 | auto search | title plus reconstruction instructions | End-to-end retrieval, synthesis, and attribution |
| C2 | auto search | title plus source-ledger instructions | Discovery and relevance classification |
| C3 | none | the same model's C2 packet | Synthesis with its own retrieval held fixed |
| C4 | none | one shared reviewed packet | Cross-model synthesis with evidence held fixed |

C1-C4 used one repetition in Gate B. The planned full experiment would have
used two repetitions and three recipes, but did not advance beyond calibration.

## Baseline v1 comparison

The baseline run was `run_cf898127d2fa4262a37018e53e4fe341` from
`cookbook-title-only-baseline-v1`. Across the three recipes originally selected
for Experiment 1, nine of twelve active-portfolio B0 observations were eligible.
All three Qwen B0 responses ended at `length` and were excluded from the primary
matched population.

For the Gate B recipe:

| Model | Baseline attempt | Finish | Human behavior | Strict F1 | Unsupported candidates | Match status |
|---|---|---|---|---:|---:|---|
| OpenAI | `attempt_a853b884355e493fb859a72e7570e3ae` | `stop` | refusal with alternative | 0.000 | 0 | eligible |
| Gemini | `attempt_868efd1f673547b0a25b713060674843` | `stop` | refusal with alternative | 0.000 | 0 | eligible |
| DeepSeek | `attempt_0ded98f3aa92416fa8af44334bb208f2` | `stop` | partial reconstruction | 0.261 | 8 | eligible |
| Qwen | `attempt_ed56b854800d4199bcbf035dd971bf5` | `length` | truncated partial reconstruction | 0.000 | 15 | excluded |

The baseline establishes two distinct starting behaviors. OpenAI and Gemini
avoided unsupported ingredient claims by declining to reconstruct. DeepSeek and
Qwen attempted answers, with substantial unsupported content. Search-assisted
answers were usually more explicit about uncertainty, but output-shape failures
prevent a valid numeric `C1 − B0` estimate.

## Execution chronology

1. OpenAI completed C1 and C2, but both responses reached the output limit.
2. Claude completed two truncated search responses for $0.21531. It was retired
   and replaced by the cheaper Baseline v1-matched Gemini route.
3. The first Qwen calibration used an incorrectly modeled limit. Its two
   responses were preserved, but superseded.
4. OpenRouter documentation clarified that cumulative results, server-tool loop
   steps, and reported search queries are different units. The harness stopped
   sending unsupported `max_uses` inside the web-search tool and adopted
   `max_total_results` plus provider-side step and cost stops.
5. Qwen C1 and C2 were rerun with concise prompts and a larger output allowance.
   Both returned clean final text.
6. Gemini and DeepSeek completed the corrected C1/C2 stage.
7. Model-specific C2 packets and one human-reviewed fixed packet were hashed and
   frozen. The four models then completed C3 and C4 without web access.

The corrected Qwen C2 result was recorded as a local failure by an intermediate
harness revision because it reported eleven queries against a ten-step loop
limit. Those values are not comparable: more than one search query can occur in
a server-tool step. Its response ended with `finish_reason: stop` and is treated
as analytically usable. It was not run a third time.

## Active condition-level operations

| Model | Condition | Attempt | Finish | Search queries | Input tokens | Output tokens | Latency | Cost |
|---|---|---|---|---:|---:|---:|---:|---:|
| OpenAI | C1 | `attempt_8756c6f93bc84e699c3b02c5e3bb601d` | `length` | 1 | 12,952 | 607 | 14.453 s | $0.04422200000 |
| OpenAI | C2 | `attempt_a5fb7de7db824f4aafc723bd4b581aab` | `length` | 1 | 12,993 | 613 | 14.598 s | $0.03430050000 |
| Qwen | C1 | `attempt_042deb09a01a400d911ab4383f9c2939` | `stop` | 9 | 36,152 | 1,587 | 41.311 s | $0.04823161000 |
| Qwen | C2 | `attempt_fefc442a619e49ed949c8916d92d0ef7` | `stop` | 11 | 44,687 | 1,156 | 32.388 s | $0.04688665500 |
| Gemini | C1 | `attempt_38bbbc3b429f4bab988e7a2b0cac5305` | `stop` | 1 | 1,667 | 604 | 5.904 s | $0.00901010000 |
| Gemini | C2 | `attempt_d53ee0bccc6d43ae89fcd26167ba5930` | `stop` | 3 | 3,165 | 593 | 6.320 s | $0.02343200000 |
| DeepSeek | C1 | `attempt_a17fb13bc241499ca0f45eacc66753eb` | `stop` | 6 | 12,071 | 1,563 | 36.087 s | $0.04205788160 |
| DeepSeek | C2 | `attempt_edb99a801f194b4eb58f2c62c94c8e15` | `stop` | 4 | 8,066 | 1,104 | 23.992 s | $0.03300254656 |
| OpenAI | C3 | `attempt_53840ef1e8544cdba4c36803e10b4043` | `length` | 0 | 749 | 800 | 10.207 s | $0.00949800000 |
| OpenAI | C4 | `attempt_da88031a72b74f50b745af7281e8e832` | `length` | 0 | 522 | 800 | 8.812 s | $0.00904400000 |
| Gemini | C3 | `attempt_01a0169798704237a16d8e31b72f7dda` | `stop` | 0 | 680 | 671 | 3.344 s | $0.00188150000 |
| Gemini | C4 | `attempt_ce8024f086a64bb1ae92cbedf34ca16f` | `stop` | 0 | 567 | 749 | 3.578 s | $0.00204260000 |
| Qwen | C3 | `attempt_c6b39b289eab40e589d2514ff4af64b0` | `stop` | 0 | 842 | 741 | 13.006 s | $0.00224740000 |
| Qwen | C4 | `attempt_44d894e9012c4d46a0a8be3820c22070` | `length` | 0 | 564 | 800 | 12.911 s | $0.00227970000 |
| DeepSeek | C3 | `attempt_7ce34d53a2ed4a2080ae6bcd630664fe` | `length` | 0 | 1,016 | 800 | 12.265 s | $0.00198401280 |
| DeepSeek | C4 | `attempt_c8179d6d742b4a7da70951a52feb6221` | `stop` | 0 | 545 | 764 | 15.366 s | $0.00164772960 |

All 16 active calls returned text and incurred one attempt. Ten were clean
terminal responses and six were truncated. Search queries varied from one to
eleven per request even though every request used the same high-level `auto`
policy, demonstrating that the model/provider search system is part of the
behavior under evaluation rather than a constant preprocessing step.

## Cost accounting

### Active runs

| Stage | Model | Run ID | Calls | Cost |
|---|---|---|---:|---:|
| C1/C2 | OpenAI | `run_7119c2df60c446a499f085fe2a87c668` | 2 | $0.07852250000 |
| C1/C2 | Qwen rerun | `run_675895a1d31a46aa8585c740482c1c96` | 2 | $0.09511826500 |
| C1/C2 | Gemini | `run_bd0adbffb3cc49e99bf25177faa8d36d` | 2 | $0.03244210000 |
| C1/C2 | DeepSeek | `run_f77878eebe8545c9854abc3cb99fb5e3` | 2 | $0.07506042816 |
| C3/C4 | OpenAI | `run_75af0e79e6f74d3293d58a315dc0c042` | 2 | $0.01854200000 |
| C3/C4 | Gemini | `run_a0aac0114fae42419582a6ac455ff3de` | 2 | $0.00392410000 |
| C3/C4 | Qwen | `run_d968069eecb34f16ac40b606a53f52b8` | 2 | $0.00452710000 |
| C3/C4 | DeepSeek | `run_b3e669676a144f4a9156c7a087e6abfa` | 2 | $0.00363174240 |
| **Active subtotal** | | | **16** | **$0.31176823556** |

### Superseded calibration

| Model | Run ID | Calls | Result | Cost |
|---|---|---:|---|---:|
| Qwen initial | `run_40998edf93b14bc3aeaa00d41d58141e` | 2 | both truncated; replaced by corrected run | $0.08792930500 |
| Claude | `run_6eba24e8645c403599863d26fe9d40d8` | 2 | both truncated; model retired | $0.21531000000 |
| **Calibration subtotal** | | **4** | | **$0.30323930500** |

The charged total was $0.61500754056, leaving $0.38499245944 unspent. Claude
accounted for 35.0% of the full spend and 71.0% of the superseded calibration
spend.

## Source discovery results

No reviewed source presented the target cookbook recipe. No reviewed source
said it adapted that recipe. The useful results were book metadata and
same-dish variants.

The operational review below was performed with model identity visible. It is
appropriate for this calibration outbrief but is not a substitute for the
blinded review planned for a benchmark.

| C2 model | Fully readable source blocks | Correct relevance labels | False exact labels | False adaptation labels | Review |
|---|---:|---:|---:|---:|---|
| OpenAI | 4 | 2 | 1 | 1 | publisher metadata upgraded to exact; unrelated adaptation upgraded to target adaptation |
| Qwen | 6 | 6 | 0 | 0 | clean separation of two metadata pages and four variants |
| Gemini | 6 | 4 | 2 | 0 | two generic fennel/tortas pages upgraded to exact |
| DeepSeek | 6 | 6 | 0 | 0 | one metadata page and five variants labeled correctly |
| **Total** | **22** | **18 (81.8%)** | **3** | **1** | no true exact or attributed source |

Every `exact_cookbook_recipe` claim in the readable ledgers was false. The
taxonomy contributed to the problem: it had no dedicated `cookbook_metadata`
label, forcing pages that established the book but not the recipe into the
overly broad `unrelated` bucket.

The shared fixed packet contained one publisher-metadata page and three
human-reviewed same-dish variants:

- the Hachette page establishing the book and author but not the recipe;
- [Leite's Culinaria](https://leitesculinaria.com/94627/recipes-spanish-olive-oil-tortas-de-aceite.html),
  a wheat-flour fennel and olive-oil variant adapted from a different book;
- [Mount Zero Olives](https://mountzeroolives.com.au/blogs/recipes/fennel-seed-tortas),
  an independently published wheat-flour fennel-seed variant;
- [Nigella's guest recipe](https://www.nigella.com/recipes/guests/jose-pizarros-tortas-de-aceite),
  another conventional same-dish variant.

The packet explicitly stated that none of these sources established the target
cookbook recipe.

## Evidence packet identities

The fixed packet hash was:

`076c0eaacdcc3363a8fb4452ad3d641b3c6c0367be81b70fe942e7d10256fa8f`

| Model | C2 source attempt | Own-packet SHA-256 |
|---|---|---|
| OpenAI | `attempt_a5fb7de7db824f4aafc723bd4b581aab` | `f4be525d01bbfc50eb9f51653ea399a33b55663cfe86785b3acb9516826f17e2` |
| Gemini | `attempt_d53ee0bccc6d43ae89fcd26167ba5930` | `8778f8ac4b2cfe5f10b563c0b0625580b729edde14c7355e714788a07622e5fb` |
| Qwen | `attempt_fefc442a619e49ed949c8916d92d0ef7` | `cbde142fc8646d5b1c42afb81f29a494c7c4308aef2e38e6f0880b83bca8b30e` |
| DeepSeek | `attempt_edb99a801f194b4eb58f2c62c94c8e15` | `9a0e307540b047d8406384b9b480302293024045335fa8a2a8cb6cdcd6b084d5` |

The generated configs embedded the packet content and hash in the immutable
case prompt. Raw packet content remains in ignored artifacts.

## Output-contract compliance

The experiment requested one compact source block per C2 source and one compact
ingredient block per reconstructed ingredient. Compliance was substantially
worse than transport success:

| Condition group | Strictly compliant responses | Common failure |
|---|---:|---|
| C1 | 0 of 4 | returned methods or complete variant recipes instead of one target hypothesis |
| C2 | 1 of 4 | markdown wrappers, introductions, or truncation; fields remained human-readable |
| C3 | 0 of 4 | `EVIDENCE` contained prose instead of one allowed label |
| C4 | 0 of 4 | prose evidence, missing ingredient fields, invalid status, or truncation |

Only three of twelve active reconstruction responses emitted one of the exact
allowed status values. Raw text was preserved and reviewed; malformed output
was not silently repaired. This is the main reason a paired ingredient score is
not reported.

## Model-by-model response review

The excerpts below are short examples from model outputs. They illustrate
behavior and are not source quotations or cookbook text.

### OpenAI GPT-5.6 Sol

OpenAI was the most willing to produce a concrete cookbook hypothesis. C1 began
with a useful boundary:

> “a reasoned reconstruction, not verified cookbook content”

It then supplied a detailed formula with exact quantities and a method. The
formula combined a proposed gluten-free flour/starch system, psyllium, yeast,
salt, sugar, fennel, sesame, water, and olive oil. Several broad ingredient
identities overlapped the private reference, but multiple specific flour,
starch, and seed choices were unsupported. Exact quantities made the answer
look more authoritative than its evidence warranted.

OpenAI's C2 ledger contained the strongest attribution failures. It labeled a
publisher book page `exact_cookbook_recipe` even while saying that the page did
not display the recipe, and labeled a recipe adapted from a different source as
`attributed_adaptation` of the target.

C3 introduced anise seed or anise-flavored spirit as an uncertain possibility
because of the Spanish title. C4 became more conservative and converged on a
generic seven-part same-dish structure. All four active OpenAI responses ended
at `length`, so none provided a complete contract-conforming record.

### Gemini 2.5 Flash

Gemini's C1 correctly ended with:

> `STATUS: insufficient_evidence`

However, instead of one hypothesis for the target, it returned three complete
wheat-flour variant ingredient lists. That was epistemically cautious but did
not answer the experimental question in the required form.

Gemini's C2 was fast and inexpensive, but labeled the Leite's and Mount Zero
variant pages as exact cookbook recipes simply because their titles closely
matched the dish. In C3, Gemini used its own ledger very conservatively and
proposed only fennel and olive oil. With the shared C4 packet it expanded to a
seven-part generic structure. Both evidence-only responses ended cleanly, but
used `STATUS: Hypothesis`, which was not an allowed status.

### Qwen 3.8 27B

Qwen's corrected C1 opened its first block with:

> “No ingredient list found.”

It clearly separated the unavailable target from several public variants and
ended `insufficient_evidence`. It did not produce a single target hypothesis,
but it was the most explicit about why variant recipes could not verify the
cookbook.

Qwen's C2 was the best source ledger in the active run: two book/catalog pages
were labeled unrelated to recipe evidence, and four conventional variants were
labeled `same_dish_variant`. C3 proposed a compact generic set while warning
that the specific gluten-free flour system was not verifiable. C4 lost several
ingredient values because of formatting drift and then truncated.

The rerun also showed that search-query counts are behavioral telemetry rather
than a direct loop-step limit: C1 reported nine queries and C2 eleven, but both
returned final `stop` responses within their cost stops.

### DeepSeek V4 Pro

DeepSeek's B0 answer attempted a recipe and accumulated eight unsupported
candidates. Its search-assisted C1 improved attribution language:

> “none should be treated as the verified cookbook content”

Like Gemini, it returned multiple public variant lists instead of one target
hypothesis. DeepSeek's C2 ledger was fully correct in the operational review:
one publisher metadata page was not treated as recipe evidence, and five recipe
pages were classified as same-dish variants.

C3 and C4 both converged on the generic flour, fennel, olive oil, yeast, sugar,
salt, and water structure. C3 truncated; C4 ended cleanly with a prominent
`RECONSTRUCTION ONLY` warning. Relative to B0, the staged evidence made
DeepSeek's uncertainty and attribution boundary much clearer even though a
formal F1 delta is unavailable.

### Claude Opus 4.8 calibration

Claude was removed from the active portfolio. Its C1 and C2 calls cost
$0.11086 and $0.10445 and both truncated. C1 also misidentified the cookbook's
author, writing:

> “by Jules Shepard, or possibly conflated with another GF baking title”

That error occurred despite search being enabled. Claude did correctly decline
to describe the conventional variants as the book's verified recipe, but its
cost, truncation, and author confusion made it a poor fit for this experiment.

## What fixed evidence changed

The C4 packet removed retrieval variance and made the attribution boundary
unambiguous. Three useful patterns emerged:

1. Models converged on the conventional dish's common core rather than each
   inventing a different detailed formula.
2. Models generally stopped claiming exact cookbook support.
3. The missing cookbook-specific gluten-free system remained visible: the
   evidence justified a generic flour component, not the reference's particular
   combination of flours, starch, and binders.

This suggests fixed evidence is useful for studying synthesis discipline, but
not sufficient to recover obscure proprietary recipes when public sources only
cover neighboring variants.

## Hypothesis assessment

| Hypothesis | Gate B assessment | Evidence |
|---|---|---|
| H1: search improves strict ingredient F1 | indeterminate | output-contract failures prevent paired scoring; only one obscure recipe ran |
| H2: search reduces unsupported ingredients on obscure recipes | partially supported | answers became more cautious, but C1 often returned whole variant lists |
| H3: fixed evidence reduces repetition variance | not tested | Gate B used one repetition |
| H4: `direct` and `multi_source` labels are better calibrated | not tested | models rarely emitted one allowed label per ingredient |
| H5: models upgrade same-dish variants into target evidence | supported | OpenAI and Gemini produced false exact/attributed source labels |

The strongest finding is H5. Similar titles and dish identity were sufficient
for some systems to overstate provenance even when their own support text
acknowledged that the page was not the cookbook recipe.

## Harness findings and changes landed

Gate B led to the following implementation changes:

- prompt-level selection of one tool profile instead of an unconditional
  prompt-by-tool Cartesian product;
- immutable matching of later cases to Baseline v1 attempt, model, provider,
  prompt-version, parameter, and finish metadata;
- sequential reservation and actual-cost reconciliation for search runs;
- cost recovery from malformed provider responses when usage is present;
- fail-closed handling of genuinely nonterminal `tool_calls` responses;
- documented `max_total_results` and `stop_server_tools_when` controls;
- separation of reported search queries from server-tool loop steps;
- hashed generation of private model-specific and fixed-evidence configs;
- per-run preservation of catalogs, endpoint snapshots, plans, requests,
  untouched responses, usage, generation metadata, and costs.

The default offline suite contains 87 tests and covers the new baseline matcher,
prompt-specific profiles, cost stops, terminal handling, and budget behavior.

## Limitations

- Gate B used one obscure recipe and one repetition. It cannot establish average
  model or search effects.
- Prompt versions and operational controls changed during calibration. Only the
  corrected active runs are compared as the final portfolio.
- The source review in this outbrief was not blinded to model identity.
- Six active responses truncated, and zero reconstruction responses strictly
  followed the full ingredient-block contract.
- There was no exact public source, so the experiment primarily tested behavior
  under absent evidence rather than extraction from a source-rich case.
- The fixed packet was deliberately small and paraphrased. It held evidence
  constant but did not represent every source discovered.
- The web-search server tool was beta during execution; provider behavior and
  controls may change.
- A generic ingredient such as “gluten-free flour blend” cannot be treated as a
  strict match for multiple specific reference ingredients.

## Final decision

Experiment 1 is paused at Gate B. Gate C was not run and should not be resumed as
part of this experiment.

The work produced reusable infrastructure and several lessons for a future
Experiment 3:

- define `cookbook_metadata` separately from recipe relevance;
- prefer compact, mechanically enforceable output rows over prose blocks;
- reserve enough output tokens for the contract, not for open-ended narrative;
- grade source attribution before ingredient accuracy;
- keep fixed-evidence synthesis separate from product-style auto search;
- use a source-rich case when the research question requires exact-source
  extraction, and an obscure case when testing calibrated abstention;
- continue excluding Claude unless a later question justifies its cost.

Raw responses, public excerpts, generated evidence configs, and private ground
truth remain in ignored local artifacts. The repository contains versioned
configurations, implementation, packet hashes, aggregate results, and this
redistribution-safe outbrief.
