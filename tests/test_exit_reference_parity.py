"""Deterministic, read-only differential of managed-position exit decisions."""

import hashlib
import importlib
import json
import random
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FMA = Path.home() / "FMA_Competition/fma_mpb_v41_20261013/fma_mpb_v41"
sys.path.insert(0, str(ROOT / "src"))
from portfolio.exit_policy import ExitParameters, plan_mpb_exit

try:
    import pandas as pd
except ImportError:
    pd = None


@unittest.skipIf(pd is None or not FMA.exists(), "local frozen FMA and pandas required")
class TestFrozenExitParity(unittest.TestCase):
    def test_408_deterministic_cases(self):
        snapshot = json.loads((ROOT / "configs/mpb_exit_reference.json").read_text())
        for name, expected in snapshot["source_sha256"].items():
            self.assertEqual(hashlib.sha256((FMA / name).read_bytes()).hexdigest(), expected)
        sys.path.insert(0, str(FMA))
        reference = importlib.import_module("momentum_pullback_breakout")
        policy = ExitParameters.from_json(ROOT / "configs/mpb_exit_reference.json")
        fixed = [
            (90, 80, 100, 100, False), (89, 80, 100, 100, False),
            (95, 96, 100, 100, False), (100, 100, 100, 100, False),
            (129.99, 80, 100, 100, False), (130, 80, 100, 100, False),
            (150, 80, 100, 100, False), (130, 80, 75, 100, False),
            (150, 80, 50, 100, False), (100, 80, 1000, 1000, False),
            (110, 80, 720, 1000, False), (89, 80, 100, 100, True),
            (100, 80, 1000, 1000, True), (130, 80, 1000, 1000, False),
            (150, 80, 1000, 1000, False), (105, 80, 100, 100, False),
            (130.01, 80, 100, 100, False),
        ]
        rng = random.Random(20261102)
        cases = list(fixed)
        for _ in range(391):
            original = rng.randint(50, 1500)
            cases.append((
                rng.uniform(70, 180), rng.uniform(65, 145),
                rng.randint(1, original), original, bool(rng.getrandbits(1)),
            ))
        self.assertEqual(len(cases), 408)
        for index, (raw, ema, shares, original, same_day) in enumerate(cases):
            adjusted = raw * (0.95 if index % 7 == 0 else 1.0)
            nav = 1_000_000.0
            pos = pd.DataFrame([{
                "ticker": "ZZZ", "sector": "Industrials", "shares": shares,
                "avg_cost": 100.0, "initial_stop": 90.0,
                "initial_shares": original,
                "entry_date": "2025-09-19" if same_day else "2025-09-18",
            }])
            with (
                self.subTest(case=index),
                patch.object(reference, "rankings", return_value=pd.DataFrame()),
                patch.object(reference, "signal_features", return_value={"ema21": ema, "close": adjusted}),
                patch.object(reference, "generate_orders", return_value=pd.DataFrame()),
                patch.object(reference, "compliance_report", return_value=pd.DataFrame()),
            ):
                result = reference.decision(
                    hist={"ZZZ": None, "SPY": None}, universe=pd.DataFrame(),
                    asof="2025-09-19", cash=nav - shares * raw,
                    positions=pos, transactions=pd.DataFrame(columns=["date", "ticker"]),
                    transaction_count=0, prices={"ZZZ": raw},
                )
                expected = result["targets"].iloc[0]
                actual = plan_mpb_exit(
                    shares=shares, original_shares=original, entry_cost=100.0,
                    initial_stop=90.0, close_raw=raw, ema21_adjusted=ema,
                    close_adjusted=adjusted, nav=nav, same_day=same_day, policy=policy,
                )
                self.assertEqual(actual.target_shares, int(expected["target_shares"]))
                self.assertEqual(actual.reason, str(expected["reason"]))
        print("408/408 deterministic managed-position exit cases matched")
