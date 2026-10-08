"""Scorecard: `python -m evals`. Runs in a few seconds, standard library only."""
import sys

from audit import stats

from .scenarios import N_CONFIGS, T_BAR, kill_bar_table, score


def main(runs: int = 300) -> None:
    rows = score(runs)
    print(f"Share of {runs} simulated runs in which each pipeline reported an edge (bar: mean > 0, t >= {T_BAR:g})\n")
    print(f"{'scenario':<46}{'truth':<42}{'naive':>7}{'audited':>9}")
    for r in rows:
        print(f"{r['title']:<46}{r['truth']:<42}{r['naive']:>7.0%}{r['audited']:>9.0%}")
    null = [r for r in rows if not r["edge_is_real"]]
    print(f"\nNo-edge scenarios: naive reports an edge in {sum(r['naive'] for r in null) / len(null):.0%} of runs, "
          f"audited in {sum(r['audited'] for r in null) / len(null):.1%}.")

    print(f"\nMultiple testing at t >= {T_BAR:g}:")
    for n in (20, 115, N_CONFIGS):
        print(f"  {n:>5} tests of nothing: {stats.expected_false_passes(n, T_BAR):6.1f} pass by chance, "
              f"best t is typically {stats.median_best_t(n):.2f}, bar for the best should be {stats.sidak_t(n):.2f}")

    k = kill_bar_table()
    print(f"\nA real edge (mean {k['mean']:+.1%} a trade, median {k['median']:+.1%}) with a -$150 kill bar, 400 trades:")
    for size, p in k["fire"].items():
        print(f"  ${size:>2} a trade: the bar fires in {p:.0%} of paths")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 300)
