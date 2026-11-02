import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from portfolio.risk_budget import additional_risk_trim, budget_fraction


class TestRiskBudget(unittest.TestCase):
    def test_dynamic_budget_is_bounded(self):
        self.assertEqual(budget_fraction("A"), 0.04)
        self.assertEqual(budget_fraction("B"), 0.04)
        self.assertEqual(
            budget_fraction("C", sigma_20=0.01, sigma_reference=0.20), 0.05
        )
        self.assertEqual(
            budget_fraction("C", sigma_20=0.80, sigma_reference=0.20), 0.02
        )

    def test_trim_accounts_for_preplanned_mpb_sell(self):
        result = additional_risk_trim(
            {"AAA": {"shares": 100, "stop": 90}},
            {"AAA": 20},
            prices={"AAA": 100},
            nav=10_000,
            risk_fraction=0.04,
            gap_buffer=0.01,
        )
        self.assertEqual(result["extra_sells"], {"AAA": 44})
        self.assertTrue(result["projected_within_budget"])
        self.assertLessEqual(result["projected_risk_dollars"], 400)

    def test_trim_does_not_touch_position_below_budget(self):
        result = additional_risk_trim(
            {"AAA": {"shares": 30, "stop": 90}},
            {},
            prices={"AAA": 100},
            nav=10_000,
            risk_fraction=0.04,
            gap_buffer=0.01,
        )
        self.assertEqual(result["extra_sells"], {})


if __name__ == "__main__":
    unittest.main()
