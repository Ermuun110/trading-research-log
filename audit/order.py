"""Work out the order of trades inside one block from the pool reserves. Standard library only.

A bonding-curve trade records the pool's token reserve after the trade. The reserve before it
follows from the size (add the tokens back for a buy, subtract them for a sell). Inside one
block every trade's "before" is another trade's "after", so they can be linked into a chain.

The archive I used has a block number and a one-second timestamp but no position inside the
block, so "the state as of block S" was returning an arbitrary row. See
case-studies/03-intra-slot-order.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class Trade:
    """One trade on a constant-product pool. Amounts are integers in base units, as on chain."""
    reserve_after: int   # pool token reserve after this trade
    tokens: int          # tokens moved, always positive
    is_buy: bool         # a buy takes tokens OUT of the pool

    @property
    def reserve_before(self) -> int:
        return self.reserve_after + self.tokens if self.is_buy else self.reserve_after - self.tokens


class AmbiguousOrder(ValueError):
    """The trades do not form a single chain (duplicate reserves, a gap, or a missing row)."""


def chain_slot(trades: Sequence[Trade]) -> list[Trade]:
    """Return the trades of one block in execution order.

    Raises AmbiguousOrder when the chain cannot be resolved. Callers should then take the
    worst case for the strategy, never the row the database happened to return first.
    """
    if not trades:
        return []
    by_before: dict[int, Trade] = {}
    for t in trades:
        if t.reserve_before in by_before:
            raise AmbiguousOrder("two trades start from the same reserve")
        by_before[t.reserve_before] = t
    afters = {t.reserve_after for t in trades}
    if len(afters) != len(trades):
        raise AmbiguousOrder("two trades end at the same reserve")
    starts = [t for t in trades if t.reserve_before not in afters]
    if len(starts) != 1:
        raise AmbiguousOrder(f"expected one first trade, found {len(starts)}")
    ordered = [starts[0]]
    while ordered[-1].reserve_after in by_before:
        ordered.append(by_before[ordered[-1].reserve_after])
        if len(ordered) > len(trades):
            raise AmbiguousOrder("cycle in the reserve chain")
    if len(ordered) != len(trades):
        raise AmbiguousOrder("the chain does not cover every trade")
    return ordered


def last_in_slot(trades: Sequence[Trade]) -> Trade:
    """The trade that left the pool in its end-of-block state."""
    return chain_slot(trades)[-1]
