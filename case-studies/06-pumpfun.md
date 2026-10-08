# 6. Why I couldn't make pump.fun work

About 1 coin in 90 graduates. You can predict which ones fairly well, and it still doesn't make money, because by the time a coin looks like a graduate the price already says so. The people who do win are mostly in a position I can't get into. And every filter I built ran into the same trade-off: strict enough to avoid the junk meant almost no trades, and loose enough to trade meant buying the junk.

This page pulls together the pump.fun numbers from across the Solana ideas.

## The base rates

- My archive has 4.34M launched coins. 48,079 of them graduated, which is 1.107%.
- 42% of launches get no buyer at all in their first three blocks. Of those, 0.36% double in the next half hour. So a lot of coins are dead within about a second of being created.
- Buying with no filter at all (one position per coin, 14-minute hold, all costs charged) returns −25.28% a trade.
- Fees are 2.5 to 3.5% a round trip before slippage and priority fees.
- A coin that gets rugged doesn't print −100%. The curve has a floor, so it prints as roughly −80 to −90% depending on how far up the curve you bought. That confused me early on: I thought my wallet list was avoiding rugs because I never saw a −100%.

Two results told me the problem wasn't only costs. I searched 4,470 combinations of wallet ranking, entry rule and hold time, and none had a positive median. Then I repriced them with fees set to zero and fills at the mid price, and the best one still had a median of −0.28% and won 47.9% of the time. And with real costs, the share of my wallet-following trades that won never reaches 50% at any holding time from 5 seconds to 4 hours. It peaks at 45 to 47% around 4 to 5 minutes.

## You can predict graduation, and it doesn't pay

This surprised me more than anything else on this venue.

Sort entries by how much SOL is already in the curve. The bottom tenth graduates 0.09% of the time and the top tenth 43.39%. That's a 499x difference from one number you can read before buying. The top tenth was also the worst tenth to buy.

The cleanest version of this is the "ride to graduation" test. Wait until a coin's curve first holds 70 SOL (it completes at about 85), buy, and hold until it graduates.

| Curve at entry | Share that graduate | Share needed to break even | Best model's top 1% |
|---|---|---|---|
| 70 SOL | 60% | 80% | 86% |
| 75 SOL | 72% | 88% | 88% |
| 80 SOL | 87% | 95% | 94% |

The ones that don't graduate lose 76 to 81%, and the ones that do only have a little further to go, so you need to be right 80 to 95% of the time. A walk-forward model on holder concentration, flows and creator history got the hit rate up to 86 to 94% on its top picks. That is a good classifier. It still lost money in all 180 settings I tried (the best was −3.4% a trade).

The same thing happened from the wallet side. Scoring wallets by how often the coins they buy go on to graduate lifts the graduation rate from 0.9% to 40.4%, a 45x lift, and 0 of 224 settings made money. The wallets that are good at it are buying late on the curve, at a price that already includes the answer.

And with no wallet signal at all, I cut every coin's state into deciles on 12 features (volume, buyers, trade count, price against its low and so on): 120 groups, none positive. More volume and more buyers were both worse.

So I can't say it's impossible to predict which coin goes up. What I can say is that everything I could measure before buying either didn't predict the return, or predicted graduation at a price that left nothing.

## Who actually wins

There are 2,101 wallets that win consistently, taking about 14,200 SOL a day between them. I went through where it comes from.

- 58% of it is creators flipping the buy they make in their own launch. That only pays when bundled wallets buy right behind them. Without a bundle the same trade has a median of −3.8% and wins 33% of the time. I tried it myself and lost about $9 a launch.
- The rest is mostly wallets that are first in the block. Moving their entry to the worst price in the same block turns every type of winner negative (−4 to −16% a trade).
- Deployer history doesn't help either. Wallets that have never launched before graduate at 2.96% and account for 54% of all graduations (25,975 of 48,079). Repeat deployers with no earlier graduate are at 0.18%. The good operators use a fresh wallet for every launch.
- The coins that reach seven figures are often built. In one day of 135 graduates, 3 reached $1M. In one family of them a single wallet supplied 50 to 98% of all the SOL bought. In another, the same roughly 2,400 wallets traded every coin.

None of that is something a filter on public data gets me into.

## The filter trade-off

Every selection rule I built on this venue ended up in the same place.

When the rule was strict, there was nothing to trade. My strictest wallet list for the live bot (40 or more past copies per wallet) left 8 wallets. Wallet lists also go stale quickly: one rule returned +8.4% a trade with a list built that day, +4.2% with a list one week old and +0.5% at two weeks.

When I loosened the rule to get enough trades, I was buying the population again. The looser list (20 past copies) reproduced a live median of −4%. On the rebuilt wallet list from [case study 1](01-selection-lookahead.md), the entry rules lifted a group that loses 7% a trade to about zero, and no further.

And the return shape makes waiting expensive. Most trades lose a little and a few win a lot, so a long losing run is normal even when a rule works. A −$150 stop gets hit 53.9% of the time at $45 a trade with a real edge behind it.

## Conclusion

The people that benefit are insiders, who use fresh wallets, and that isnt something we can detect or filter programmatiically or mathematically. Either that or the very lucky few buyers who are in the 99.99th percentile. More than likely, I would have been drained copying all the non profitable wallets to find the few that successfully buy. 
