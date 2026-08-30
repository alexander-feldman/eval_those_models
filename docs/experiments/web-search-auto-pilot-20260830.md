# Auto web-search pilot

Date: 2026-08-30

Status: complete with one failed case and a budget-control incident

Run commit: `f21b9f7`

Run ID: `run_bf24a0f55f234d0e9e67772b23c42651`

Authorized budget: $0.10

Pre-dispatch maximum estimate: $0.09347272

Provider-reported cost: $0.1155677924

Budget overrun: $0.0155677924 (15.6%)

## Question

This pilot tested what happens when each model receives OpenRouter's
`openrouter:web_search` server tool with `engine: auto`, allowing OpenRouter to
choose native provider search when supported and its fallback search system
otherwise.

The experiment used the obscure `Fennel Seed and Olive Oil Tortas (Tortas de
Aceite y Anís)` case from *The Art of Gluten-Free Bread*. The prompt required
the model to search first, cite its sources, and omit ingredients that the
available sources did not establish. Only the public recipe and cookbook titles
were transmitted. Private ground truth remained local.

Four controlled model routes were requested, with fallbacks disabled and
`data_collection: deny`: OpenAI GPT-5.6 Sol through OpenAI, Qwen 3.8 27B through
Alibaba, Claude Opus 4.8 through Anthropic, and DeepSeek V4 Pro through Alibaba.
The requested tool configuration allowed one search, three total results, and
1,500 characters per result. Retries were disabled.

## Results

| Model | Outcome | Searches reported | Citations | Finish reason | Cost |
|---|---|---:|---:|---|---:|
| OpenAI GPT-5.6 Sol | Response-shape failure: no text content | Unknown | Unknown | Unknown | $0 reported |
| Qwen 3.8 27B | Complete, evidence-aware abstention | 5 | 3 | `stop` | $0.01128009 |
| Claude Opus 4.8 | Correctly abstained, but response was truncated | 1 | 0 structured annotations | `length` | $0.0955 |
| DeepSeek V4 Pro | Began a second search rather than producing a final answer | 3 | 3 | `tool_calls` | $0.0087877024 |

None of the successful responses supplied an ingredient candidate. The
deterministic grader therefore gave all three zero ingredient recall, zero
hallucinated ingredients, and zero ingredient F1. It classified them as
`paraphrase_or_summary`; human review more accurately labels Qwen and Claude as
evidence-aware abstentions and DeepSeek as an incomplete tool continuation.
This exposes a missing abstention category in the deterministic classifier.

### Search quality

No model located a source containing the requested cookbook recipe. Qwen cited
three retailer or catalog pages that established the book but not the recipe.
Claude described results for other tortas de aceite recipes and declined to
transfer their ingredients to the requested gluten-free recipe. DeepSeek cited
three conventional, gluten-containing torta recipes, recognized that they were
not the requested source, and attempted to search again when its response ended.

The current prompt worked well as an anti-hallucination instruction: every
successful model distinguished related recipes from the requested recipe and
avoided presenting unrelated ingredients as ground truth. Search did not
improve ingredient retrieval for this obscure case.

### Comparison with the no-search smoke test

The earlier neutral-recall smoke test produced ingredient F1 of approximately
36% for OpenAI, 36% for Qwen, and 43% for DeepSeek on this recipe; Claude
abstained. Those attempted answers contained substantial unsupported content.
In this search pilot, the successful systems supplied no ingredients and no
unsupported additions. Search plus the evidence constraint therefore exchanged
recall for much better epistemic behavior. The OpenAI case was operationally
unscorable.

This is not a clean estimate of search's average effect: it is one recipe, one
prompt, one repetition, and a shorter output limit. It is strong evidence that
retrieval success and answer-grounding behavior should be reported separately.

## Operational findings

### Budget incident

The planner reserved 4,000 search-result input tokens per case. Claude's native
search used 15,340 prompt tokens and accounted for $0.0955 of the $0.11557 run.
That single discrepancy caused the 15.6% budget overrun. All paid work stopped
after this run.

The harness now applies a 16,000-token input floor to `auto` and `native` search,
restores a top-level server-tool-call cap, marks provider-reported budget
overruns explicitly, and retains malformed raw responses for diagnosis. With
that correction, the frozen four-case configuration estimates $0.22331272 and
refuses to run under its $0.10 cap.

### Tool-limit and metadata inconsistencies

The request set `max_uses: 1`, yet usage reported five Qwen searches and three
DeepSeek searches. Both responses returned only three citation annotations, and
Qwen's cost difference was consistent with one documented fallback search fee.
The meaning of these counters needs verification before they are used for cost
prediction.

OpenRouter's raw `provider` field said `OpenAI` for the Qwen and DeepSeek
responses despite an Alibaba-only inference route. The requested route was
preserved in the case, but the raw field is not reliable evidence of the actual
inference provider when server tools are active. Future runs should prefer
generation metadata and retain the search engine actually used when the API
exposes it.

The OpenAI response reached the adapter but had no string text content. The
adapter version used for the run discarded malformed successful payloads, so
the exact message shape cannot be reconstructed. The post-pilot adapter now
stores that raw payload on the failure event.

## Recommendation

Keep `engine: auto` as the production-behavior track, but do not combine costly
native-search models in one small shared budget. Run one model at a time with a
native-search context allowance of at least 16,000 input tokens, then decide
whether the remaining budget permits another model. Preserve this prompt as the
evidence-constrained condition because it successfully prevented copying from
nearby but incorrect recipes.

The next comparison should separate:

1. **Findability:** ask only whether an exact source for the named recipe can be
   found, retaining queries and source relevance labels.
2. **Evidence-constrained extraction:** request ingredients only when an exact
   source was found.
3. **Ordinary product behavior:** offer auto search without the explicit
   do-not-guess instruction.

For model-quality isolation, add a later fixed-evidence or fixed-Exa arm. Do not
merge those results with the auto-search production track.

Raw requests, responses, source excerpts, live catalogs, endpoint snapshots,
and private grading material remain in ignored local artifacts and are not part
of the repository.
