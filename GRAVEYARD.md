# Graveyard

This is a table of what I tested and how each idea died. It's not all 71, just the ones where I have clean numbers. Returns are per trade after costs unless it says otherwise.

The last column:

- **FAIL**: didn't meet the pass mark I'd written down beforehand
- **ARTIFACT**: the result came from a bug or a mistake in my method
- **ERA**: worked in one period and not in another
- **PARKED**: passed what I tested it on, but I never proved it or traded it
- **OPEN**: still running on paper

## Solana memecoins (pump.fun bonding curves and graduated pools)

| Rule | Looked like | Deciding test | Status |
|---|---|---|---|
| Follow a fixed cohort of 608 "durable" wallets; buy when the 3rd one enters a coin | +8.13% | Wallet list rebuilt from prior weeks only: −0.73%, t −0.78, positive in 5 of 11 weeks (89,262 entries) | **ARTIFACT** selection lookahead |
| Same, real money | paper positive | 296 round trips, −0.0063 SOL | **FAIL** |
| Filter coins by features that predict graduation | top decile graduates 43% of the time, bottom decile 0.09% | That top decile returns −0.13% | **FAIL** predictable and priced |
| Coin-state features at entry | | 120 deciles, 0 positive | **FAIL** |
| GBM on 32 features when a coin first crosses 70 SOL | +9.1%, t 4.6, median +41% | Untouched week, frozen model: −12.1% (n = 141) and −8.3% (n = 128) | **FAIL** |
| Confluence: second "followable" wallet buys within 600 s | +5.9%, holdout +18% | Exact order inside each block: +0.82% (n = 764, day-t 0.50) | **ARTIFACT** tie-breaking |
| Decide at launch with a GBM, land two blocks later | +4 to +10%, day-t 3 to 7 | Holdout day-t 0.0 / 1.41 / −0.55 | **FAIL** |
| Rank every wallet by how well it copies at 2 blocks late | 4 of 5 frozen configs positive on the holdout, placebo −10 to −27% | Pre-registered pick: holdout −4.1% | **FAIL** by its own rule |
| Slow wallet copy chosen for money per day (4,752-config grid) | 5 of 5 finalists pass, +3 to +9% | First unseen tape: headline −8.0% (n = 97). Lists go stale in about a week | **FAIL** |
| First-copier: buy right after a followed wallet's first buy, raw block feed, real money | positive median in replay | All live profit from one operator's bot; the other 591 trades averaged 0.0% (to 1 Oct). Trades net +0.054 SOL over 1,392 round trips; wallet −0.254 SOL after 836 latency test buys | **FAIL** |
| Follow the 2,101 wallets that win consistently (+14.2k SOL a day between them) | winners persist week to week | From a follower's seat: −11.3% | **FAIL** the edge is the seat |
| Keep only wallets with real own profit that is not their own buying | +8.3% on selection period | Confirmation: sum-t 1.03, three days carry it, 1 of 5 configs positive | **FAIL** |
| Buy every graduation pool at the open | | −10 to −17% | **FAIL** |
| Graduation pool with 5 to 30 SOL inflow in first 20 s | median +38%, win 60% | n = 150, mean −6.90% | **FAIL** small wins, large collapses |

## Crypto perpetuals

| Rule | Looked like | Deciding test | Status |
|---|---|---|---|
| Cross-sectional model, long/short the meme tier of Binance perps, 24 h hold | +229 bp a day, t 4.09 | Frozen model on 2023-01 to 2025-08: −7.7 bp a day, t −0.82 | **ERA** one bear year |
| Same model on all top-250 perps | +176 bp a day, t 4.43 | Edge sits entirely in the meme tier; same era test | **ERA** |
| 60-minute cross-sectional reversal, top 1% of signals | +22.4 bp a trade net, 110 trades a day, day-t 3.04 on an untouched holdout | 2023-01 to 2025-08: +6.2 bp against a +30 bar | **ERA** |
| Same signal, 24 h hold, BTC-hedged | +51.5 bp a trade, day-t 5.38, positive in 2023, 2024 and 2025 | Not pre-registered. About $14 a day on $4k | **PARKED** |
| Flush reversion: long a perp after a 15-minute drop of 5% on 3x volume | +1.34 / +1.04 / +1.19% across three periods | 240-minute version passes 2020-22, fades 2023-25 (2025: −0.45%); live paper negative | **ERA** |
| Short a coin on another venue after a Binance delisting notice | +22.2% per event, t 4.33, n = 47, positive every year | 47 events in under three years, one −100% | **PARKED** |
| Short new perp listings for 14 days | +7.01%, t 3.9 | The loss had been capped at −100% at exit. Honest isolated margin: +2.51%, t 1.2 | **ARTIFACT** |
| Funding-settlement snipe on extreme funding | | Price hands back 93 to 124% of the payment within half a second. 12 of 12 cells negative | **FAIL** |
| Follow large public TWAP orders on Hyperliquid | gross drift +0.13% | 7,282 orders: −0.07 to −0.27% in all 12 cells; the drift equals the placebo | **FAIL** |
| Move the reversal book to a zero-fee venue | | Only 66 of 528 coins listed there: −25.0 bp, day-t −1.85 | **FAIL** the spread replaces the fee |
| Time-series trend following on 609 perps | | No edge | **FAIL** |
| Technical-indicator scan, high-frequency order-book signals and market making on Hyperliquid | | Each failed its pre-registered bar | **FAIL** |

## Arbitrage

Arbitrage is what I wanted to do first. Most of these found a real gap that was smaller than what it costs me to trade it. Two were gaps that disappeared once I used live quotes.

| Rule | Looked like | Deciding test | Status |
|---|---|---|---|
| Funding-rate dislocations between venues | +0.383% a trade, t 7.82, out of sample | Walked the real order books: 0.838% cost at $3k a leg against 0.603% gross | **FAIL** negative at every size |
| Static funding carry, short Hyperliquid perp against long Binance perp | positive out of sample in 27 of 28 pairs | +4.55% a year. Real, and too small to matter on my capital | **PARKED** |
| Price gaps on meme perps between Binance, Bybit and Hyperliquid | | 34 hours of live quotes: gross +2.1 bp against 23.5 bp for four taker fees, so −21.4 bp a trade. Resting orders did worse (−22.8 bp) | **FAIL** |
| Lead-lag on the same quotes (Binance moves about 200 ms before Hyperliquid) | +12.8 bp using the time I received the quote | Hyperliquid quotes reached me 283 ms late. On the venue's own clock: −16.1 bp. 0 of 18 cells positive | **ARTIFACT** stale quotes |
| Tokenised stocks on Solana against the same stock on Bybit | | 715 two-way executable quotes: none above +10 bp after fees, best −5.3 bp. Prices sit within about 2 bp | **FAIL** |
| Polymarket strike ladders priced out of order | 3,672 "riskless" violations of 2 cents or more | They were last trades in thin markets. A live book on a busy ladder had no crossed pairs | **ARTIFACT** stale prints |

## Prediction markets

| Rule | Looked like | Deciding test | Status |
|---|---|---|---|
| Polymarket: follow wallets ranked on 180 days of history (404.5M fills) | +31 to +35% ROI at the wallet's own price, out of sample | Same side 60 s later costs 8 cents more: −0.9 to −2.4% | **FAIL** |
| Polymarket: rest NO-side orders in non-sports markets | about +6% on stake in 2024-25 | Fresh 2026 pull, 56.3M prints: −0.01% | **ERA** competed away |
| Polymarket: buy pre-game favourites at 0.90 to 0.95 | win about 1.2 cents more than the mid | +0.35 cents after half a spread and the fee, z 0.47 (34,054 games) | **FAIL** |
| Polymarket: copy the top monthly-profit wallets | | 14,277 first buys: win rate 0.548 at price 0.546, ROI −0.96% | **FAIL** |
| LLM probability with no news against the market price, 1,000 markets created after the model's knowledge cutoff | | Blind arm z −0.72. Market Brier 0.144, model 0.186 | **FAIL** |
| Polymarket liquidity-reward quoting, real money | modelled reward | First reading paid about a quarter of the model; −$65.29 on $419 | **FAIL** adverse selection |
| Kalshi 15-minute markets: rest orders selling the side priced at 5 cents or less | +0.80 cents a contract, 20 of 22 days positive (5,060 trades, 88 losses) | Own fills unknown. Forward paper book running, gate not yet read | **OPEN** |
| Kalshi same markets as a taker | | 0 of 168 cells after the 7% fee | **FAIL** |

## What they have in common

Going back through the table, most of these died in one of five ways.

The thing that predicted the outcome was already in the price. Coins about to graduate, sports favourites, long shots: you can predict all of them fine, and you still can't make money buying them.

The edge belonged to whoever was first. The winners on pump.fun and on Polymarket are winning because of where they are in the queue, and I couldn't get there by following them.

The gap was smaller than my costs. Every arbitrage I looked at was like this: the gap is there, and it belongs to whoever pays the lowest fees and has the fastest link.

It only worked in one period. Three perp strategies and one market-making one were really bets on a particular year.

Or my backtest filled an order that couldn't have been filled: a closed bonding curve, a random row in a block, a loss capped at −100% when the real position would have lost more.
