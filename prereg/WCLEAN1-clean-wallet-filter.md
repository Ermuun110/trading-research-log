# PREREG-WCLEAN1 (2026-10-07, written BEFORE any filtered number is computed) — family 71: "clean" wallets for the slow copy rule

User, 2026-10-07: "keep looking at wallets, on how to filter them, when to follow them, good pnls (not inflated by their own
buys)" and "understand why it failed, and find ways to work around it".

## What failed, and the hypothesis
Family 41b (slow wallet copy: wallet's first >= 0.1 SOL buy of a coin, copy lands 2 slots later, sell after 300 s; speed does not
matter, 1 vs 3 slots <= 0.3 pp) passed P2 at +3..+9% a trade and died on list AGE: +8.4% with a list built today, +4.2% one week
old, +0.5% two weeks old. Known from the live copier: the best-scoring wallets are often operators (one operator = 10 of 16 "good"
wallets; ladder bots whose own later buys lift the price) and they rotate wallets within days.

**H:** the decay with list age comes from wallets whose copy score is made by their own buying (ladders, dominant buyer of the
coin) or who lose money themselves. Wallets with a real own profit and no self-pumping keep their copy edge when the list is old.

## Data (all on disk, no new pull)
`data/work/launch/launch.duckdb` (`ev`, `sl`), copy events and returns `data/work/launch/we` (46.7M events, exact in-slot order,
entry = worst state in slot buy+2, exit r9 = time 300 s, per-coin fee, impact at 0.2 SOL). P1 = 2026-05-01..06-30, P2 = 07-01..08-25.

## Per-event wallet facts (the wallet's own trades in that coin from its first >= 0.1 SOL buy on, first 2 h of the coin)
- `cash` = sells x (1 - 0.0176) - buys x (1 + 0.0176), SOL. Unsold tokens count as 0.
- `ladder` = 1 if the wallet buys the same coin again within 300 s of its first buy.
- `dom` = 1 if the wallet's own buys in [first buy, +300 s] are >= 50% of ALL buy SOL of the coin in that window.

## Wallet filters (28-day window, same causal rule as the score; an event counts from the day after its buy time + 2 h)
- **C1 real profit:** sum of `cash` over the window > 0.
- **C2 no ladder:** share of events with `ladder` <= 0.20.
- **C3 not the dominant buyer:** share of events with `dom` <= 0.20.
- **C4 clean:** C1 and C2 and C3. **X = not C4** (reported, the "inflated" side).
No other thresholds are tried. The filters are applied ON TOP of the five frozen 41b configs (`frozen_W11.json`), unchanged.

## Read
Table: 5 configs x list age L in {0, 7, 14, 24} days x filter {none, C1, C2, C3, C4, X} x {P1, P2}: n/day, mean, median, daily-sum t.
1. **Pick on P1 only:** F* = the filter among C1..C4 with the highest daily-sum t of the headline config (t>=2, c2, sb>=.5) at
   L = 24, with >= 5 trades/day.
2. **Confirm on P2 at L = 24, headline config with F\*:** mean >= +2% a trade AND daily-sum t >= 2.5 AND top-3-day share of P&L
   < 50% AND n >= 300 AND at least 4 of 5 configs with mean > 0 under F* AND F* beats the unfiltered headline at L = 24 on mean.
3. **Only if 2 passes:** one read on the pump tape 2026-09-26 06:48 -> 09-30 end (never used by 41b), lists frozen on data through
   Sep 1 (24-28 days old), fills as the PREREG11 addendum plus an entry 6 slots late (tollbooth speed). Bars: n >= 200, mean >=
   +2%, coin-bootstrap 5th percentile > 0, >= 3 of 5 configs > 0, both fills. If 2 fails the tape is NOT read.
A pass at 3 is a CANDIDATE for forward paper, not a money result. A fail at 2 closes the filter idea on this venue.

## Not allowed after seeing numbers
Changing thresholds (0, 0.20, 0.50, 300 s), the window, the configs, the exit, or picking F* on P2.
