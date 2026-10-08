"""Era table for the meme-tier long/short book. Standard library only.

    python research/era_metrics.py

Reads data/meme_tier_walkforward_daily.csv: one row per daily rebalance of the walk-forward
book (monthly expanding refit, 20% a side of the high-volatility third of the top-250 Binance
perps, 24 h hold), net of tiered costs and settled funding, per unit of one side's notional.
"""
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from audit import stats  # noqa: E402


def load():
    with open(os.path.join(ROOT, "data", "meme_tier_walkforward_daily.csv")) as f:
        return [(r["date"], float(r["net"])) for r in csv.DictReader(f)]


def line(label, values):
    print(f"{label:<22}{len(values):>6}{sum(values) / len(values) * 1e4:>+10.1f}"
          f"{stats.tstat(values):>+8.2f}{stats.sharpe(values):>+8.2f}{stats.max_drawdown(values) * 100:>9.0f}%"
          f"{sum(v > 0 for v in values) / len(values):>8.1%}")


if __name__ == "__main__":
    rows = load()
    print(f"{'period':<22}{'days':>6}{'bp/day':>10}{'t':>8}{'Sharpe':>8}{'max DD':>10}{'win':>8}")
    for year in sorted({d[:4] for d, _ in rows}):
        line(year, [v for d, v in rows if d[:4] == year])
    line("2023-04 to 2025-08", [v for d, v in rows if d < "2025-09"])
    line("2025-09 to 2026-08", [v for d, v in rows if d >= "2025-09"])
    line("all", [v for _, v in rows])
