# Six backtest mistakes I caught

A coding agent can write and run a backtest in a couple of minutes, so it's easy to end up with one that looks like a winner and isn't. These are the six mistakes I caught in my own results, roughly in the order they cost me the most, and the check I use for each one now.

Where there's a check in code I've pointed to it. The functions are in [`audit/`](audit) and the simulated versions are in [`evals/`](evals).

## 1. I picked the sample using the answer

My main strategy followed 608 wallets. Those wallets had been chosen using 19 weeks of data, and then the strategy was backtested on those same 19 weeks. So it was being scored on wallets that were picked because they'd done well in exactly that period.

When I rebuilt the list properly, using only earlier weeks for each test week, the result went from +8.13% a trade to −0.73%. I had real money on it at the time.

I made the same kind of mistake twice more on Polymarket. Once a wallet ranking leaked which side the wallet ended up on. Another time I filtered sports markets by total volume, which sounds harmless, but total volume includes trading during the game, and filtering on it ended up selecting upsets. That made favourites look 4 to 10 cents overpriced when they weren't.

It also happened with an LLM. When I gave a model batches of Polymarket questions to forecast, the batches themselves leaked the answers. That one is in [case study 5](case-studies/05-llm-vs-market-price.md).

Now, for anything that selects wallets, coins or markets, I ask whether it could have been computed at the moment of the trade. `audit.leakage.check_no_lookahead` and `rolling_top` do this for the simple case. In the simulated version (`lookahead`), wallets with no skill at all pass a normal backtest 99% of the time.

## 2. It found a winner in a big search

For one wallet-copy idea we ran a grid of 4,752 settings and took the best five. All five passed a second period at +3 to +9% a trade, which looked like confirmation. On the first data none of them had seen, the main one made −8.0% over 97 trades. The same thing happened with three models that picked coins at launch: +4 to +10% in research, and all three failed the holdout week.

If you test 4,752 things that do nothing, the best of them will show a t-stat of about 3.6 just by luck (`audit.stats.median_best_t`). To trust the winner it would need about 4.25 (`sidak_t`). I didn't know those numbers at the time and I should have.

Now the rule and the pass mark get written down before the test, and if a number came out of a search I write the size of the search next to it.

## 3. It booked fills I couldn't have got

The first paper book ran 236 trades before I looked hard at how it was filling them. It was missing four costs: priority fees, failed transactions, the delay between deciding and landing, and worst of all it was pricing exits against bonding curves that had already closed. You can't sell into those. 79% of the book's profit came from that.

Later a different signal showed +5.9% a trade. Pump.fun data doesn't record the order of trades inside a block, and my code was grabbing whichever row the database returned first. Once I rebuilt the real order the result was +0.82%. I only found it because a second version of the evaluator gave different numbers from the first. Details in [case study 3](case-studies/03-intra-slot-order.md), code in `audit.order.chain_slot`.

Now every cost gets charged before a paper book takes its first trade, entries fill at the worst price in the block they'd land in, and whenever there's a new version of an evaluator it gets run against the old one on the same trades.

## 4. It read the same holdout more than once

When a holdout fails, the natural thing is to tweak the rule and try the same week again. One strategy family went through the same holdout week three times before it got marked as used. On a different idea, some of the variants were chosen after looking at a slice of data I'd set aside for testing.

A holdout you've looked at three times is training data. Now each one gets a single read per strategy family and is then written down as spent, with its dates. `audit.leakage.HoldoutLedger` is that idea as code: it keeps a file of what's been read and throws an error on a second read.

## 5. It timed itself with its own clock

The bot reported that it was getting orders in within one second of the signal. That was measured from when its own websocket message arrived to when it made its decision, so it was only measuring my code. The real delay has to come from the chain, by matching the signal wallet's transactions against the coin's.

Later I spent a while trying to get orders in faster because some position-in-queue stats suggested it mattered. A randomized test (half the trades with a higher fee) showed it got me in about 70 ms earlier and made no difference to profit.

I don't have code for this one. It needs chain data and live trades, and I haven't worked out how to turn it into a unit test.

## 6. It used a t-stat on the wrong thing

Trades on the same day aren't independent. In one backtest a single crash day had 25 positions open at once and they all lost about 15%. If you count those as 25 separate observations your t-stat is far too high. The fix is to add up each day first and take the t-stat of the daily totals (`audit.stats.clustered_tstat`). In the simulation, a strategy with zero edge passes the per-trade version 26% of the time and the daily version 4%.

Two related things. Several strategies had a positive average and a negative median, meaning a handful of big wins were carrying everything, so now I always print the median and how much of the profit came from the best three days. And for strategies that sell cheap contracts (win 2 cents most of the time, lose 98 occasionally), a t-stat on dollars is useless: sell 100 fairly priced 2-cent contracts and 13% of the time you'll see no losses at all and an infinite t-stat. For those I test the number of losses against what the price implies (`lottery_pvalue`).

## What none of this fixes

I ran 115 pre-registered tests. With a pass mark around t = 2, about 2.6 of those would pass by pure chance even if nothing worked. So one pass doesn't mean much on its own. In practice a pass just earned the idea another test: a holdout, an older period, or real fills. So far everything that passed once has either failed the next test or is still waiting on live data.

## The rules as they're written

These are copied from the instructions file the agent reads at the start of each session:

> **Charge every real cost before a book's FIRST trade.**
>
> **A paper exit must be a fill you could have taken.** A completed pump.fun curve is zeroed and locked; pricing the exit at the last pre-migration reserves books a sale that could not happen.
>
> **Never report a latency measured off your own observation clock.**
>
> **Any -100% / no-route booking is a claim** — re-quote live before it enters a verdict.
>
> **Kill bars are pre-registered and derived from the return distribution.** A dead sub-book takes no new entries and is never revived mid-drawdown.
>
> **A confirmation timeout is UNKNOWN, not failure.** Treating it as failure and retrying double-buys.
>
> **A cap that lives in memory is not a cap** — a crash loop resets it.
