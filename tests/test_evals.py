import unittest

from evals.scenarios import SCENARIOS, score


class Scorecard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r["key"]: r for r in score(runs=80)}

    def test_every_scenario_is_scored(self):
        self.assertEqual(set(self.rows), {s.key for s in SCENARIOS})

    def test_audited_pipeline_rarely_reports_an_edge_that_is_not_there(self):
        for key, r in self.rows.items():
            if not r["edge_is_real"]:
                self.assertLessEqual(r["audited"], 0.10, key)
                self.assertGreater(r["naive"], r["audited"], key)

    def test_naive_pipeline_is_reliably_fooled_by_the_structural_leaks(self):
        for key in ("lookahead", "block-order", "grid", "one-year"):
            self.assertGreaterEqual(self.rows[key]["naive"], 0.9, key)

    def test_audited_pipeline_still_finds_a_real_edge(self):
        self.assertGreaterEqual(self.rows["real-skill"]["audited"], 0.8)

    def test_deterministic(self):
        self.assertEqual(score(runs=10), score(runs=10))


if __name__ == "__main__":
    unittest.main()
