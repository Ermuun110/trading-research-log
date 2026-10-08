# PREREG-FS1 — single-venue funding-settlement snipe on Binance USDT-M perps (1m bars)

Frozen 2026-10-06 before any data of this test is pulled. Third session of the day; labels `FS*` are this session's.

## Idea
When a perp's settled funding rate is extreme, the receiving side is paid |r| of notional for holding through one instant.
Hold only across that instant. The open question (memory `xvenue-funding-smallcaps`: "+0.56%/event, no price-gap, no slippage")
is whether the price move across the settlement takes the payment back. Reachable from Hong Kong (Binance / Bybit).

## Data
`data.binance.vision`, all USDT-M symbols incl. delisted, 2024-10-01 .. 2026-09-30:
monthly `fundingRate` files (settled rate, interval hours) and daily 1m klines for the event days only.

## Rule
- Event: a settlement at time T with settled rate |r| >= theta. Side = the receiver (long if r < 0, short if r > 0).
- Entry = close of a 1m bar before T, exit = close of a 1m bar after T. Binance may apply the fee within +-15 s of T, so the
  honest entry is at least 15 s early and the honest exit at least 15 s late.
- Return per event = |r| + side * (exit / entry - 1) - cost.
- Cost = 0.10% taker round trip + 0.20% spread / slippage round trip = **0.30%** (sensitivity 0.20% and 0.50%, not gated).
- Cells (12): theta in {0.3%, 0.5%, 1.0%} x entry in {T-60 s, T-0 s (optimistic, breaks the 15 s rule)} x exit in {T+60 s, T+5 min}.
  Only the four cells with entry T-60 s x theta in {0.5%, 1.0%} can be nominated; the rest are context.
- Events with a missing bar on either side are dropped and counted.

## Periods
P1 = 2024-10-01 .. 2025-09-30 nominates ONE cell (highest day-clustered t among nominable cells with n >= 100).
P2 = 2025-10-01 .. 2026-09-30 is read once on that cell.

## Gate (P2, the nominated cell; all must hold)
1. n >= 100 events on >= 40 distinct days.
2. net mean > +0.15% per event at 0.30% cost.
3. day-clustered t >= 2.5 (per-day sums).
4. median > 0.
5. top-3 days < 50% of total P&L.
6. Placebo: the same trade at settlements of the same coins with |r| < 0.05% has a gross price leg within +-0.05% of 0.
7. Still net > 0 at 0.50% cost (stress).

## What a PASS means
A candidate for the tick test only (FS2: executable bid / ask from `aggTrades` at T-15 s and T+15 s). No survivor claim, no
paper book, nothing deployed from this test. A FAIL closes the single-venue version on Binance.
