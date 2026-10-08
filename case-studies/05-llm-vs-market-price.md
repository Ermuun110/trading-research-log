# 5. Can an LLM beat the Polymarket price with no news?

Short version: no, at least not where anyone is trading. This is the model on its own, with no news and no web search, so it's a baseline and not a trading bot. The model is worse than the price on markets with real volume. It only looks better on markets nobody trades, at prices you can't get. The harder part was building a test that didn't leak the answers to the model.

## The idea

I wanted to try the obvious thing: have a language model read a prediction market question, estimate the probability, and bet when the market price is far from that. Size the bets with Kelly.

I used an LLM here and not a trained model because these questions are text ("will X say Y", "who wins the nomination") and there are no numeric features to train on. Where the inputs are numbers I used gradient-boosted models ([case study 4](04-what-came-closest.md), [case study 6](06-pumpfun.md)).

## Why the model gets no news

A real version of this would let the model search the news before it answers. I couldn't test that on past markets. A search run today brings back articles written after the market resolved, so the model would just read the result.

The only version I could test on history is the model by itself, on questions about things that happened after its training data ends. So the model here knows nothing about the weeks the markets were open, and the market does. That's a handicap, and I knew it going in. What I wanted to find out was how much the model knows before it reads anything, and whether that's ever enough to find a wrong price.

## Getting a fair test

The usual problem with testing an LLM on past events is that it may already know what happened. The way around that is to only use markets created after the model's knowledge cutoff.

The model was Claude Opus 5.5. Its training data ends in June 2026. That's the date Anthropic gives and I didn't measure it myself, so I left six weeks of margin. I took Polymarket events that started on or after 15 July 2026 and were due to end by 30 September. I left out sports, crypto prices, weather and similar categories where the answer is a number and not a judgement. That left 1,383 events with 16,319 markets. I kept one market per event, and only where the YES price was between 5 and 95 cents a day after opening. From 1,094 of those I sampled 1,000: 307 culture, 296 politics, 159 "will X be mentioned", 129 tech, 99 finance.

Eight separate agents each got 125 markets, with no web access and no shell. It ran in two stages.

**Stage 1, blind.** The agent sees the question, the resolution rules, the other outcomes in the event and the dates, and gives a probability. No price. Those answers were copied and hashed before anything else happened, so they couldn't be changed afterwards.

**Stage 2, with the price.** The agent then sees the market midpoint from one day after opening and chooses buy YES, buy NO or pass.

Afterwards I checked each agent's transcript for what it had opened: five file reads and two writes each, and nothing else.

For fills I was strict. A bet only counts if someone actually traded on my side at my limit price or better within the next 24 hours. Fees are included and positions are held to resolution.

All of this was written down and committed before any forecasts were read ([the file](../prereg/LLM1-llm-forecast-vs-price.md)).

## The leaks

This is the part I learned the most from. Three of the eight agents pointed out, in their own answers, that the material I'd given them was leaking information.

1. **The list of other outcomes was from today.** Say an event is "what will the number be" and has markets for different thresholds. If Polymarket added higher thresholds later on, their presence in the list tells you which way the number went. That affected 169 markets.
2. **Related markets that opened later were in the same batch.** If a follow-up market exists at all, it tells you something about how the first one went.
3. **So were their later prices**, in the stage 2 file.

I dropped every market with the first problem (169 of them) and the ones the agents had flagged for the other two. The clean set was 824 markets. I couldn't remove every case of the second and third kind. But all three leaks help the model, so a fail would still be a fail. If it had passed I'd have had to throw the result out.

These changes were made and committed before the results were read. The times are in [the prereg notes](../prereg/README.md).

## What happened

**Betting blind** (model disagrees with the midpoint by 15 points or more): 361 signals, but for 224 of them nobody ever traded at my price. Of the 137 that did fill, the average price paid was 0.346 and 32.8% won, so slightly worse than the price implied (z of −0.72). The average return was +12.6% but the median was −100%, meaning a few cheap winners were carrying it. It did beat a version with the model's answers shuffled (−19%), so the model knows something. Just not more than the price.

**Betting with the price visible:** the agents passed on 936 of 1,000 markets. On the clean set that left 55 signals. 42 of those never filled. The 13 that filled all won.

13 out of 13 sounds great, so I looked at what they were. 51 of the 55 signals were right compared to the midpoint. But the midpoint wasn't a price anyone was offering. These were brand new markets for unlikely outcomes, with empty order books, where the "price" on screen is just halfway between a very low bid and a very high ask. Where a fill did happen, the median amount that traded at my price was $44. The model had found quotes that weren't real, which is no use for trading.

**How good are the forecasts themselves?** Brier score, lower is better:

| | Market price | Model, blind |
|---|---|---|
| Markets with at least 3 trades the day before (426) | 0.144 | 0.186 |
| Markets with fewer (398) | 0.152 | 0.135 |

So the model loses clearly to a price that people are trading at, and beats a number on the screen that nobody is trading at.

I never got to Kelly sizing. With no edge at a price you can actually get, the Kelly bet is zero.

## What it cost

Eight agents and about 2.3 million tokens, for a fail. Looking at it afterwards, one batch of 125 markets showed the whole picture: the agents pass on nearly everything, and what they pick has no trades. I should have run one agent first. I do that now.

## What I took from it

Markets created after a model's cutoff are a clean way to test it, and you can reuse the idea for any model. But the test material has to be built from what existed at the decision time, and a list or batch pulled today probably isn't. Giving the model one question at a time would have avoided two of the three leaks.

A midpoint is not a price. The test has to check that someone actually traded there.

The version with live news is still untested, and this result doesn't say anything about it. It would have to be run forward in real time, and I haven't done that.

And it was the agents themselves that caught the leaks, which I didn't expect. It's worth asking for that directly: "tell me if anything in what I gave you gives the answer away."
