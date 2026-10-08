"""Guards against using the answer to choose the sample. Standard library only."""
from __future__ import annotations

import json
import os
from statistics import fmean
from typing import Mapping, Sequence


class LookaheadError(ValueError):
    """A selection step saw data from the period it is tested on."""


class HoldoutReused(RuntimeError):
    """A holdout period was read a second time for the same strategy family."""


def check_no_lookahead(selection_end, test_start) -> None:
    """Raise unless every selection input is dated strictly before the test period.

    Works on anything ordered: dates, week numbers, block heights.
    """
    if selection_end >= test_start:
        raise LookaheadError(f"selection uses data to {selection_end!r}, test starts {test_start!r}")


def rolling_top(history: Mapping[str, Sequence[float]], k: int, top_frac: float, min_periods: int = 1) -> list[str]:
    """Names ranked in the top `top_frac` by mean over periods strictly before `k`.

    `history[name][t]` is that name's return in period t. This is the honest version of
    "pick the good wallets": the list for period k is built from periods 0..k-1 only.
    """
    if k < min_periods:
        raise LookaheadError(f"period {k} has fewer than {min_periods} prior periods to select on")
    scores = {name: fmean(r[:k]) for name, r in history.items() if len(r) >= k}
    n_top = max(1, round(len(scores) * top_frac))
    return sorted(scores, key=scores.get, reverse=True)[:n_top]


class HoldoutLedger:
    """Keeps a JSON file of which holdout periods have been read for each strategy family,
    and raises on a second read of an overlapping period.
    """

    def __init__(self, path: str):
        self.path = path
        self._spent: dict[str, list[list]] = {}
        if os.path.exists(path):
            with open(path) as f:
                self._spent = json.load(f)

    def is_spent(self, family: str, start, end) -> bool:
        """True if [start, end] overlaps any period already read for `family`."""
        return any(start <= e and s <= end for s, e in self._spent.get(family, []))

    def spend(self, family: str, start, end) -> None:
        """Mark [start, end] as read for `family`. Call this BEFORE loading the data."""
        if start > end:
            raise ValueError("start is after end")
        if self.is_spent(family, start, end):
            raise HoldoutReused(f"{family}: holdout {start}..{end} overlaps a period already read")
        self._spent.setdefault(family, []).append([start, end])
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self._spent, f, indent=1, sort_keys=True)
        os.replace(tmp, self.path)
