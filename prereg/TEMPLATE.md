# PREREG-&lt;LABEL&gt;: &lt;one-line rule&gt;

Frozen &lt;date, time&gt; before &lt;the data pull / the first result / the read&gt;. Commit this file on its own.

## Why

The hypothesis in two or three sentences. Who is on the other side of the trade, and why would they keep paying? What earlier result makes this worth one test?

## Method

- **Data**: source, date range, universe. What is excluded and why.
- **Selection**: every list, cohort or model, with the date range it is built from. Nothing may use data from the test period.
- **Rule**: entry, exit, size. Exact enough that two people would code the same thing.
- **Fills and costs**: where the entry fills (worst price in the landing block, next bar open), fees per side, funding, slippage, failed sends.
- **Periods**: P1 selection, P2 confirmation, holdout. The holdout is read once.
- **Search size**: how many configurations will be tried on P1.

## Bars: all must hold

1. Mean return per trade at least ...
2. t-stat clustered by day at least ...
3. Positive in at least ... of ... periods
4. Sample at least ...
5. Top three days less than ...% of profit
6. Placebo arm (same filters, signal shuffled) below ...

## Failure reading

What a fail will be taken to mean, written now. Which family or idea closes with it. What will NOT be tried next on the same data.

## Amendments

Anything changed after the freeze and before the read, with the time and the reason. A change after the read is a new pre-registration.
