import datetime as dt
import os
import tempfile
import unittest

from audit import leakage


class NoLookahead(unittest.TestCase):
    def test_selection_must_end_before_the_test(self):
        leakage.check_no_lookahead(selection_end=7, test_start=8)
        with self.assertRaises(leakage.LookaheadError):
            leakage.check_no_lookahead(selection_end=8, test_start=8)
        with self.assertRaises(leakage.LookaheadError):
            leakage.check_no_lookahead(selection_end=18, test_start=0)  # the 608-wallet cohort

    def test_works_on_dates(self):
        leakage.check_no_lookahead(dt.date(2026, 8, 25), dt.date(2026, 8, 26))
        with self.assertRaises(leakage.LookaheadError):
            leakage.check_no_lookahead(dt.date(2026, 9, 1), dt.date(2026, 8, 26))


class RollingTop(unittest.TestCase):
    history = {"steady": [0.1] * 6, "late": [-0.5, -0.5, -0.5, 9.0, 9.0, 9.0], "bad": [-0.2] * 6}

    def test_only_earlier_periods_count(self):
        self.assertEqual(leakage.rolling_top(self.history, 3, top_frac=0.34), ["steady"])
        self.assertEqual(leakage.rolling_top(self.history, 6, top_frac=0.34), ["late"])

    def test_refuses_to_select_on_nothing(self):
        with self.assertRaises(leakage.LookaheadError):
            leakage.rolling_top(self.history, 0, top_frac=0.5)


class Ledger(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "holdouts.json")

    def tearDown(self):
        self.dir.cleanup()

    def test_second_read_is_refused(self):
        ledger = leakage.HoldoutLedger(self.path)
        ledger.spend("launch-selection", "2026-08-26", "2026-09-01")
        with self.assertRaises(leakage.HoldoutReused):
            ledger.spend("launch-selection", "2026-08-26", "2026-09-01")
        with self.assertRaises(leakage.HoldoutReused):
            ledger.spend("launch-selection", "2026-08-30", "2026-09-05")  # overlap counts

    def test_other_family_or_other_period_is_fine(self):
        ledger = leakage.HoldoutLedger(self.path)
        ledger.spend("launch-selection", "2026-08-26", "2026-09-01")
        ledger.spend("wallet-copy", "2026-08-26", "2026-09-01")
        ledger.spend("launch-selection", "2026-09-02", "2026-09-08")

    def test_survives_a_restart(self):
        leakage.HoldoutLedger(self.path).spend("flush", "2026-09-01", "2026-09-18")
        reopened = leakage.HoldoutLedger(self.path)
        self.assertTrue(reopened.is_spent("flush", "2026-09-10", "2026-09-12"))
        with self.assertRaises(leakage.HoldoutReused):
            reopened.spend("flush", "2026-09-01", "2026-09-18")

    def test_rejects_a_backwards_range(self):
        with self.assertRaises(ValueError):
            leakage.HoldoutLedger(self.path).spend("x", 5, 1)


if __name__ == "__main__":
    unittest.main()
