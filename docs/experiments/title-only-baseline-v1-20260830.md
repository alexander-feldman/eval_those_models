# Title-only baseline v1

Date: 2026-08-30

Status: complete; ingredient scores remain provisional pending grader repair

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

The current deterministic output is not suitable for a leaderboard. It labeled
45 responses as partial reproductions, but the human pass found only 34 specific
reconstruction attempts; navigation suggestions and explicitly hypothetical
ingredient lists were frequently parsed as answer content. It also lacks
abstention and false-premise categories.

Identity matching materially undercounted obvious culinary matches because of
pluralization, modifiers, compound reference rows, and alternatives. The grader
created 71 review items across 90 responses, too many to function as a focused
exception queue. Quantity and order results should not be reported until the
reference round-trip work and response parsing are repaired.

The next review step is to verify one-to-one ingredient matches for the 34
specific attempts after those repairs, then repeat only the eight truncated
neutral cases with a larger output ceiling. Raw requests, responses, usage,
catalogs, endpoints, and private review packets remain ignored local artifacts.
