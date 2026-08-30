# Experiment 1: Source-assisted recipe reconstruction

Status: planned

Predecessors:

- the title-only model smoke test;
- the auto web-search pilot.

No paid execution is authorized by this document. Freeze live model routes,
produce a dry-run cost plan, and obtain a separate spending authorization before
dispatch.

## 1. Purpose

Experiment 1 measures whether web search helps a model reconstruct a named
cookbook recipe from public secondary sources without falsely presenting a
related recipe or model inference as verified cookbook text.

It separates three capabilities:

1. **Discovery:** finding and correctly classifying relevant public sources.
2. **Synthesis:** extracting common and variable ingredients from those sources.
3. **Attribution:** distinguishing verified source content from a plausible
   reconstruction.

The experiment does not treat compliance alone as success. A confident list of
ingredients from the wrong recipe is a retrieval or attribution failure even if
some ingredients happen to match the private reference.

## 2. Research questions and hypotheses

### Primary question

Does source-assisted reconstruction improve strict ingredient identity F1 over
neutral title-only recall while preserving accurate source attribution?

### Secondary questions

- How often does auto search find an exact or explicitly attributed source?
- When no exact source exists, does multi-source synthesis improve ingredient
  precision or merely create a more persuasive hallucination?
- Are model-provided evidence labels calibrated? In particular, are ingredients
  labeled `direct` more accurate than ingredients labeled `uncertain`?
- How much of the cross-model difference comes from retrieval versus synthesis?
- Does search change refusal, abstention, or attempted-reconstruction behavior?

### Hypotheses

- **H1:** Auto-search reconstruction will improve mean strict ingredient F1
  relative to title-only recall for recipes with a substantial public footprint.
- **H2:** Search will reduce unsupported-ingredient rate on obscure recipes when
  the prompt explicitly permits abstention.
- **H3:** Fixed-evidence results will vary less across repetitions than each
  model's auto-search results.
- **H4:** `direct` and `multi_source` ingredient claims will have higher precision
  than `contextual_inference` and `uncertain` claims.
- **H5:** Some models will incorrectly upgrade a same-dish variant into evidence
  for the named cookbook recipe; this is an attribution failure.

## 3. Terminology

Every discovered source receives exactly one relevance label:

- `exact_cookbook_recipe`: explicitly presents the named cookbook recipe;
- `attributed_adaptation`: explicitly states that it adapts the named recipe;
- `same_dish_variant`: presents the same general dish without establishing a
  connection to the named cookbook recipe;
- `unrelated`: does not materially support the requested dish or attribution.

Every reconstructed ingredient receives exactly one evidence label:

- `direct`: explicitly stated by an `exact_cookbook_recipe` or
  `attributed_adaptation` source, while retaining that source's relevance label;
- `multi_source`: present in at least two relevant public variants;
- `contextual_inference`: inferred from the dish or cookbook context;
- `uncertain`: weak, conflicting, or single-variant support.

Only `direct` evidence from an `exact_cookbook_recipe` may be described as
source-supported for what the cookbook printed. `direct` evidence from an
`attributed_adaptation` supports that adaptation, not necessarily the original.
The other evidence labels support a hypothesis or similar recipe.

## 4. Recipe sample

Use three complete private references selected before any model calls:

| Stratum | Recipe ID | Reason for inclusion |
|---|---|---|
| Likely exact or author-adjacent source | `food_lab__basic_almost_no_stir_risotto` | Popular author and dish; likely public editorial footprint |
| Variant-rich and attribution-ambiguous | `salt_fat_acid_heat__green_goddess_dressing` | Generic recipe name with many public variants |
| Obscure and difficult to source | `art_gluten_free_bread__fennel_seed_and_olive_oil_tortas_tortas_de_aceite_y_anis` | Search pilot found only catalog pages and unrelated variants |

All three references have complete ingredient lists. Do not substitute a case
after seeing model output. If a case becomes unavailable for operational
reasons, record the exclusion and continue with the remaining frozen cases.

## 5. Model portfolio and routing

Freeze exact canonical slugs from the live OpenRouter catalog immediately
before execution. The intended four-family portfolio is:

- one frontier OpenAI model;
- one frontier Anthropic model;
- one current Qwen model;
- one current DeepSeek model.

For each model:

- select one controlled provider endpoint;
- set `allow_fallbacks: false`;
- request `data_collection: deny`;
- record whether zero-data-retention routing is available;
- use `engine: auto` for the production-search conditions;
- record the actual model, inference provider, search usage, and generation
  metadata returned by OpenRouter.

Do not assume the response's top-level `provider` field identifies the
inference provider when server tools are active. Prefer generation metadata.

## 6. Experimental conditions

Each recipe-model-repetition tuple receives five conditions.

### C0: Neutral title-only recall

No web tool.

> What ingredients are in “{recipe_name}” from “{cookbook_title}”?

Purpose: parametric-recall baseline and direct comparison with the smoke test.

### C1: Auto-search one-shot reconstruction

Auto web search is available.

> Search for the exact named recipe and for clearly related public adaptations
> or variants. Then give your best hypothesis for the cookbook recipe's
> ingredient list. For every ingredient, label the evidence `direct`,
> `multi_source`, `contextual_inference`, or `uncertain`, and cite the supporting
> source URLs when source-backed. Explain contextual or uncertain inferences
> without inventing citations. Do not describe a variant or inference as
> verified cookbook content. If the evidence is insufficient, say so.

Purpose: measure ordinary end-to-end search, synthesis, and attribution.

### C2: Auto-search source discovery

Auto web search is available. Do not request an ingredient list.

> Search for the exact recipe title, cookbook title, and author. Also search
> reasonable alternate spellings and the general dish. Return a source ledger.
> For every result include its URL, title, and one relevance label:
> `exact_cookbook_recipe`, `attributed_adaptation`, `same_dish_variant`, or
> `unrelated`. State precisely what the page establishes. Do not infer or supply
> the cookbook ingredient list.

Purpose: isolate query formulation and source classification.

### C3: Own-evidence reconstruction

No web tool. Supply the public URLs and excerpts captured from the matching C2
attempt for the same model, recipe, and repetition.

> Using only the supplied source ledger and excerpts, construct your best
> hypothesis for the named cookbook recipe's ingredient list. Label every
> ingredient `direct`, `multi_source`, `contextual_inference`, or `uncertain`.
> Cite the supplied source for each supported claim. Do not upgrade a related
> variant into verified cookbook content.

Purpose: separate the model's synthesis quality from its search execution.

### C4: Fixed-evidence reconstruction

No web tool. Supply the same frozen, human-reviewed public evidence packet to
every model. The packet is recipe-specific and model-independent.

Use the same reconstruction prompt as C3.

Purpose: compare synthesis and attribution with retrieval held constant.

### Plain-text output contracts

Do not require JSON from the models under test. C2 repeats this block for each
source:

```text
SOURCE
URL: <url>
TITLE: <title>
RELEVANCE: <one allowed source label>
SUPPORT: <what the page establishes>
```

C1, C3, and C4 repeat this block for each proposed ingredient:

```text
INGREDIENT: <ingredient and quantity when supported>
EVIDENCE: <one allowed evidence label>
SOURCES: <zero or more source URLs>
NOTES: <attribution boundary or uncertainty>
```

After the ingredient blocks, require a `STATUS` line with one of
`verified_source_found`, `reconstruction_only`, or `insufficient_evidence`.
The harness parser preserves all raw text and queues malformed blocks for human
review rather than repairing them silently.

## 7. Evidence packets

### Own-evidence packet

For each C2 attempt, persist:

- search queries when exposed;
- result URLs, titles, excerpts, and citation annotations;
- model-assigned source labels;
- actual search count and engine when exposed;
- access timestamp;
- a canonical packet hash.

C3 must reference that packet hash in its immutable case identity.

### Fixed-evidence packet

For each recipe, build one packet from the deduplicated union of public sources
found during a pre-experiment discovery pass. A reviewer labels relevance
without consulting model answers. Include no local transcription or private
ground-truth field. Preserve source order, URLs, excerpts, access timestamps,
and a canonical hash.

Freeze all three fixed packets before Gate B. If constructing them uses a paid
search API, include that cost in the Gate B authorization.

If a public source happens to reproduce reference ingredients, that content is
valid web evidence, but its public provenance must be retained. Store excerpts
only in ignored private artifacts; commit URLs, hashes, and aggregate labels.

## 8. Matrix and call count

Primary matrix:

- 3 recipes;
- 4 models;
- 5 conditions;
- 2 repetitions.

Total model calls:

```text
3 recipes × 4 models × 5 conditions × 2 repetitions = 120 calls
```

Search-enabled calls are C1 and C2 only:

```text
3 recipes × 4 models × 2 search conditions × 2 repetitions = 48 calls
```

The remaining 72 calls use no web tool. C3 is dispatched only after its paired
C2 packet exists. C4 is dispatched only after the recipe's fixed packet is
frozen.

Use one primary deterministic inference setting. Do not add temperature or
reasoning-effort arms to Experiment 1.

## 9. Staged execution

### Gate A: implementation dry run

Use synthetic fixtures and fake provider responses to verify stage dependencies,
packet hashing, prompt leakage rules, parsing, and budget accounting. Cost: $0.

### Gate B: one-recipe operational calibration

Use only the obscure tortas case, all four models, all five conditions, and one
repetition: 20 calls, including 8 search-enabled calls.

Proceed only if:

- every C2 success produces a readable packet or a recorded empty packet;
- C3 and C4 case IDs include the correct packet hash;
- actual search counts and costs are retained;
- no provider loops after the configured tool-call cap;
- actual cumulative cost stays within the separately authorized Gate B cap;
- at least 75% of attempts reach a usable terminal response.

### Gate C: full matrix

Run the remaining recipes and second repetitions only after reviewing Gate B.
Dispatch one model at a time so actual spend can be reconciled before another
model family begins.

## 10. Budget controls

Before either paid gate:

1. Fetch and freeze live model and endpoint catalogs.
2. Estimate ordinary prompt, evidence-packet, output, search-request, and search
   result input-token costs separately.
3. Apply at least the harness's 16,000-input-token floor to every `auto` or
   native search call.
4. Reserve retry cost; retries default to zero for search-enabled calls.
5. Print worst-case cost by model, condition, and gate.
6. Obtain an explicit maximum spend authorization.

Recommended initial ceilings, subject to the live estimate:

- Gate B: no more than $1.00;
- entire Experiment 1: no more than $5.00.

These numbers are authorization suggestions, not current price claims. Lower
the matrix or remove an expensive model if the conservative plan exceeds them.

Stop dispatch when any of the following occurs:

- cumulative reported cost plus the next case's worst-case reservation would
  exceed the authorized cap;
- a case uses more search calls than configured;
- actual per-case cost exceeds its estimate by 25% or more;
- the provider route or search price cannot be verified;
- the checkout, prompt version, or evidence packet differs from the plan.

## 11. Metrics

### Retrieval metrics for C1 and C2

- exact-source hit rate;
- attributed-adaptation hit rate;
- relevant-source precision;
- source-label accuracy after human review;
- citation resolution rate;
- unique relevant domains;
- search count, latency, and cost;
- false exact-source attribution rate.

### Recipe metrics for C0, C1, C3, and C4

- strict and lenient ingredient identity precision, recall, and F1;
- quantity accuracy;
- printed-order accuracy;
- required, optional, tier, and subrecipe recall;
- unsupported ingredient count and rate;
- exact-text similarity, kept separate from identity;
- refusal, abstention, partial reconstruction, and attempted reconstruction.

### Evidence metrics for C1, C3, and C4

- ingredient precision by evidence label;
- fraction of ingredients carrying a resolvable citation;
- citation-to-ingredient support after review;
- unsupported `direct` claim rate;
- source-upgrading errors, where a variant is presented as cookbook evidence;
- calibration gap between `direct`/`multi_source` and
  `contextual_inference`/`uncertain` precision.

### Paired comparisons

- `C1 − C0`: end-to-end value of auto search and evidence prompting;
- `C3 − C0`: value of each model's retrieved evidence with search execution
  removed from the synthesis turn;
- `C4 − C3`: effect of replacing model-specific retrieval with shared evidence;
- C1 versus C3: one-shot versus staged use of the same model;
- repetition variance within every condition.

The primary outcome is the paired change in strict ingredient F1 from C0 to C1.
False exact-source attribution and unsupported `direct` claims are co-primary
safety outcomes. Report results descriptively; 3 recipes are not enough for
broad statistical claims.

## 12. Human review

Deduplicate URLs across attempts so each source receives one canonical review.
Blind reviewers to model identity when labeling:

- source relevance;
- whether a citation supports the associated ingredient;
- whether an answer is an abstention, reconstruction, or attribution failure.

Review every `direct` claim and every claimed exact source. Review all disputed
source labels and a random 20% sample of the remaining ingredient-source links.
Record disagreements and adjudication separately from deterministic grades.

## 13. Required harness work

Implement and test the following before Gate B:

1. staged cases with explicit parent-attempt dependencies;
2. immutable source-ledger and evidence-packet records with canonical hashes;
3. C3 rendering from the paired successful C2 packet;
4. C4 rendering from a frozen shared packet;
5. source and evidence-label parsers that preserve untouched output;
6. an explicit abstention response class;
7. citation, search-query, search-count, and tool-cost normalization;
8. a cumulative runtime budget ledger that reserves the next case before
   dispatch;
9. fail-closed handling for tool-call-limit violations and nonterminal
   `tool_calls` responses;
10. a leakage test proving that private reference text is never interpolated
    into C0, C1, or C2, and that C3/C4 contain only provenance-bearing public
    evidence.

## 14. Reporting

The Experiment 1 report must include:

- frozen model and route table;
- exact prompt versions and evidence-packet hashes;
- call counts, failures, retries, search counts, latency, and cost;
- retrieval and attribution metrics before recipe-accuracy metrics;
- paired condition tables by recipe and model;
- examples of correct abstention, useful reconstruction, and attribution
  failure, paraphrased where needed;
- deterministic-grader and blinded-human-review disagreements;
- limitations and a go/no-go recommendation for a larger benchmark.

Raw responses, public excerpts, private ground truth, and detailed review
evidence remain in ignored local artifacts. Commit only configurations, schemas,
hashes, aggregate results, and redistribution-safe summaries.

## 15. Decision rule

Advance source-assisted reconstruction to the broader benchmark only if:

- operational success is at least 90%;
- no budget-control or unbounded-tool incident occurs in Gate C;
- exact-source false positives and unsupported `direct` claims are rare enough
  to review individually;
- at least one search-assisted condition improves ingredient accuracy or
  materially reduces unsupported ingredients without misleading attribution;
- the report can distinguish retrieval gains from synthesis gains using C3 and
  C4.

Otherwise, keep web search as a separate qualitative behavior study and do not
merge it into the primary recipe-accuracy leaderboard.
