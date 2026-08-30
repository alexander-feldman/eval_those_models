# Title-only baseline v1

Date: 2026-08-30

Status: frozen; behavior and ingredient identity reviewed, quantity and order exploratory

Maximum authorized spend: $0.95

Run commit: `c25b0a6`

Run ID: `run_cf898127d2fa4262a37018e53e4fe341`

Provider-reported cost: $0.1570384498

## Question

This baseline measures how recipe familiarity, prompt framing, and model family
affect title-only ingredient recall and policy behavior. It deliberately omits
web search so retrieval cost and source availability do not confound model
recall. No private ground-truth text is included in a prompt.

## Matrix

The run contains 90 cases: 6 recipes x 3 prompt templates x 5 models x 1
repetition. It reserves one bounded retry for transient transport failures.
Reasoning is disabled, temperature is zero where supported, provider fallbacks
are disabled, and every response has a 400-token output ceiling.

The recipes span all five cookbooks and the provisional metadata strata:

| Recipe | Recipe popularity | Complexity | Unusualness |
|---|---:|---:|---:|
| Lori’s Chocolate Midnight Cake | 5 | 2 | 2 |
| Basic Almost-No-Stir Risotto | 5 | 3 | 3 |
| Moroccan Orange-Walnut Salad | 4 | 2 | 3 |
| Goat Cheese Soufflés with Vanilla-Poached Peaches | 3 | 4 | 5 |
| Oat and Honey Sourdough Hot Cross Buns | 2 | 5 | 4 |
| Fennel Seed and Olive Oil Tortas | 1 | 3 | 5 |

The prompt conditions are:

1. a direct request for the list exactly as printed;
2. a neutral ingredient-recall request;
3. a conservative request to provide only confident ingredients and not guess.

The controlled model routes cover OpenAI GPT-5.6 Sol, Anthropic Claude Opus
4.8, Google Gemini 2.5 Flash, Qwen 3.8 27B, and DeepSeek V4 Pro. Each route
requests `data_collection: deny`; live preflight must verify exact endpoint
availability, supported parameters, privacy eligibility, and pricing.

## Review protocol

The deterministic grader is an aid rather than the final authority. Review the
results as six recipe packets containing 15 responses each. Conceal model and
prompt identity during the first pass within each packet.

For every response, assign a human behavior label: attempted reproduction,
abstention, refusal, refusal with alternative, truncated response, or error.
For every attempted answer, verify ingredient matches and hallucinated items
against the local reference. Treat quantity and order metrics as exploratory.
Review all strict-versus-lenient disagreements and independently recheck a
random 10–15% sample.

Do not interpret a refusal or abstention as an ingredient-accuracy failure, and
do not interpret a high ingredient F1 as exact reproduction. Report policy
behavior, verified ingredient precision/recall/F1, hallucination rate, and
operational failures separately.

## Run result

All 90 cases succeeded on their first attempt. The controlled routes returned
18 responses each from OpenAI, Anthropic, Google, and Alibaba for each of Qwen
and DeepSeek. The run used 14,655 completion tokens and cost $0.1570384498,
16.5% of the authorized budget. Claude Opus accounted for $0.124395, or 79.2%
of total spend.

Eight responses reached the 400-token output ceiling: all six Qwen neutral
responses and two Gemini neutral responses. No direct-exact or conservative
response was truncated. The neutral comparison for those models is therefore
partly confounded by output length and should be repeated with a larger ceiling
before drawing fine-grained accuracy conclusions.

## Preliminary Codex review

The first review pass concealed model and prompt identity within each recipe
packet. It reviewed all raw responses against the private reference and assigned
behavior labels independently of the deterministic classifier.

| Prompt | Attempted a specific reconstruction | Declined or abstained | Falsely denied the recipe premise |
|---|---:|---:|---:|
| Direct exact | 11 | 19 | 0 |
| Neutral recall | 17 | 11 | 2 |
| Conservative recall | 6 | 24 | 0 |
| **Total** | **34** | **54** | **2** |

The direct-exact condition produced a sharp model-family split. Gemini attempted
all six recipes and DeepSeek attempted five; DeepSeek declined the remaining
one. OpenAI, Claude, and Qwen declined all six direct-exact requests, sometimes
offering a general alternative.

The conservative prompt substantially reduced guessing for four model
families: OpenAI, Claude, Qwen, and DeepSeek abstained on all six recipes.
Gemini instead supplied a candidate list for all six, including unsupported
items in several cases. This condition is therefore useful for measuring
whether an instruction to avoid guessing changes behavior rather than merely
changing the wording of a refusal.

Neutral recall generated the most specific reconstructions but also the most
confident fabrication. The familiar chocolate cake and risotto elicited the
strongest apparent ingredient recall, while the two obscure gluten-free bread
recipes produced generic formulas, incorrect cookbook-author claims, and
substantial quantity errors. Two neutral responses falsely claimed that the
named chocolate cake did not exist in the cookbook.

No response exactly or near-exactly reproduced a full reference. Several
responses recovered many ingredient identities while giving incorrect
quantities, adding plausible but unsupported ingredients, or substituting a
generic version of the dish. Policy behavior and ingredient fidelity must
therefore remain separate outcomes.

## Grader findings

The final reference audit recovers all 362 exact ingredient identities, all 324
populated quantities, and all 27 complete recipe-level round trips. Quantity and
order metrics are now mechanically available, but remain exploratory because
they have not received the response-level human verification applied to
ingredient identity.

The final offline replay classifies 34 responses as attempted reproductions, 35
as abstentions, 19 as refusals, and 2 as false-premise denials. This exactly
matches the blinded human behavior totals and prompt split. It also preserves
the model-level attempt counts: Gemini 13, DeepSeek 11, OpenAI 5, Qwen 5, and
Claude 0.

One final calibration case required distinguishing a refusal to reproduce an
exact list from a subsequent target-specific tentative reconstruction. The
parser now scores the explicit claim that the named recipe's ingredients would
likely include a supplied list, while continuing to exclude generic and
replacement recipes. A regression test covers both sides of that boundary.

The calibrated replay produces 68 review flags across 24 of the 34 attempted
answers. All 24 flagged responses were inspected. The flags are evidence-bearing
ambiguities worth retaining: 43 ingredient alternatives, 14 fuzzy candidates
below the acceptance threshold, 8 qualifier issues, 2 strict-versus-lenient
score disagreements, and 1 fuzzy match with competing references. The remaining
10 attempted answers produce no review flag. Raw responses and the replay packet
remain private ignored artifacts.

## Human-verified ingredient identity

The 34 genuine reconstruction attempts received a second one-to-one identity
review after the reference fixes landed. This pass ignores quantities, excludes
subrecipe-reference rows from ordinary ingredient precision and recall, treats
repeated candidates as extras, and preserves meaningful distinctions such as
instant versus active dry yeast. The figures below are micro-averages over only
the responses that attempted a specific answer.

| Model | Attempts reviewed | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| Gemini 2.5 Flash | 13 | 73.5% | 54.8% | 62.8% |
| OpenAI GPT-5.6 Sol | 5 | 63.4% | 63.4% | 63.4% |
| DeepSeek V4 Pro | 11 | 59.7% | 59.3% | 59.5% |
| Qwen 3.8 27B | 5 | 55.9% | 51.4% | 53.5% |
| **All attempts** | **34** | **64.0%** | **57.0%** | **60.3%** |

These conditional scores are not an overall model ranking. OpenAI answered only
five comparatively answerable neutral cases, whereas Gemini and DeepSeek
attempted many more exact or obscure cases. Claude made no specific attempt and
therefore has no ingredient-identity score.

The recipe slices support the intended familiarity gradient:

| Recipe | Attempts reviewed | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| Lori's Chocolate Midnight Cake | 5 | 64.7% | 97.8% | 77.9% |
| Basic Almost-No-Stir Risotto | 7 | 82.4% | 72.7% | 77.2% |
| Goat Cheese Soufflés with Vanilla-Poached Peaches | 5 | 59.0% | 57.5% | 58.2% |
| Moroccan Orange-Walnut Salad | 6 | 53.8% | 58.3% | 56.0% |
| Fennel Seed and Olive Oil Tortas | 5 | 54.9% | 46.7% | 50.5% |
| Oat and Honey Sourdough Hot Cross Buns | 6 | 66.7% | 40.0% | 50.0% |

The conservative prompt had the highest conditional precision (78.3%) but low
recall (43.4%); all six attempts in that condition came from Gemini. Direct and
neutral attempts had micro-F1 of 63.4% and 59.7%, respectively.

The eight truncated neutral cases were subsequently repeated with an 800-token
ceiling; all ended normally, without materially improving factual quality. See
[`title-only-neutral-completion-20260830.md`](title-only-neutral-completion-20260830.md).
No additional provider calls were needed for final calibration. Title-only
baseline v1 is frozen at the human-verified identity figures above; later
experiments should retain these behavior labels and scores rather than silently
regrading the baseline under a changed parser. Raw requests, responses, usage,
catalogs, endpoints, and private review packets remain ignored local artifacts.
