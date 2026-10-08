import math
import unittest
from statistics import fmean, stdev

from audit import stats


class TStat(unittest.TestCase):
    def test_known_value(self):
        self.assertAlmostEqual(stats.tstat([1, 2, 3, 4, 5]), 3 / (stdev([1, 2, 3, 4, 5]) / math.sqrt(5)))
        self.assertAlmostEqual(stats.tstat([1, 2, 3, 4, 5]), 4.2426, places=3)

    def test_zero_variance_is_infinite_not_an_error(self):
        self.assertEqual(stats.tstat([0.02] * 50), math.inf)
        self.assertEqual(stats.tstat([-0.02] * 50), -math.inf)
        self.assertEqual(stats.tstat([0.0] * 50), 0.0)

    def test_needs_two_observations(self):
        with self.assertRaises(ValueError):
            stats.tstat([1.0])


class Clustering(unittest.TestCase):
    values = [1, 1, 1, 1, -1, -1, -1, -1, 1, 1, 1, 1]
    days = [0] * 4 + [1] * 4 + [2] * 4

    def test_cluster_sums(self):
        self.assertEqual(stats.cluster_sums(self.values, self.days), [4, -4, 4])

    def test_clustered_t_is_the_t_of_the_day_sums(self):
        self.assertAlmostEqual(stats.clustered_tstat(self.values, self.days), 0.5)

    def test_clustering_removes_the_inflation(self):
        self.assertGreater(stats.tstat(self.values), 2 * stats.clustered_tstat(self.values, self.days))

    def test_length_mismatch(self):
        with self.assertRaises(ValueError):
            stats.cluster_sums([1, 2], [0])

    def test_top_share(self):
        self.assertAlmostEqual(stats.top_share([5, 1, 1, 1], "abcd", k=1), 5 / 8)
        self.assertGreater(stats.top_share([10, -3, -3, -3], "abcd", k=1), 1.0)  # the rest lost money
        self.assertTrue(math.isnan(stats.top_share([-1, -1], "ab")))


class Series(unittest.TestCase):
    def test_capped(self):
        self.assertEqual(stats.capped([0.5, 9.0, -1.0], 3.0), [0.5, 3.0, -1.0])

    def test_era_split(self):
        out = stats.era_split([1, 2, 3, -1, -2, -3], ["a"] * 3 + ["b"] * 3)
        self.assertEqual(out["a"][:2], (3, 2.0))
        self.assertEqual(out["b"][:2], (3, -2.0))
        self.assertAlmostEqual(out["a"][2], -out["b"][2])

    def test_sharpe_scales_with_root_time(self):
        r = [0.01, -0.01, 0.02, 0.0, 0.005]
        self.assertAlmostEqual(stats.sharpe(r, 1), fmean(r) / stdev(r))
        self.assertAlmostEqual(stats.sharpe(r, 4), 2 * stats.sharpe(r, 1))

    def test_max_drawdown(self):
        self.assertAlmostEqual(stats.max_drawdown([1, -2, 1, -3, 5]), 4.0)  # peak +1, trough -3
        self.assertEqual(stats.max_drawdown([1, 1, 1]), 0.0)


class MultipleTesting(unittest.TestCase):
    def test_false_pass_rate(self):
        self.assertAlmostEqual(stats.false_pass_rate(2.0), 0.02275, places=4)
        self.assertAlmostEqual(stats.expected_false_passes(115, 2.0), 115 * 0.02275, places=2)
        self.assertAlmostEqual(stats.prob_any_false_pass(1, 2.0), stats.false_pass_rate(2.0))
        self.assertGreater(stats.prob_any_false_pass(115, 2.0), 0.9)

    def test_best_of_n(self):
        self.assertAlmostEqual(stats.median_best_t(1), 0.0)
        self.assertAlmostEqual(stats.median_best_t(4752), 3.62, delta=0.02)
        self.assertLess(stats.median_best_t(20), stats.median_best_t(200))

    def test_sidak(self):
        self.assertAlmostEqual(stats.sidak_t(1), 1.645, places=3)
        self.assertAlmostEqual(stats.sidak_t(20), 2.80, delta=0.01)
        # the bar for the best of n keeps the family-wise rate at alpha
        self.assertAlmostEqual(stats.prob_any_false_pass(115, stats.sidak_t(115)), 0.05, places=6)


class Lottery(unittest.TestCase):
    def test_binom_cdf(self):
        self.assertAlmostEqual(stats.binom_cdf(2, 5, 0.5), 16 / 32)
        self.assertAlmostEqual(stats.binom_cdf(0, 100, 0.02), 0.98 ** 100)
        self.assertEqual(stats.binom_cdf(-1, 10, 0.5), 0.0)
        self.assertEqual(stats.binom_cdf(10, 10, 0.5), 1.0)
        with self.assertRaises(ValueError):
            stats.binom_cdf(1, 10, 1.0)

    def test_no_losses_in_100_is_not_evidence(self):
        self.assertGreater(stats.lottery_pvalue(0, 100, 0.02), 0.05)

    def test_no_losses_in_300_is(self):
        self.assertLess(stats.lottery_pvalue(0, 300, 0.02), 0.05)


if __name__ == "__main__":
    unittest.main()
