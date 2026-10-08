import unittest

from audit import risk


class KillBar(unittest.TestCase):
    right_tail = [-0.3] * 13 + [0.2] * 6 + [2.5]  # mean +0.05, median -0.3

    def test_never_fires_without_losses(self):
        self.assertEqual(risk.kill_bar_fire_prob([0.01, 0.02], size=45, bar=150, n_trades=200, n_paths=200), 0.0)

    def test_always_fires_without_wins(self):
        self.assertEqual(risk.kill_bar_fire_prob([-0.5], size=45, bar=150, n_trades=200, n_paths=200), 1.0)

    def test_bigger_size_never_fires_less(self):
        probs = [risk.kill_bar_fire_prob(self.right_tail, s, 150, 300, n_paths=400, seed=3) for s in (5, 10, 20, 45)]
        self.assertEqual(probs, sorted(probs))
        self.assertGreater(probs[-1], probs[0])

    def test_a_real_edge_still_gets_stopped_out(self):
        p = risk.kill_bar_fire_prob(self.right_tail, size=45, bar=150, n_trades=300, n_paths=400, seed=3)
        self.assertGreater(p, 0.3)

    def test_deterministic(self):
        a = risk.kill_bar_fire_prob(self.right_tail, 20, 150, 300, n_paths=300, seed=5)
        self.assertEqual(a, risk.kill_bar_fire_prob(self.right_tail, 20, 150, 300, n_paths=300, seed=5))

    def test_largest_safe_size(self):
        sizes = (5, 10, 20, 45)
        safe = risk.largest_safe_size(self.right_tail, sizes, 150, 300, max_fire_prob=0.10, n_paths=400, seed=3)
        self.assertIn(safe, sizes[:-1])
        self.assertLessEqual(risk.kill_bar_fire_prob(self.right_tail, safe, 150, 300, n_paths=400, seed=3), 0.10)
        self.assertIsNone(risk.largest_safe_size([-0.5], sizes, 150, 300, n_paths=100))

    def test_rejects_nonsense(self):
        with self.assertRaises(ValueError):
            risk.kill_bar_fire_prob(self.right_tail, size=0, bar=150, n_trades=10)


if __name__ == "__main__":
    unittest.main()
