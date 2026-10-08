# PREREG-LLM1 (family 68; 67 was taken by PREREG-NOQ1 in the same hour) — does an LLM's probability find mispriced Polymarket markets?

Frozen 2026-10-07 before any price or outcome of the universe has been read. Seen so far: the event listing (titles, tags, dates,
market counts, comment counts). `llm1_pull.py` stores `outcomePrices` in `data/work/llm1/` but prints none of it.

User's idea: "sentiment analysis, identify misplaced bets, Kelly sizing". Kelly is a sizing rule and needs an edge first; the test is
whether a language model's probability carries information the price does not, at a fill a taker could have had.

## Why this can be tested honestly now
The forecasting model's knowledge ends in 2026-06. Every market below was created on or after 2026-07-15, so the model cannot know
an outcome. It gets no web, no price (stage 1) and no file except its own question pack.
What this does NOT test: a model fed live news. That cannot be backtested (search leaks the future); it is forward paper only.

## Universe (frozen)
- gamma `/events`, `closed=true`, event start >= 2026-07-15, scheduled end 2026-07-16 .. 2026-09-30.
- Event dropped if it carries any tag of: Sports (1), Crypto (21), Hide From New (102169), Weather (84), Up or Down (102127),
  Multi Strikes (102516), Hit Price (102134), Tweet Markets (972). These are price / count-state markets (dead families 24, 57, 58,
  the ladders, the weather bot) where a model without a live feed knows nothing. 1,383 events / 16,319 markets remain.
- Market eligible if: outcomes are [Yes, No]; market start >= 2026-07-15; t0 = market start + 24 h; scheduled end >= t0 + 24 h;
  the CLOB midpoint of the YES token at t0 (last 1-minute point in the 6 h up to t0) is in [0.05, 0.95].
- **One market per event**, drawn with `random.Random(67)` among the eligible ones; then 1,000 events drawn with the same generator
  (all of them if fewer). No volume field is used anywhere (FLB1: total volume selects upsets).
- Markets not resolved to 1 / 0 (or 0.5 / 0.5 = void, kept at payoff 0.5) are dropped and counted, after the forecasts are in.

## Forecasts
- 8 forecasting agents (the session's model), ~125 markets each. Tools allowed: Read on the pack, Write of the answer file. Any web
  or shell use voids the agent's pack (transcripts are checked).
- **Stage 1 (blind):** pack = event title, question, resolution text (<= 900 chars), the names of the event's other outcomes,
  market start and scheduled end. Output: P(YES) per market, and a flag if the model believes it knows the outcome.
- **Stage 2 (screener), sent only after the stage-1 file is written:** the midpoint at t0 per market. Output: action YES / NO / PASS
  and a revised probability. The agent is told the taker cost and to act only where it believes the price is wrong by >= 10 points.

## Trade rules (taker, held to resolution)
- **Arm B (blind):** side = YES if p1 - mid0 >= 0.15, NO if mid0 - p1 >= 0.15. Limit = (model probability of that side) - 0.10.
- **Arm S (screener):** side = the stage-2 action. Limit = (stage-2 probability of that side) - 0.05.
- Fill = the first taker BUY print of that side's token in (t0 + 60 s, t0 + 24 h] at a price <= the limit and in [0.05, 0.95], at
  that print's own price (`data-api /trades`). No such print = no trade (rate reported).
- Fee per share = rate * p * (1 - p): the market's own `feeSchedule.rate`, or 0.05 where the market had none.
- P&L per share = payoff - p - fee. ROI = P&L / (p + fee). Equal stake per position.

## Statistics and gate (each arm read once)
- mean ROI; t clustered by scheduled end day and by t0 day; z = sum(payoff - p - fee) / sqrt(sum p (1 - p)).
- Placebo: the model's probabilities permuted across markets, 2,000 draws, same rule.
- **PASS:** n >= 150 positions, mean ROI >= +5.0% net, both t >= 2.5, z >= 2.5, positive in both halves by t0, top-3 end days < 50%
  of the P&L, observed mean ROI above the 99th percentile of the placebo.
- Reported, not gated: Brier score of p1 and of mid0; logistic fit outcome ~ logit(mid0) + logit(p1) with an event bootstrap;
  Arm B at a 0.25 threshold; split by tag group (politics / elections, mentions, culture, tech, finance) and by YES / NO side;
  how often the stage-1 "I know this" flag fired.
- **PASS = candidate only.** Next step would be a forward paper book with live news on the separate VM (needs an API key: the user's
  decision). Sizing registered for that stage: stake fraction = 0.25 * (p_hat - c) / (1 - c), c = price + fee,
  p_hat = price + w * (model - price) with w from the logistic fit, capped at 2% of equity per market.
- FAIL = one line in the table; no threshold, tag or side is re-picked on this sample.

## Clarifications before any forecast or tape (2026-10-07; no outcome and no sampled price shown on screen)
1. Family number is 68 (67 was taken by PREREG-NOQ1 in the same hour).
2. Counts: 12,926 time-eligible markets, 10,070 with a midpoint at t0, 7,830 in 0.05-0.95, on 1,094 events; 1,000 events sampled
   (culture 307, politics 296, mentions 159, tech 129, finance 99, other 10). Packs are four text files per agent.
3. The stage-1 prompt tells every agent one selection fact, the same for all markets: "one day after it opened the market traded
   somewhere between 5c and 95c". A real screener sees that too, and without it a model would call every candidate of a 28-way
   race a long shot and the blind arm would be a NO-on-everything rule.
4. Tapes: a market whose tape cannot be paged back to t0 - 24 h is dropped and counted (`llm1_tape.py`).
5. Polymarket's own comment threads were considered as a sentiment input: 154 of the 1,383 events have any comment. Not used.

## Amendment before the read (2026-10-07; all 1,000 stage-1 answers frozen and hashed, no outcome or result printed yet)
Two forecasters reported a look-ahead in the packs themselves (my design error, found by them, not by me):
- **Leak A, same event.** "Other outcomes listed in the same event" was taken from the event as it stands today, so it includes
  strikes that were added after t0 (a new lower strike tells the reader the number went down). Mechanical rule: a sampled market
  is contaminated if any other market of its event was created after its t0 (or has no start date). 169 of 1,000.
- **Leak B, same pack.** A forecaster reads 125 questions opened over ten weeks; a later-opened related market (the "higher
  strikes" follow-up, next week's edition of a recurring market) tells it how an earlier one developed. Six ids were reported
  (Q0511, Q0895, Q0231, Q0653, Q0725, Q0957). This cannot be removed mechanically.
- **Rule for the read:** the gated sample is the 831 markets without leak A, minus the reported ids. The contaminated markets are
  printed separately, not gated. Both leaks help the model, never the price. So a **FAIL stands as it is**; a **PASS would be void**
  until re-run on clean packs (one question per call, outcome list as of t0), and would be reported as "not a result".
- Stage-2 action counts seen so far (five packs): 1-2 YES, 2-12 NO, 113-122 PASS each. Arm S will therefore have far fewer than
  the 150 positions its gate needs; it is read as registered and cannot pass on n. Nothing else about the answers has been looked at.
- Tool audit of the stage-1 transcripts: each agent made 4 Reads (its packs) and 1 Write, nothing else; 0 "known outcome" flags.
- Addendum, still before the read: a third forecaster reported six more ids (Q0116, Q0540, Q0644, Q0860: later-created markets
  in the outcome lists or elsewhere in the pack; Q0668, Q0852: **leak C**, the stage-2 price file shows a related market's price at
  a later date). They are dropped too (`data/work/llm1/reported_leaks.json`, read by `llm1_eval.py`; any further reported id goes
  in the same file before the read). Leak C also only helps the model.
