# 7. Low-latency copy trading on Solana (ongoing)

**Status:** ongoing. Pass mark not yet met. Next step: a ShredStream feed.
**Period covered:** 11 to 14 October 2026 (family 78).

## 1. Summary

This project tests whether a small account can profit by copying well-known pump.fun traders fast enough to land directly behind them in the same block, ahead of the wave of copy bots that follows each of their buys.

The effect is real: the first seats behind a followed trader earn +6% to +15% a trade on held-out data, and later seats earn nothing or lose. Over four days I reduced the time between the trader's buy and mine from about 80 ms to 36 ms. The remaining gap is set by how the validators build blocks (20 ms auction rounds), not by my own system, which now accounts for about 0.2 ms of it. Real-money results so far are small and negative, and the pre-registered pass mark has not been met.

The work is ongoing. The one lever left is seeing the trader's transaction earlier than the public feed shows it, and the next step is to test that with ShredStream.

## 2. Hypothesis

Traders at the top of public leaderboards have thousands of followers, many of them running copy bots. When one of them buys, those bots react within milliseconds and push the price up inside the same block. A copy that lands at seat 1 to 3 of that wave buys before most of the demand arrives and should be able to sell into it.

## 3. Evidence that the effect exists

Measured on six days of raw block data before any trading:

| Finding | Value |
|---|---|
| Buyers in the same block after a followed trader's buy (median) | 3 buyers, 2.5 SOL (random buy of the same size: 1 buyer, 0.23 SOL) |
| Price move by the end of that block | +9.3% |
| Share of first followers in the trader's own Jito bundle | 5% (the rest react to his buy) |
| Trader buying his own coin | 1.5 to 4% of buys |

Value of each seat, for 52 traders selected on three days and tested on the following three:

| Seat behind the trader | Return per trade |
|---|---|
| 1 | +15.5% |
| 2 | +6.0% |
| 3 | +1.9% |
| 4 | 0.0% |
| Worst seat of the next block | −7.1% |

Most of the profit in the wave goes to three or four fast wallets trading 3 to 4 SOL a buy; one earned +344 SOL in 5.6 days. Small bots at seat 4 or later earn approximately nothing.

**Risk control adopted early.** Every buy carries a price cap of +10% over the price the trader's buy left. A late copy then fails instead of filling at the top, which improves the worst case from −7.1% to −1.05% per signal.

## 4. Method: measuring latency correctly

My first latency figures converted a transaction's position in a block into milliseconds. This proved invalid, because a large part of each block is laid down together at the start of the slot. All figures below use a single clock: the time a transaction's data arrives on my own server from a raw block (shred) feed.

## 5. Latency reduction

| Change | Landing behind the copied buy (median) |
|---|---|
| Initial live run, server in Frankfurt | 64 to 83 ms (about seat 6) |
| First code fixes, 60 test buys | 69 ms (9% within 30 ms) |
| Server moved to Amsterdam, next to the validators' ingress nodes | 40 ms |
| Persistent direct QUIC connection to the leader | 36 ms |
| Signal-to-signed-buy path rewritten as one Rust thread, receive thread pinned to a dedicated CPU, missing block data rebuilt from erasure codes | 37 ms (no further change) |

My own processing time fell from about 2 ms to about 0.2 ms. Those improvements were real and measured individually, but they stopped affecting the landing time at around 36 to 40 ms.

**Why it plateaued.** The validators I can reach fastest run Jito's BAM client, which builds blocks in 20 ms auction rounds, ordered by fee inside each round. When the trader's buy lands in round *k*, mine lands in round *k*+2 on most sends. Reaching round *k*+1 requires seeing his transaction roughly 5 to 10 ms earlier than the public feed delivers it. Nothing on my server can provide that; the rest of the delay is inside the leader's own pipeline.

## 6. Levers tested and rejected

| Lever | Result |
|---|---|
| 0.01 SOL tips through a landing service | No faster on BAM leaders, about 90 ms slower on others. Cost 0.115 SOL |
| 7x higher priority fee (76 test buys) | Round *k*+1 on 6% of the expensive arm against 18% of the cheap arm. The fee only orders buys inside a round already reached |
| Several signed copies of one buy (one durable nonce, losers dropped at no cost) | Median gain 0.0 ms over a single direct send |
| Following the late part of the wave (45 to 400 ms after the trader) | Zero net on 337 signals |
| Same, restricted to wallets with a good priced record | +2.9% per signal in-sample; −0.20% on 798 out-of-sample signals. The in-sample result came from one operator in one hour |
| Predicting his coin from its creator wallet and buying first | Pre-registered on 1,000 launches: −16.2% per launch. Hit rate 8.3% against 21% needed |

## 7. Where the profit in the wave goes

- 63 wallets reach round *k*+1 on at least 80% of the buys they copy. Within that round, order is purchased with fees, and the wallets at the front lose money per fill (−6.7% on 305 SOL across 192 fills, measured on chain).
- The profit in the wave goes mainly to the trader's own additional wallets, which land in his round with no delay. That position is not available to an outside copier at any speed.
- With perfect knowledge of his coin, buying one block before him and selling one block after returns +38% per trade across 185 of his real coins. Buying at the copy seat (the end of his block) returns about 0%. The edge is one block wide.

## 8. Real-money results

All trading used a separate small wallet, funded with 0.19 SOL in total; about 0.15 SOL has been spent.

| Activity | Result |
|---|---|
| 7 hours of live copying at 0.01 SOL per buy | 69 sends, 8 fills, −0.0497 SOL. 93% of the loss was priority fees on buys that failed the price cap. Trades before fees: +3.8% of turnover (n = 8) |
| Tip test | 0.115 SOL, no improvement |
| Test buys used to measure landing time | Remainder of the spend |

## 9. Current status and next steps

**Pass mark (set before going live):** a median landing of 30 ms or less behind the trader, and at least 30% of buys filling within the +10% cap. Current: 36 to 40 ms, and roughly 1 fill in 5. Not met.

**Next step: ShredStream.** The remaining lever is an earlier view of the trader's transaction, which a dedicated shred feed may provide. I will test this with a ShredStream trial before committing to any paid feed, using a timer that races the new feed against my current one on the same followed transactions. The bar is set in advance: a lead of 20 ms or more on followed transactions justifies continuing; under 10 ms closes this route. The expected gain is a prediction and has not been measured, and the test may come back empty.

Until the pass mark is met, position size stays at the minimum and no paid feed is purchased. Two pre-registered reads on the late-wave variant are also due.

## 10. Lessons so far

The result is consistent with the rest of my pump.fun work ([case study 6](06-pumpfun.md)) and with wallet following ([case study 2](02-wallet-identity.md)): the profit belongs to whoever is first, and in this case that is largely the trader and his own wallets. Reducing latency from about 80 ms to 36 ms was worthwhile engineering and showed precisely where the remaining delay sits. Whether an earlier data feed can close the last 10 to 15 ms is the open question this project is now testing.
