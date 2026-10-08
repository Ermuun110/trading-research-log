import random
import unittest

from audit.order import AmbiguousOrder, Trade, chain_slot, last_in_slot


def make_slot(rng, n):
    """n trades in execution order on a constant-product pool, integer base units."""
    sol, tok = 30_000_000_000, 1_073_000_000_000_000
    k, trades, held = sol * tok, [], 0
    for _ in range(n):
        if held and rng.random() < 0.35:  # sell part of what earlier buys took out
            amount = rng.randint(1, held)
            tok += amount
            sol = k // tok
            held -= amount
            trades.append(Trade(reserve_after=tok, tokens=amount, is_buy=False))
        else:
            sol += rng.randint(10_000_000, 2_000_000_000)
            new_tok = k // sol
            held += tok - new_tok
            trades.append(Trade(reserve_after=new_tok, tokens=tok - new_tok, is_buy=True))
            tok = new_tok
    return trades


class ChainSlot(unittest.TestCase):
    def test_recovers_execution_order_from_shuffled_rows(self):
        for seed in range(200):
            rng = random.Random(seed)
            truth = make_slot(rng, rng.randint(1, 12))
            if len({t.reserve_after for t in truth}) != len(truth):
                continue  # a sell returned the pool to an earlier state: genuinely ambiguous
            rows = truth[:]
            rng.shuffle(rows)
            self.assertEqual(chain_slot(rows), truth, f"seed {seed}")
            self.assertEqual(last_in_slot(rows), truth[-1])

    def test_empty_and_single(self):
        self.assertEqual(chain_slot([]), [])
        only = Trade(reserve_after=90, tokens=10, is_buy=True)
        self.assertEqual(chain_slot([only]), [only])

    def test_missing_row_is_ambiguous(self):
        truth = make_slot(random.Random(1), 6)
        with self.assertRaises(AmbiguousOrder):
            chain_slot(truth[:2] + truth[3:])

    def test_duplicate_row_is_ambiguous(self):
        truth = make_slot(random.Random(2), 4)
        with self.assertRaises(AmbiguousOrder):
            chain_slot(truth + [truth[1]])

    def test_reserve_before(self):
        self.assertEqual(Trade(reserve_after=90, tokens=10, is_buy=True).reserve_before, 100)
        self.assertEqual(Trade(reserve_after=90, tokens=10, is_buy=False).reserve_before, 80)


if __name__ == "__main__":
    unittest.main()
