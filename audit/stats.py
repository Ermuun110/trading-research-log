"""Statistics used for the verdicts in this log. Standard library only.

Each function is here because I got a result wrong without it. GUARDRAILS.md has the stories.
"""
from __future__ import annotations

import math
from collections import defaultdict
from statistics import NormalDist, fmean, stdev
from typing import Hashable, Sequence

_NORMAL = NormalDist()


def tstat(values: Sequence[float]) -> float:
    """One-sample t-statistic of the mean against zero.

    Assumes the observations are independent. Trades usually are not: use
    `clustered_tstat` unless you can argue otherwise.
    """
    n = len(values)
    if n < 2:
        raise ValueError("need at least two observations")
    m, sd = fmean(values), stdev(values)
    if sd == 0:
        return math.copysign(math.inf, m) if m else 0.0
    return m / (sd / math.sqrt(n))


def cluster_sums(values: Sequence[float], groups: Sequence[Hashable]) -> list[float]:
    """Sum of `values` inside each group (a day, a market, an event), in first-seen order."""
    if len(values) != len(groups):
        raise ValueError("values and groups differ in length")
    sums: dict[Hashable, float] = defaultdict(float)
    for v, g in zip(values, groups):
        sums[g] += v
    return list(sums.values())


def clustered_tstat(values: Sequence[float], groups: Sequence[Hashable]) -> float:
    """t-statistic of the per-group sums.

    Trades that share a day share a market move. Treating them as independent multiplies
    the t-stat by roughly sqrt(1 + (m - 1) * rho) for m trades a day with correlation rho.
    Collapsing to one number per day removes that inflation.
    """
    return tstat(cluster_sums(values, groups))


def top_share(values: Sequence[float], groups: Sequence[Hashable], k: int = 3) -> float:
    """Share of total profit that comes from the best `k` groups.

    Above 1.0 means the rest of the sample lost money. Undefined (nan) if the total is not positive.
    """
    sums = sorted(cluster_sums(values, groups), reverse=True)
    total = sum(sums)
    return sum(sums[:k]) / total if total > 0 else math.nan


def capped(values: Sequence[float], cap: float) -> list[float]:
    """Clip each value at `cap`, so that one huge winner can't carry the mean."""
    return [min(v, cap) for v in values]


def era_split(values: Sequence[float], eras: Sequence[Hashable]) -> dict[Hashable, tuple[int, float, float]]:
    """Per-era (n, mean, t-stat). An edge that lives in one era is a regime bet."""
    by_era: dict[Hashable, list[float]] = defaultdict(list)
    for v, e in zip(values, eras):
        by_era[e].append(v)
    return {e: (len(v), fmean(v), tstat(v)) for e, v in by_era.items()}


def sharpe(period_returns: Sequence[float], periods_per_year: float = 365.0) -> float:
    """Annualised Sharpe ratio of a return series, zero risk-free rate. Crypto trades every day: 365."""
    return fmean(period_returns) / stdev(period_returns) * math.sqrt(periods_per_year)


def max_drawdown(period_returns: Sequence[float]) -> float:
    """Largest peak-to-trough fall of the cumulative (additive) return. Returned as a positive number."""
    peak = cum = worst = 0.0
    for r in period_returns:
        cum += r
        peak = max(peak, cum)
        worst = max(worst, peak - cum)
    return worst


# ----------------------------------------------------------------- multiple testing

def false_pass_rate(t_bar: float) -> float:
    """Chance that a strategy with no edge clears a one-sided bar of `t_bar` (normal approximation)."""
    return 1.0 - _NORMAL.cdf(t_bar)


def expected_false_passes(n_tests: int, t_bar: float) -> float:
    """How many of `n_tests` zero-edge strategies clear `t_bar` by chance."""
    return n_tests * false_pass_rate(t_bar)


def prob_any_false_pass(n_tests: int, t_bar: float) -> float:
    """Chance that at least one of `n_tests` independent zero-edge strategies clears `t_bar`."""
    return 1.0 - (1.0 - false_pass_rate(t_bar)) ** n_tests


def median_best_t(n_tests: int) -> float:
    """Median of the best t-stat among `n_tests` independent zero-edge strategies.

    For 4,752 configurations this is about 3.6.
    """
    return _NORMAL.inv_cdf(0.5 ** (1.0 / n_tests))


def sidak_t(n_tests: int, alpha: float = 0.05) -> float:
    """t-bar the BEST of `n_tests` must clear for a family-wise false-pass rate of `alpha`."""
    return _NORMAL.inv_cdf((1.0 - alpha) ** (1.0 / n_tests))


# ------------------------------------------------------------------ lottery payoffs

def binom_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p), summed in log space."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be strictly between 0 and 1")
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    log_p, log_q = math.log(p), math.log1p(-p)
    total = 0.0
    for i in range(k + 1):
        log_pmf = (math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
                   + i * log_p + (n - i) * log_q)
        total += math.exp(log_pmf)
    return min(total, 1.0)


def lottery_pvalue(losses: int, n: int, implied_loss_prob: float) -> float:
    """P-value for "we lost less often than the price implies".

    Selling a contract at 2 cents wins 98 times in 100 when the price is fair. A t-stat over
    dollars per trade is useless here: a run with no losses has zero variance and an infinite t.
    The honest question is whether `losses` is surprisingly few given `n` and the price.
    """
    return binom_cdf(losses, n, implied_loss_prob)
