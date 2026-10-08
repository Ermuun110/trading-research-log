# Pre-registration — honest rolling-cohort rebuild (2026-09-17)

## Why

Every backtest in this repo selects entries with `seed_wallets_wxc.json`, the 608
wallets chosen using archive weeks 0-18. So a backtest over weeks 0-19 is scored
on wallets picked *because* of what they did in those same weeks
(`cohort-lookahead-and-ladder`). Every number produced today — wxcd +8.13%,
wxcm +8.25%, the deep-curve rule's 52.4% winrate — carries that leak.

With the entry shortfall now known to be ~0 rather than 17-24%
(`entry-shortfall-artifact`), the lookahead is the last thing standing between
these books and a real verdict. This is the test that decides the project.

## Method

For each TEST WEEK k, the cohort is rebuilt using **only weeks < k**:

- from `wa.duckdb wk_agg` (all 4.14M wallets, honest curve fills)
- present in >= 6 of weeks k-8..k-1  (durability)
- window `mean_cap` > 0 and >= 20 trades  (profitable in-window)
- traded in week k-1  (liveness — the filter `wxc-book` found takes the
  still-alive rate from 21% to 72-79%)

Entries are that cohort's first buys of each mint during week k ONLY. Nothing
about week k, or any later week, touches selection. Test weeks k = 8..18
(`wk_agg` ends at week 18), giving 11 independent out-of-sample weeks.

Pricing is the same honest twin used everywhere today: live 3s fill timing,
worst price in the landing slot, 1.25%/side, executor priority formula,
graduation via PF, 840s hold, capped +300%, one position per mint.

## Books tested (all pre-specified, no new cuts)

| book | rule |
|---|---|
| wxcd | arrival 3 + rested >= 6h |
| wxce | arrival 3 |
| rk4 | arrival 4 |
| wxcm | arrival 5 |
| DEEP | arrival >= 4 + rested >= 6h + curve > 60 SOL |

## Pre-registered bars — a book SURVIVES only if ALL hold

1. mean capped return **>= +2.0%/trade**
2. **t >= 3.0**
3. positive in **>= 8 of 11** test weeks
4. n **>= 500** entries

The DEEP book additionally must keep what made it interesting, or it is just
another right-tail book: **NET winrate > 50%** and **median > 0**.

## Pre-registered failure reading

If no book clears the bars on an honest cohort, then the positive results in this
repo are the selection leak, the wallet axis is closed for good (family 18 said
the ceiling is negative; this would say even the survivors were an artifact), and
paper trading should stop rather than continue accruing toward a verdict that
cannot come. Record that plainly. Do not re-cut the cohort recipe to find a
version that passes — one recipe, stated above, one run.
