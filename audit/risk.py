"""Position size against a kill bar (a stop on total losses). Standard library only.

When most trades lose a little and a few win a lot, normal losing streaks are long, and a stop
at a round number gets hit even by a strategy that works. These functions estimate how often.
"""
from __future__ import annotations

import random
from typing import Sequence


def kill_bar_fire_prob(returns: Sequence[float], size: float, bar: float, n_trades: int,
                       n_paths: int = 2000, seed: int = 0) -> float:
    """Chance that cumulative profit touches -`bar` within `n_trades`.

    `returns` are per-trade fractional returns observed out of sample, resampled with
    replacement into `n_paths` equity paths at `size` dollars a trade. Assumes trades are
    independent, which understates the risk when losses cluster. Path i draws from its own
    generator, so two sizes are compared on the same paths and the result is monotone in size.
    """
    if size <= 0 or bar <= 0:
        raise ValueError("size and bar must be positive")
    fired = 0
    for i in range(n_paths):
        rng = random.Random(seed * 1_000_003 + i)
        equity = 0.0
        for _ in range(n_trades):
            equity += size * rng.choice(returns)
            if equity <= -bar:
                fired += 1
                break
    return fired / n_paths


def largest_safe_size(returns: Sequence[float], sizes: Sequence[float], bar: float, n_trades: int,
                      max_fire_prob: float = 0.10, n_paths: int = 2000, seed: int = 0) -> float | None:
    """Largest of `sizes` whose kill bar fires no more often than `max_fire_prob`. None if none qualifies."""
    ok = [s for s in sorted(sizes)
          if kill_bar_fire_prob(returns, s, bar, n_trades, n_paths, seed) <= max_fire_prob]
    return ok[-1] if ok else None
