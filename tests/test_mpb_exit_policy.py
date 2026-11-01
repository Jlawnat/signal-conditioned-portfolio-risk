import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from portfolio.exit_policy import (
    ExitParameters, plan_mpb_exit
)

POLICY = ExitParameters.from_json(
    ROOT / "configs/mpb_exit_reference.json"
)


def plan(close, ema=80, shares=100, original=100,
         nav=1_000_000, same_day=False):
    return plan_mpb_exit(
        shares=shares,
        original_shares=original,
        entry_cost=100,
        initial_stop=90,
        close_raw=close,
        ema21_adjusted=ema,
        close_adjusted=close,
        nav=nav,
        same_day=same_day,
        policy=POLICY,
    )


class TestMPBExits(unittest.TestCase):
    def test_planned_stop(self):
        r = plan(89)
        self.assertEqual(r.target_shares, 0)
        self.assertEqual(r.reason, "planned_stop_breach")

    def test_ema21_exit(self):
        r = plan(105, ema=106)
        self.assertEqual(r.target_shares, 0)
        self.assertEqual(
            r.reason, "trend_exit_below_ema21"
        )

    def test_three_r(self):
        close = 100 + (POLICY.levels[0] + 0.01) * 10
        r = plan(close)
        expected = math.floor(
            100 * (1 - POLICY.fractions[0])
        )
        self.assertEqual(r.target_shares, expected)
        self.assertEqual(
            r.reason, "cumulative_3R_profit_take"
        )

    def test_five_r(self):
        close = 100 + (POLICY.levels[1] + 0.01) * 10
        r = plan(close)
        expected = math.floor(
            100 * (1 - POLICY.fractions[1])
        )
        self.assertEqual(r.target_shares, expected)
        self.assertEqual(
            r.reason, "cumulative_5R_profit_take"
        )

    def test_no_repeat_overtrim(self):
        close = 100 + (POLICY.levels[0] + 0.01) * 10
        target = math.floor(
            100 * (1 - POLICY.fractions[0])
        )
        r = plan(close, shares=target, original=100)
        self.assertEqual(r.target_shares, target)

    def test_concentration_trim(self):
        r = plan(
            100, shares=1000, original=1000,
            nav=1_000_000
        )
        expected = math.floor(
            POLICY.trim_target * 1_000_000 / 100
        )
        self.assertEqual(r.target_shares, expected)
        self.assertEqual(
            r.reason, "concentration_guard_trim"
        )

    def test_same_day_protection(self):
        r = plan(
            89, shares=1000, original=1000,
            same_day=True
        )
        self.assertEqual(r.target_shares, 1000)

    def test_invalid_fill_metadata_rejected(self):
        with self.assertRaises(ValueError):
            plan_mpb_exit(
                shares=100,
                original_shares=100,
                entry_cost=95,
                initial_stop=100,
                close_raw=105,
                ema21_adjusted=100,
                close_adjusted=105,
                nav=1_000_000,
                same_day=False,
                policy=POLICY,
            )


if __name__ == "__main__":
    unittest.main()
