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


class RiskOfTheBook(unittest.TestCase):
    def test_sharpe_se_at_zero_sharpe(self):
        # SR = 0 leaves sqrt(1 / n) per period; with n = 365 the annualised value is exactly 1
        self.assertAlmostEqual(stats.sharpe_se([0.01, -0.01] * 182 + [0.0]), 1.0, places=6)

    def test_sharpe_se_grows_with_the_sharpe(self):
        flat = [0.01, -0.01] * 100
        tilted = [0.02, 0.0] * 100
        self.assertGreater(stats.sharpe_se(tilted), stats.sharpe_se(flat))

    def test_newey_west_without_lags_is_the_plain_t(self):
        values = [0.3, -0.1, 0.4, 0.2, -0.2, 0.5, 0.1, 0.0]
        n = len(values)
        self.assertAlmostEqual(stats.newey_west_tstat(values, lags=0), stats.tstat(values) * math.sqrt(n / (n - 1)))

    def test_newey_west_shrinks_t_under_positive_autocorrelation(self):
        import random
        rng, x, values = random.Random(3), 0.0, []
        for _ in range(2000):
            x = 0.8 * x + rng.gauss(0.0, 1.0)
            values.append(0.1 + x)
        self.assertLess(stats.newey_west_tstat(values, lags=20), 0.6 * stats.tstat(values))

    def test_newey_west_needs_enough_data(self):
        with self.assertRaises(ValueError):
            stats.newey_west_tstat([0.1, 0.2, 0.3], lags=2)

    def test_kelly(self):
        # mean 0.01, sample variance 0.0002
        self.assertAlmostEqual(stats.kelly_leverage([0.02, 0.0]), 50.0)

    def test_compound_and_ruin(self):
        path = stats.compound([0.1, -0.5, 0.3], leverage=2.0)
        self.assertAlmostEqual(path[0], 1.2)
        self.assertEqual(path[1:], [0.0, 0.0])

    def test_positive_mean_can_lose_money_above_twice_kelly(self):
        values = [0.05, -0.04] * 200            # mean +0.5% a period
        f = stats.kelly_leverage(values)
        self.assertGreater(stats.compound(values, 1.0 * f)[-1], 1.0)
        self.assertLess(stats.compound(values, 2.5 * f)[-1], 1.0)


if __name__ == "__main__":
    unittest.main()
