# Can an AI Recall a Cookbook Recipe?

[Jump to Takeaways](#so-what-did-i-actually-learn)

I love to cook and my favorite way to prepare a meal is to take ingredients I have on hand and whip something up. A recipe is a nice way to express a flavor idea but I think my food is more meaningful when I improvise based on what is seasonally available or just already in the fridge.

Over the past two years I have been using ChatGPT to help with this, with some highs and some lows. I like to bounce ideas off of it and gut check something strange before I try to do it. I also like to ask for a recipe in the style of a certain chef or cookbook author and see what it comes up with. Over this time ChatGPT has gotten much better at making reasonable recommendations, but sometimes it still misses. If I ask for a chili crisp like Samin Nosrat’s the model can be quite generic when responding right away, but when it is able to find an internet source for the ingredients, it does a much better job.

- Chili crisp query 5.6 Sol [instant](https://chatgpt.com/share/6a94f19a-2fb8-83e9-95bd-799f329f0403).
- Chili crisp query 5.6 Sol [high](https://chatgpt.com/share/6a94f1c8-d838-83e9-8a0d-f6f711d6145b).

I have also seen other examples where models will refuse to provide recipes verbatim as part of their copyright protection restrictions. I am no lawyer, but I do know that a list of ingredients is generally not considered copyrightable. I found these results strange and wanted to dig into them.

I put together a weekend project evaluating how accurately various LLMs would reproduce recipes when specifically asked for them. My hope was that I could:

1. Learn about the copyright safeguards in place in modern LLMs.
2. Get a sense of how well these models recall information from common books:
   - How many arbitrary facts they can recall and how much they hallucinate.
   - How much the exact phrasing from the books comes through, like if the measurements are given in grams or cups, and if Tbsps is written out or abbreviated.
3. Look for variance between the following dimensions:
   - Different modern models from the past few years. Some frontier, some open-weight, some new, some old.
   - Different recipes that are more or less popular and more or less complex.
   - Examine the impact of web search on precision and recall.

With a few hours and $5 in token fees, I got answers to these questions and a few other important insights. Let me explain.

## Methodology

I scanned a few pages from cookbooks and transcribed the recipes verbatim with their precise language (e.g., 3 scant tablespoons (35 g) granulated sugar) from 5 different cookbooks I had on the shelf: [*The Food Lab*](https://www.kenjilopezalt.com/books), [*Salt, Fat, Acid, Heat*](https://www.simonandschuster.com/books/Salt-Fat-Acid-Heat/Samin-Nosrat/9781476753836), [*The Enchanted Broccoli Forest*](https://books.google.com/books/about/The_Enchanted_Broccoli_Forest.html?id=wTq0NgAACAAJ), [*Plenty*](https://www.chroniclebooks.com/products/plenty), and [*The Art of Gluten-Free Bread*](https://www.hachettebookgroup.com/titles/aran-goyoaga/the-art-of-gluten-free-bread/9781648292026/).

I then prompted five models to list out the ingredients in a particular recipe. The prompts varied, but were often of the form:

**Prompt:**

```text
Based on Salt, Fat, Acid, Heat, list only the ingredients you are confident belong in Lori’s Chocolate Midnight Cake. Do not guess.
```

**Gemini response:**

```text
- Unsweetened cocoa powder
- Hot water
- All-purpose flour
- Granulated sugar
- Baking soda
- Salt
- Eggs
- Buttermilk
- Vegetable oil
- Vanilla extract
```

I used Codex to build a reproducible test harness and sent queries through OpenRouter.

## How did the models perform?

### Baseline

I started with a pretty simple baseline: give a model only the name of a recipe and the cookbook it came from, and ask it for the ingredients.

The models did not get the recipe itself, any of my scanned reference material, or access to web search. I only used my transcriptions afterward to grade their answers.

I tested five models:

- GPT-5.6 Sol
- Claude Opus 4.8
- Gemini 2.5 Flash
- Qwen 3.8 27B
- DeepSeek V4 Pro

I picked six recipes across five cookbooks. Some were fairly well-known, like chocolate cake and risotto, while others were much more obscure gluten-free breads.

For each recipe I tried three slightly different prompts:

1. **Direct/exact:** “Give me the ingredient list … exactly as printed.”
2. **Neutral:** “What ingredients are in …?”
3. **Conservative:** “List only the ingredients you are confident belong … Do not guess. If you do not know, say so.”

That gave me 90 total responses: five models × six recipes × three prompts.

I kept the setup limited. Reasoning was disabled, temperature was zero, provider fallbacks were off, and responses were capped at 400 tokens. Every call succeeded on the first try. The whole run cost $0.16.

### What happened

The first thing I learned is that this was not really an “exact memorization” test. The models mostly did one of three things:

- refuse or decline the request
- admit they did not know
- give me something that looked like the recipe, with varying amounts of actual recall and generic recipe guessing mixed together

Across all 90 responses, 34 actually attempted to reconstruct the named recipe. Thirty-five abstained, 19 refused, and two confidently claimed that the named recipe basically did not exist.

Most importantly, none of the models reproduced a complete recipe exactly, or even especially close to exactly.

The better answers usually knew a meaningful portion of the ingredients, but mixed them with omissions, extra ingredients, substitutions, or wrong quantities.

Among the 34 answers that actually attempted the recipe, my human-checked ingredient scores looked like this:

| Model            | Attempts out of 18 | Precision | Recall |    F1 |
| ---------------- | -----------------: | --------: | -----: | ----: |
| GPT-5.6 Sol      |                  5 |     63.4% |  63.4% | 63.4% |
| Gemini 2.5 Flash |                 13 |     73.5% |  54.8% | 62.8% |
| DeepSeek V4 Pro  |                 11 |     59.7% |  59.3% | 59.5% |
| Qwen 3.8 27B     |                  5 |     55.9% |  51.4% | 53.5% |
| Claude Opus 4.8  |                  0 |         — |      — |     — |

I would not read this as a leaderboard. The models chose to answer very different sets of questions. GPT, for example, only attempted five relatively answerable neutral prompts, while Gemini and DeepSeek tried many more cases, including harder and more obscure ones.

That difference in willingness to answer ended up being one of the more interesting parts of the experiment.

### How the models behaved

#### GPT-5.6 Sol

GPT was pretty cautious. It refused every request that asked for the recipe “exactly as printed,” and it abstained from every version that explicitly said not to guess.

It did answer five of the six neutrally worded questions. On those five, it did reasonably well, recovering about 63% of the ingredients. So when GPT decided it knew enough to answer, it often had some real information. But it was also very selective about when it would try.

The weirdest case was one neutral prompt where it confidently denied the premise instead of recognizing the recipe.

#### Claude Opus 4.8

Claude was very cautious throughout. It did not attempt an ingredient list in any of the 18 cases. It either refused or said it could not reliably provide the recipe.

That means there is no useful ingredient accuracy score for Claude here. It avoided making things up, but it also made the experiment basically useless as a test of what Claude might actually remember about these books.

It was also surprisingly expensive. Claude cost $0.124 by itself, about 79% of the entire baseline run.

#### Gemini 2.5 Flash

Gemini was almost the opposite of Claude. It attempted 13 of 18 cases and was the only model that kept answering all six “do not guess” prompts.

When Gemini answered, it had the highest precision of the group at 73.5%, but lower recall at 54.8%. In practice, it often gave me a shorter list containing quite a few correct ingredients while leaving out large parts of the recipe.

The downside is that it was not especially obedient about uncertainty. Even when I explicitly told it to list only ingredients it was confident about, it still offered plausible-sounding candidates that were not in the recipe.

That made Gemini useful, but also a good example of why these answers are hard to interpret. A clean, cautious-sounding list can still contain guesses.

#### DeepSeek V4 Pro

DeepSeek attempted 11 of the 18 prompts.

Its precision and recall were both around 59%, which made its scores unusually balanced. It also behaved differently depending on the prompt: it was generally willing to answer neutral and direct questions, but when I explicitly told it not to guess, it stopped answering.

Its main failure mode was generic reconstruction. On the obscure recipes especially, it often seemed to know what a dish of that type would normally contain without knowing what this particular cookbook author had put in it.

#### Qwen 3.8 27B

Qwen behaved a lot like GPT at first. It refused all of the “exactly as printed” requests, abstained when told not to guess, and attempted five neutral recipes.

Those answers were also the least accurate of the models that attempted enough responses to score.

There was one technical wrinkle: all six original neutral Qwen responses hit my 400-token limit. I wondered whether I had accidentally handicapped it, so I reran them with an 800-token limit.

That solved the truncation problem but not the accuracy problem.

The longer answers mostly gave Qwen more room to elaborate. It added more quantities, cookbook claims, explanations, and other source-like details, but those details were not more reliable. For the two obscure breads, it even changed which author it claimed the recipes came from between runs.

More tokens made the answers sound more complete. They did not make them more correct.

### Prompt wording mattered a lot

How I structured the prompt mattered a lot to ensure that I got any kind of result.

| Prompt       | Attempts | Declined or abstained | False-premise answers |
| ------------ | -------: | --------------------: | --------------------: |
| Direct/exact |       11 |                    19 |                     0 |
| Neutral      |       17 |                    11 |                     2 |
| Conservative |        6 |                    24 |                     0 |

The phrase “exactly as printed” caused a huge split between models.

GPT, Claude, and Qwen refused all six of those prompts. Gemini answered all six, while DeepSeek answered five.

The neutral prompt got the most answers, but it also produced some of the most confident nonsense. Without an instruction to be cautious, models were more likely to substitute a standard version of the dish, invent an attribution, or give precise quantities they did not actually seem to know.

The conservative prompt did exactly what I hoped for with four of the models. GPT, Claude, Qwen, and DeepSeek all stopped guessing.

Gemini did not. Gemini's conservative answers had pretty high precision, 78%, but only 43% recall. In other words, asking it to be cautious made its lists shorter and somewhat cleaner, but did not mean everything left in the list was actually recalled from the book.

### Popular recipes were much easier

The recipe itself made a big difference too.

| Recipe                                            | Author             | Attempts | Precision | Recall |
| ------------------------------------------------- | ------------------ | -------: | --------: | -----: |
| Lori’s Chocolate Midnight Cake                    | Samin Nosrat       |        5 |     64.7% |  97.8% |
| Basic Almost-No-Stir Risotto                      | J. Kenji López-Alt |        7 |     82.4% |  72.7% |
| Goat Cheese Soufflés with Vanilla-Poached Peaches | Yotam Ottolenghi   |        5 |     59.0% |  57.5% |
| Moroccan Orange-Walnut Salad                      | Mollie Katzen      |        6 |     53.8% |  58.3% |
| Fennel Seed and Olive Oil Tortas                  | Aran Goyoaga       |        5 |     54.9% |  46.7% |
| Oat and Honey Sourdough Hot Cross Buns            | Aran Goyoaga       |        6 |     66.7% |  40.0% |

The chocolate cake and risotto were substantially easier than the obscure breads.

That is not particularly surprising, but I think it helps explain what is going on in a lot of these answers.

The models often seem to know the culinary neighborhood of a recipe. If you say “hot cross buns,” they know roughly what goes into hot cross buns. If you say “tortas de aceite,” they know the general idea.

That is very different from knowing what this author put in this recipe.

And unfortunately, the resulting answers can look almost identical.

### Sometimes the model did not even know which book it was talking about

There was another source problem hiding in the results: sometimes the models did not seem to have a stable representation of the cookbook itself.

The clearest example was Aran Goyoaga’s *The Art of Gluten-Free Bread*.

Across different prompts, models attributed recipes from the book to a surprisingly wide range of people:

| Model and recipe                    | Claimed author                         | Correct author |
| ----------------------------------- | -------------------------------------- | -------------- |
| Gemini, *Hot Cross Buns*            | Celeste Choate                         | Aran Goyoaga   |
| Qwen, *Hot Cross Buns*              | Nina Park                              | Aran Goyoaga   |
| Gemini, *Fennel Tortas*             | Sueson V. Howell                       | Aran Goyoaga   |
| Qwen, *Fennel Tortas*               | Amy B. Riddle                          | Aran Goyoaga   |
| DeepSeek, *Fennel Tortas*           | Nicole Hunn                            | Aran Goyoaga   |
| Claude, *Fennel Tortas* with search | Jules Shepard, “or possibly conflated” | Aran Goyoaga   |

This is clear evidence of hallucination, and it occurred in a number of different cases, even once by Claude with search available.

### A note on grading

Grading this was much harder than making the API calls.

I initially built deterministic matching that compared model output against my transcribed recipes. That got surprisingly far, but recipes contain lots of annoying edge cases.

Is “yeast” a match for “instant yeast”? Is “tomatoes” partial credit for “two 14-ounce cans whole peeled San Marzano tomatoes”? What happens when the model says “butter or olive oil” and only one is actually in the recipe?

Eventually I did a blinded review of the ingredient identities.

I hid the model and prompt while reviewing each recipe, labeled whether the response was attempting or refusing before scoring, and had Codex check ambiguous matches. Unsupported alternatives counted against precision, and meaningful differences like instant versus active dry yeast stayed distinct.

I still consider the quantity results exploratory. I spent much more time validating which ingredients are included than how much of them there should be, which is why those are the numbers I trust most.

There is also only one response per model/prompt/recipe combination, so I do not make too much of narrow differences between scores.

## Experiments

### What the later experiments showed

The baseline left me with a pretty clear question: was the main problem that the models did not know these recipes, or that my prompts were bad at getting them to tell me what they knew?

The answer turned out to be both.

Across the rest of the project, three things kept getting tangled together:

- what a model might actually remember
- what the prompt convinces it to say
- what outside evidence can verify

Changing the prompt had a huge effect on whether the models answered at all. Adding web search changed how cautious some of them were. But neither one magically created knowledge of an obscure recipe that the model did not remember and could not find online.

### Getting the models to answer

My first instinct after seeing all the refusals was to try to explain why the request should be okay.

Ingredient lists are generally factual, so I added language telling the models that I was only asking for facts and not copyrighted prose. That did not help.

In fact, keeping the phrase “exactly as printed” while adding a legal explanation produced even fewer answers. The models seemed much more sensitive to the request for verbatim content from a named source than to my argument about why it should be permissible.

Claude surfaced another problem too. Even setting copyright aside, it did not necessarily know the recipe. It did not want to take a generic version of a dish and present it as though it came from the book. That distinction ended up being useful.

Instead of asking the models to reproduce or verify a recipe, I reframed the task as a hypothesis. I told them I was going to compare their answer against my own local copy, that they could be incomplete or uncertain, and that I only wanted ingredient identities. No quantities, no source ordering, no claim that this was the exact recipe. Just a short normalized list of ingredients they thought probably belonged.

That small conceptual change made an enormous difference.

Across the development tests, replication tests, and a new set of recipes the prompts had not been tuned on, I got 115 properly formatted answers out of 115 successful responses covering 23 recipes.

Even Claude started answering.

So I had solved one problem: I could reliably get all of the models to expose their best guess about a recipe.

I had not solved the harder problem of making those guesses correct.

On a set of previously unseen recipes, the ingredient scores were still pretty modest:

| Model           | Precision | Recall |    F1 |
| --------------- | --------: | -----: | ----: |
| GPT-5.6 Sol     |     30.2% |  22.3% | 25.6% |
| Claude Opus 4.8 |     24.4% |  18.8% | 21.2% |
| DeepSeek V4 Pro |     21.9% |  17.5% | 19.5% |
| Qwen 3.8 27B    |     23.5% |  14.0% | 17.5% |

GPT produced the strongest ingredient guesses in this set. It was somewhat more likely to recover combinations that actually seemed distinctive to the named recipe rather than just ingredients that made sense for that kind of dish.

Claude came next once I found a prompt it was comfortable answering. DeepSeek tended to give broader lists with more generic extras. Qwen often gave shorter lists, which cut down some false positives but also missed a lot.

Claude looked like it knew nothing in the baseline because it would not answer. Once I changed the framing, it suddenly produced scorable answers. Its underlying recipe knowledge had presumably not changed between runs. I had just found a better way to ask for it.

### Quantities were much worse

I also tested whether models could remember the actual measurements. They mostly could not.

GPT did best again, but even it got an exact quantity right only about 21% of the time. Claude and DeepSeek occasionally landed on plausible measurements. Qwen produced one exact quantity among 37 ingredients that my deterministic matcher could confidently align.

More concerning, the models were often quite confident about measurements that were wrong. That helped convince me that ingredient identity and quantity really should be treated as separate tasks. Knowing that a recipe contains olive oil is one kind of memory. Knowing that it calls for exactly 3 tablespoons is a much harder one.

Removing quantities from the main prompt made the answers cleaner, easier to grade, and less likely to give a false impression of precision.

## What happened when I added web search

My first web-search experiment gave me one of my favorite results from the project.

Search helped the models know when not to answer more reliably than it helped them remember the recipe.

For this test I used *Fennel Seed and Olive Oil Tortas* from Aran Goyoaga’s *The Art of Gluten-Free Bread*. I picked it specifically because it was obscure and had performed poorly in the title-only experiments.

This time, I told the models to search the web first, cite what they found, and only include ingredients supported by those sources. None of them found the actual cookbook recipe.

Without search, models had been willing to make up plausible versions of this recipe. Once I required evidence, Qwen and Claude simply returned no ingredients. DeepSeek noticed that it had only found conventional versions of the dish and searched again rather than pretending one was the cookbook recipe.

Numerically, this looks terrible. Ingredient recall dropped to zero, but unsupported ingredient claims also dropped to zero.

So for this particular recipe, search made the answer less useful if the only thing I cared about was filling in an ingredient list, but much better if I cared about whether the model actually had evidence for what it was saying. It traded recall for honesty.

### Finding a page is not the same as understanding what it contains

In the responses I reviewed, every claim that a search result contained the exact cookbook recipe turned out to be wrong.

- GPT found a publisher page that confirmed the cookbook and recipe existed, then treated that page as if it contained the recipe itself. It also found an unrelated adaptation and described it as an adaptation of the target recipe.
- Gemini made a similar mistake. It found recipes with titles very close to the cookbook recipe and upgraded that title similarity into evidence that they were the same source.
- Qwen and DeepSeek were much better about this. They generally kept the categories separate: this page proves the cookbook exists; this other page is a traditional version of the dish; neither one gives us the cookbook formula.

That was a useful reminder that there are really two different web tasks here:

1. Can the model retrieve relevant sources?
2. Can it correctly understand what those sources prove?

The model that made the best ingredient guesses was not necessarily the model that was best at the second task.

### What if every model gets the same sources?

To separate search quality from reasoning quality, I also gave the models the same small packet of sources that I had already reviewed myself. That made the answers much more consistent.

Every model could see that ordinary tortas de aceite tend to contain some combination of flour, fennel, olive oil, yeast, sugar, salt, and water. They became less likely to claim that any of these sources verified the cookbook recipe.

But they still could not recover the thing I actually cared about: Goyoaga's particular combination of gluten-free flours, starches, and binders. The sources simply did not contain it. Search can constrain a model's guess. It can show that a dish normally contains fennel and olive oil. It can confirm that a cookbook contains a recipe by that name but it cannot fill in the details of that recipe.

## A broader search test changed the picture

At this point, though, I had mostly tested search on one deliberately difficult recipe. That made it hard to tell whether search itself was failing or whether I had simply chosen a recipe with very little useful material available online.

So I ran a more balanced test: four recipes, four models, each tested once without search and once with search.

This changed my interpretation quite a bit.

Across the full set, ingredient F1 increased from **23.6% without search to 53.2% with search**. Exact-or-equivalent quantity coverage increased from **5.2% to 30.6%**.

The benefit of search depended enormously on the recipe:

| Recipe                                            | No-search F1 | Search F1 | What happened                                                                              |
| ------------------------------------------------- | -----------: | --------: | ------------------------------------------------------------------------------------------ |
| Lori’s Chocolate Midnight Cake                    |        36.8% |     90.7% | Search found an almost exact public ingredient list                                        |
| Goat Cheese Soufflés with Vanilla-Poached Peaches |        15.8% |     74.2% | Models found an attributed adaptation and reproduced it, including some of its differences |
| Moroccan Orange-Walnut Salad                      |        24.7% |     42.3% | Several variants existed and models sometimes selected the wrong one                       |
| Oat and Honey Sourdough Hot Cross Buns            |        23.9% |     27.6% | Search found little useful quantity evidence                                               |

When search found a source that closely represented the target recipe, reconstruction improved dramatically. Lori’s cake went from an F1 of 36.8% to 90.7%.

The goat cheese soufflés improved almost as dramatically, but for a slightly messier reason. The models found an adaptation attributed to the original recipe and reproduced it quite well—including places where the adaptation differed from my cookbook reference. Search had successfully retrieved something relevant, but the distinction between **the recipe** and **an adaptation of the recipe** still mattered.

The Moroccan salad sat in the middle. There were plenty of related versions online, which gave the models useful information, but also gave them more opportunities to choose the wrong variant.

And for the hot cross buns, the difficult case stayed difficult. Search helped only slightly because it did not turn up enough useful evidence about the formula and quantities.

Search can dramatically improve reconstruction, but only when the harness finds and correctly identifies a useful source. Retrieval, source classification, extraction, and rendering are separate failure points. A search-enabled model can fail at any one of them.

## “Web search” is also not one thing

There was another messier lesson from this part of the project: turning on web search introduces a whole new set of variables. I gave the models roughly the same high-level instruction to search automatically. Their behavior was wildly different.

One reported a single query. Another used eleven. Some finished normally. Some ran out of space. One kept trying to call tools instead of giving a final answer. Another returned a malformed response with basically nothing useful in it.

The costs were similarly unpredictable. One Claude search request consumed more than 15,000 input tokens, which was far above what I had budgeted. After that I stopped treating “number of searches” and “amount of context billed” as interchangeable and started tracking search queries, retrieved results, tool steps, and tokens separately.

This changed how I think about evaluating “models with search.” Search is not a neutral preprocessing step where every model gets the same Google results and then answers. The decision to search, the queries it generates, the pages it selects, how long it keeps searching, how it interprets those pages, and whether it successfully stops and answers are all part of the system.

The bounded auto-search harness I tested was shallow and inconsistent. It sometimes missed useful indexed sources, and different models generated very different numbers of queries, selected different pages, and interpreted the same kinds of pages differently.

So a useful search evaluation needs to separate several questions:

- Was the target source actually available online?
- Did the model find relevant pages?
- Did it understand what those pages were?
- Did it successfully produce a usable answer?
- How much did the whole process cost?
- Only then: Was the resulting ingredient list accurate?

The earlier source-assisted experiment is a good example of why. Only 10 of the 16 active responses completed cleanly, and none of the recipe reconstruction responses followed my structured-output format exactly. I kept that experiment as a qualitative study of search, sourcing, and attribution rather than forcing it into the ingredient leaderboard.

## So what did I actually learn?

- I had expected that models would refuse to answer due to copyright concerns, but actually their concern was also about guessing when they didn’t know a particular answer. Prompt engineering to give leeway worked great and I didn’t need any case law or jailbreaks.

- The models knew about as much as I expected. They don’t really have obscure details memorized. They can come up with a general recipe for a chili crisp, but do not appear to know Samin Nosrat’s specific recipe internally.

- Search can make a huge difference when it finds the right source. Across my final balanced experiment, ingredient F1 more than doubled. But that improvement was very uneven by recipe, and search introduced its own problems around source selection, attribution, cost, and formatting.

- The bounded search setup I tested could also miss information that was actually available. As one final check, I had Codex search more aggressively for one of the most difficult recipes, Goyoaga's *Oat and Honey Sourdough Hot Cross Buns*. It eventually found an exact [Eat Your Books](https://www.eatyourbooks.com/library/recipes/3456166/oat-and-honey-sourdough-hot) index entry that my experimental search had missed. It exposed several ingredients, the yield, substitutions, and preparation notes, but still not the complete formula with quantities. That changed my interpretation: the experiment demonstrated bounded retrieval failure, not that the recipe was absent from the web.

### Limitations

This was a small, deliberately selected set of recipes, with only one response per model/prompt/recipe combination. Some accuracy tables only include cases where the model attempted an answer, and different stages of the project used different prompts and model sets. Web results, provider routing, and model behavior can also change over time.

### Broader project takeaways

- I used Codex to set up the experiments and I was bothered that it kept saying things like “OpenAI was the winner” when it got back some results comparing models. I had not framed the project as a competition. I cannot tell from this experiment whether that reflects model-family bias or just a general tendency to turn comparisons into leaderboards, but it made me more cautious about accepting an LLM judge’s framing at face value.

- It’s important to iterate before scaling up. I saw that slight tweaks to the prompt made a big difference in the result. It was valuable to make sure the prompt was in a good state before running it broadly. You can work out a lot of kinks from just a few instances.

- It’s hard to grade these results deterministically with heuristic rules.

  - It’s hard to match against “2 to 3 medium ripe peaches, peeled.”
  - If a response includes extra text like “I’ll search for that specifically” before giving the list of ingredients, it gunks up the whole machinery more than I would have expected.
  - An LLM judge made this much easier. Even a simple model with a few examples could propose matches and flag ambiguous cases, though I still would not trust it without an audited rubric and some human review.

- In my final setup, Claude cost about three times as much as OpenAI and substantially more than Qwen or DeepSeek.

- When comparing across models, it is very easy to get into a messy state. For example, “model A was successful on 6/7 examples. Model B got 5/9 but that seems like an improvement over B’s past performance which was 3 of 8.” This makes it possible to fudge the numbers and the evaluator needs to truly understand what is going on to determine the results.
