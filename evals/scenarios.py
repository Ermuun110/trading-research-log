"""Ground-truth scenarios for a backtesting pipeline. Standard library only.

Each scenario simulates a market where the true answer is known by construction, then asks
two pipelines the same question: is there an edge worth trading?

    naive    what a fast, competent backtest does by default
    audited  the same backtest with the matching guardrail from `audit`

Every scenario mirrors a failure that happened on real data in this log. The simulations are
deliberately simple: the point is the mechanism, and that a pipeline can be scored against it.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import fmean
from typing import Callable

from audit import leakage, order, risk, stats

T_BAR = 2.0  # the pass bar both pipelines use: mean > 0 and t >= 2


def _passes(t: float, mean: float) -> bool:
    return mean > 0 and t >= T_BAR


@dataclass(frozen=True)
class Scenario:
    key: str
    title: str
    truth: str           # what is true by construction
    edge_is_real: bool   # the correct answer to "is there an edge worth trading?"
    run: Callable[[random.Random], tuple[bool, bool]]  # -> (naive says yes, audited says yes)


# ------------------------------------------------------------------ 1. selection lookahead

def _wallet_weeks(rng: random.Random, skill_sd: float, wallets: int = 300, weeks: int = 19):
    """Weekly returns per wallet: a -5% population mean, optional persistent skill, lots of noise."""
    history = {}
    for w in range(wallets):
        skill = rng.gauss(0.0, skill_sd) if skill_sd else 0.0
        history[f"w{w}"] = [-0.05 + skill + rng.gauss(0.0, 0.30) for _ in range(weeks)]
    return history


def _cohort_test(rng: random.Random, skill_sd: float) -> tuple[bool, bool]:
    history = _wallet_weeks(rng, skill_sd)
    weeks, first_test, top = 19, 8, 0.10
    # naive: pick the best wallets on ALL weeks, then score them on weeks 8..18
    leaked = leakage.rolling_top(history, weeks, top)
    naive_weekly = [fmean(history[w][k] for w in leaked) for k in range(first_test, weeks)]
    # audited: for each test week, pick on earlier weeks only
    honest_weekly = []
    for k in range(first_test, weeks):
        leakage.check_no_lookahead(selection_end=k - 1, test_start=k)
        cohort = leakage.rolling_top(history, k, top)
        honest_weekly.append(fmean(history[w][k] for w in cohort))
    return (_passes(stats.tstat(naive_weekly), fmean(naive_weekly)),
            _passes(stats.tstat(honest_weekly), fmean(honest_weekly)))


def selection_lookahead(rng):
    return _cohort_test(rng, skill_sd=0.0)


def selection_real_skill(rng):
    return _cohort_test(rng, skill_sd=0.10)


# ------------------------------------------------------------------ 2. order inside a block

def _bundle_slot(rng: random.Random):
    """One block of 3-10 buys on a pump.fun-shaped constant-product curve, rows shuffled.

    Returns (rows in storage order, price after each row keyed by reserve, true end-of-block price).
    """
    sol, tok = 30_000_000_000, 1_073_000_000_000_000  # virtual reserves: 30 SOL, 1.073B tokens
    k = sol * tok
    rows, price_at = [], {}
    for _ in range(rng.randint(3, 10)):
        sol += int(rng.uniform(0.2, 2.0) * 1e9)
        new_tok = k // sol
        rows.append(order.Trade(reserve_after=new_tok, tokens=tok - new_tok, is_buy=True))
        tok = new_tok
        price_at[tok] = sol / tok
    end_price = sol / tok
    rng.shuffle(rows)  # the archive has no index inside the block
    return rows, price_at, end_price


def intra_block_order(rng):
    fee, naive, audited = 0.0125, [], []
    for _ in range(200):
        rows, price_at, _ = _bundle_slot(rng)
        exit_mult = math.exp(rng.gauss(-0.5 * 0.15 ** 2, 0.15))  # zero-drift move after entry
        naive_entry = price_at[rows[0].reserve_after]             # "latest row": arbitrary among ties
        true_entry = price_at[order.last_in_slot(rows).reserve_after]
        exit_price = true_entry * exit_mult
        naive.append(exit_price / naive_entry * (1 - fee) ** 2 - 1)
        audited.append(exit_price / true_entry * (1 - fee) ** 2 - 1)
    return (_passes(stats.tstat(naive), fmean(naive)),
            _passes(stats.tstat(audited), fmean(audited)))


# ------------------------------------------------------------------ 3. trades that share a day

def clustered_trades(rng):
    values, days = [], []
    for day in range(60):
        market = rng.gauss(0.0, 0.03)  # every trade that day shares this move
        for _ in range(20):
            values.append(market + rng.gauss(0.0, 0.05))
            days.append(day)
    m = fmean(values)
    return _passes(stats.tstat(values), m), _passes(stats.clustered_tstat(values, days), m)


# ------------------------------------------------------------------ 4. best of a grid

N_CONFIGS = 4752


def grid_search(rng):
    # under the null every configuration's t-stat is a standard normal draw
    best = max(rng.gauss(0.0, 1.0) for _ in range(N_CONFIGS))
    confirm = rng.gauss(0.0, 1.0)  # the frozen winner on data it has never seen
    return best >= T_BAR, best >= T_BAR and confirm >= T_BAR


# ------------------------------------------------------------------ 5. one good year

def one_good_year(rng):
    # 950 days at -20 bp/day, then 250 days at +160 bp/day: the shape of the meme-perp book
    daily = [rng.gauss(-0.0020, 0.06) for _ in range(950)] + [rng.gauss(0.0160, 0.06) for _ in range(250)]
    research_year = daily[-250:]
    naive = _passes(stats.tstat(research_year), fmean(research_year))
    eras = [i * 4 // len(daily) for i in range(len(daily))]  # four consecutive eras
    per_era = stats.era_split(daily, eras)
    audited = (_passes(stats.tstat(daily), fmean(daily))
               and all(mean > 0 for _, mean, _ in per_era.values()))
    return naive, audited


# ------------------------------------------------------------------ 6. selling lottery tickets

def short_lottery(rng):
    price, n = 0.02, 100  # sell 100 contracts at 2 cents, fairly priced
    losses = sum(rng.random() < price for _ in range(n))
    pnl = [price - 1.0] * losses + [price] * (n - losses)
    naive = _passes(stats.tstat(pnl), fmean(pnl))
    audited = fmean(pnl) > 0 and stats.lottery_pvalue(losses, n, price) < 0.05
    return naive, audited


SCENARIOS = [
    Scenario("lookahead", "Wallet list picked on the test weeks", "no skill, population mean -5%", False,
             selection_lookahead),
    Scenario("block-order", "Entry priced at an arbitrary row of the block", "zero drift, 2.5% fees", False,
             intra_block_order),
    Scenario("clustering", "t-stat over trades that share a day", "zero mean", False, clustered_trades),
    Scenario("grid", f"Best of {N_CONFIGS:,} configurations", "every configuration has zero edge", False,
             grid_search),
    Scenario("one-year", "Research on the last year only", "negative for 950 days, positive for 250", False,
             one_good_year),
    Scenario("lottery", "Dollar t-stat on 2-cent contracts", "fairly priced", False, short_lottery),
    Scenario("real-skill", "Wallet list, persistent skill present", "skill sd 10 points a week", True,
             selection_real_skill),
]


def score(runs: int = 300) -> list[dict]:
    """Run every scenario `runs` times. Returns the share of runs where each pipeline said "edge"."""
    out = []
    for i, sc in enumerate(SCENARIOS):
        naive = audited = 0
        for r in range(runs):
            n, a = sc.run(random.Random(100_003 * (i + 1) + r))
            naive += n
            audited += a
        out.append(dict(key=sc.key, title=sc.title, truth=sc.truth, edge_is_real=sc.edge_is_real,
                        naive=naive / runs, audited=audited / runs))
    return out


# ------------------------------------------------------------------ sizing: a real edge, killed by its stop

def right_tail_returns(rng: random.Random, n: int = 20_000) -> list[float]:
    """Per-trade returns with a real edge of about +2.5% and a negative median: the shape of a memecoin book."""
    out = []
    for _ in range(n):
        u = rng.random()
        if u < 0.645:
            out.append(rng.uniform(-0.50, -0.05))
        elif u < 0.935:
            out.append(rng.uniform(0.0, 0.50))
        else:
            out.append(rng.uniform(1.0, 3.0))
    return out


def kill_bar_table(bar: float = 150.0, n_trades: int = 400, sizes=(10, 15, 25, 45)) -> dict:
    """Chance a -$150 kill bar fires within 400 trades, by position size, on an edge that is real."""
    returns = right_tail_returns(random.Random(7))
    return dict(mean=fmean(returns), median=sorted(returns)[len(returns) // 2],
                fire={s: risk.kill_bar_fire_prob(returns, s, bar, n_trades, n_paths=2000, seed=11) for s in sizes})
