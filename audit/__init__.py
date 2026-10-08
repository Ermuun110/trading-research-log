"""The guardrails in GUARDRAILS.md, as code.

    stats    t-stats that respect clustering, multiple testing, lottery payoffs, era splits
    leakage  no-lookahead checks and a single-use holdout ledger
    order    exact trade order inside a block, rebuilt from pool reserves
    risk     kill bars and sizing from the return distribution

Standard library only. Run the tests with `python -m unittest`, the evals with `python -m evals`.
"""
from . import leakage, order, risk, stats

__all__ = ["leakage", "order", "risk", "stats"]
