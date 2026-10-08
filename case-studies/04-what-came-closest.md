# 4. The ones that nearly worked

Most of what I tested failed its first proper check. These didn't. Each passed an out-of-sample test and showed a return big enough to care about. I haven't traded any of them, and this page explains why.

A note on units: for the perp strategies, returns are per day on one side of the book. With $4,000 at 4x that's $8,000 a side.

| Idea | Best number I trust | What it passed | Why I didn't trade it |
|---|---|---|---|
| Long/short on meme perps, 24h hold | +229 bp a day, t 4.09 | Two separate periods, a frozen model, costs checked on live order books, paper fills checked against real trades | Loses money over 2023 to 2025 |
| Same model on all top-250 perps | +176 bp a day, t 4.43, 9 of 10 months positive | Two separate periods | All the edge is in the meme coins, so same problem |
| 60-minute reversal | +22.4 bp a trade after costs, 110 trades a day, day-clustered t of 3.04 | A holdout I hadn't touched, a shuffle placebo, capping every trade at ±20%, entering late | +6.2 bp on 2023-25 when I'd set the bar at +30 |
| Same signal, 24h hold, hedged with BTC | +51.5 bp a trade, t 5.38, positive in 2023, 2024 and 2025 | Three separate years | I found it by looking around, so it wasn't pre-registered. About $14 a day on $4k |
| Buy perps after a sharp 15-minute drop | +1.34 / +1.04 / +1.19% a trade over three periods | Three periods, entering 1 to 2 minutes late, costs of 0.40% | The 4-hour version works on 2020-22 and fades after. Live paper is negative. One crash day lost 368 points in the backtest |
| Short a delisted coin on another exchange | +22.2% per event, t 4.33, 81% win rate | Positive in 2024, 2025 and 2026 with real funding costs | Only 47 events in under three years, and one was a total loss |
| Sell the cheap side on Kalshi 15-minute markets | +0.80 cents a contract, 20 of 22 days positive | 3.23M trades, both halves of the sample | That's what other people's orders earned. Paper test of my own fills is still running |
| Same idea on Kalshi sports markets | +1.43 and +2.02 cents a contract in the two halves, t 3.98 and 7.77 | Pre-registered, 763 events, 4.72M trades, ten series | Same caveat. Paper test running |

## The meme perp model

This is the one I most wanted to be real, so I'll go through it properly.

### Where the idea came from

By late September I'd spent months on pump.fun bonding curves, where fees and slippage cost 3 to 5% a round trip. I'd just turned down a perp result worth about $35 a day as too small and wanted to get back to memecoins. It turned out the same memecoins trade as perps on Binance for 0.12 to 0.30% a round trip, you can short them, and they move around a lot more than normal altcoins.

### How it works

Take the 250 most traded perps. For each one compute 14 features from past data only (returns over different windows, volatility, funding, volume, where the price sits in its recent range, how long it's been listed) and standardise them across coins. A gradient-boosted model, retrained each month on everything up to that month, predicts each coin's return over the next 24 hours *minus the average of all coins*.

Subtracting the average matters. An earlier version without it looked good and turned out to be just long BTC and short everything else.

Go long the coins with the highest predictions and short the lowest, starting an hour after the signal, and hold for a day. Costs depend on how liquid the coin is, and funding is charged on both sides.

### Why I believed it

The edge got bigger as the coins got more volatile, which is what you'd expect if it's real:

| Coins | How much they spread out per day | Return on the second period | t |
|---|---|---|---|
| Least volatile third | 2.9% | −67.0 bp a day | −3.05 |
| Middle third | 4.4% | −64.0 bp a day | −1.53 |
| All 250 | 7.3% | +158.3 bp a day | 3.75 |
| Most volatile third (memes) | 10.6% | +350.3 bp a day | 3.96 |

(The version I actually ran takes a wider slice of the meme group, 20% on each side. That's the +229 number.)

It also held up on the things I knew to check by then:

- It worked on a first period and then on a second one. For the all-coins version the second period was 140 days, with 9 of 10 months positive and only 10% of the profit coming from the best three days.
- A model trained once on the first period did slightly better on the second than one retrained every month (+237 against +218 bp a day), so it wasn't relying on constant refitting.
- I walked through 84 live order books at $800 per coin to check costs. It came to 18.45 bp a round trip, against the 18 bp the backtest was charging.
- I compared 125 paper fills with real trades on Binance at the same moments. Real traders had paid 0.8 bp less than my paper model assumed.
- I found a bug that would have hurt. The exported model only had 10 trees, because scikit-learn had quietly switched on early stopping. With 300 trees it badly overfit (+87.8 bp). Anywhere from 30 to 120 was about the same, so I fixed it at 60.

### What killed it

Everything above was from one year of data. So I pulled 2022-11 to 2025-08 for all 864 symbols, and wrote down the pass mark before running it.

The frozen model made −7.7 bp a day (t −0.82). By year that's −7.2 in 2023, −16.9 in 2024 and +5.5 for January to August 2025. Retrained monthly it made −29.5 (t −3.0). I ran the same code on the original year to make sure I hadn't broken something, and it still gave +200. The code was fine. The earlier years are just different.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../docs/img/era-curve-dark.svg">
  <img src="../docs/img/era-curve-light.svg" alt="Cumulative return of the meme perp long/short model from April 2023 to August 2026" width="880">
</picture>

The chart is the monthly-retrained version on one continuous dataset (60 trees, and training data is cut off so that nothing overlaps the month being tested). Every point is out of sample. The series is in [`data/meme_tier_walkforward_daily.csv`](../data/meme_tier_walkforward_daily.csv) and [`research/era_metrics.py`](../research/era_metrics.py) prints this table from it:

| Period | Days | bp a day | t | Sharpe | Max drawdown | Days positive |
|---|---|---|---|---|---|---|
| 2023 | 275 | −19.1 | −1.47 | −1.69 | 63% | 46.2% |
| 2024 | 366 | −24.1 | −1.86 | −1.86 | 125% | 48.1% |
| 2025 | 365 | −20.7 | −0.87 | −0.87 | 83% | 49.6% |
| 2026 | 242 | +160.2 | +4.11 | +5.05 | 29% | 58.7% |
| Apr 2023 to Aug 2025 | 884 | −20.6 | −2.15 | −1.38 | 210% | 48.1% |
| All | 1,248 | +13.7 | +1.20 | +0.65 | 227% | 50.2% |

Even within the year I'd built it on, the money comes late. September 2025 to January 2026 loses 22 bp a day. All of the profit is from February 2026 onwards (+184 bp a day over 211 days).

While doing this I also found my funding data was missing 62.8% of its values for the original year. With complete data the frozen model makes +141 bp a day there, not +200.

Nearly all the profit is on the short side, and 2025-26 was a bad year for meme perps. So what I have is a bet that meme perps keep behaving the way they did in 2026. It might keep working. I can't tell from this data.

I ran it on paper for twelve days (+153 bp a day, t 1.69) and then shut down the server it was on to save money. Twelve days doesn't tell me anything either way.

## Why I walked away from these

Two reasons, and I only think one of them was a good one.

The good reason is the evidence. Three of the perp strategies only work in one period. The one version that's positive every year is something I spotted while looking at other results, which is the kind of finding I've learned not to trust until it's tested properly.

The bad reason is size. In their good years these make about $15 to $35 a day on $4,000. I'd set out to make a few hundred a day, so I kept moving on to the next thing. I think that was the wrong call. If something small holds up every year, you can scale it with more capital or leverage. A memecoin trade that works at a few dollars a time stays that size forever.

If I picked this up again, the first thing I'd do is pre-register the 24-hour hedged reversal and run it forward.

## What I do differently

Anything built on 2025-26 perp data gets run on 2023-25 before I call it a survivor. Model settings that go live are fixed by hand, so that a library default can't choose them for me. And I write down what a result is worth per day at my size, but I no longer use that as a reason to stop looking at it.
