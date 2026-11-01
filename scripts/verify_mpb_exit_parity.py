"""Differential test against the untouched frozen FMA decision.

Valid managed incumbent positions only. Synthetic fixtures.
No orders executed, no original project files modified.
"""

import hashlib
import importlib
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FMA = (
    Path.home()
    / "FMA_Competition/fma_mpb_v41_20261013"
    / "fma_mpb_v41"
)

sys.path.insert(0, str(ROOT / "src"))
from portfolio.exit_policy import (
    ExitParameters, plan_mpb_exit
)

snapshot = json.loads(
    (ROOT / "configs/mpb_exit_reference.json").read_text()
)

# Verify the frozen reference source has not changed.
for name, expected in snapshot["source_sha256"].items():
    path = FMA / name
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise RuntimeError(
            f"FROZEN_SOURCE_HASH_MISMATCH:{name}"
        )

sys.path.insert(0, str(FMA))
reference = importlib.import_module(
    "momentum_pullback_breakout"
)

policy = ExitParameters.from_json(
    ROOT / "configs/mpb_exit_reference.json"
)

cases = [
    {"name": "normal_hold", "raw": 105, "ema": 90},
    {"name": "stop_at_boundary", "raw": 90, "ema": 80},
    {"name": "stop_below", "raw": 89, "ema": 80},
    {"name": "ema_exit", "raw": 95, "ema": 96},
    {"name": "ema_equal_not_exit", "raw": 100, "ema": 100},
    {"name": "below_three_r", "raw": 129.9, "ema": 80},
    {"name": "exact_three_r", "raw": 130, "ema": 80},
    {"name": "exact_five_r", "raw": 150, "ema": 80},
    {
        "name": "repeat_three_r",
        "raw": 130, "ema": 80,
        "shares": 75, "original": 100,
    },
    {
        "name": "repeat_five_r",
        "raw": 150, "ema": 80,
        "shares": 50, "original": 100,
    },
    {
        "name": "concentration",
        "raw": 100, "ema": 80,
        "shares": 1000, "original": 1000,
    },
    {
        "name": "concentration_after_trim",
        "raw": 110, "ema": 80,
        "shares": 720, "original": 1000,
    },
    {
        "name": "same_day_stop_protection",
        "raw": 89, "ema": 80, "same_day": True,
    },
    {
        "name": "same_day_concentration_protection",
        "raw": 100, "ema": 80,
        "shares": 1000, "original": 1000,
        "same_day": True,
    },
    {
        "name": "adjusted_ema_conversion",
        "raw": 100, "adjusted": 95, "ema": 100,
    },
    {
        "name": "three_r_plus_concentration",
        "raw": 130, "ema": 80,
        "shares": 1000, "original": 1000,
    },
    {
        "name": "five_r_plus_concentration",
        "raw": 150, "ema": 80,
        "shares": 1000, "original": 1000,
    },
]

results = []

for case in cases:
    ticker = "ZZZ"
    day = "2025-09-19"
    raw = float(case["raw"])
    adjusted = float(case.get("adjusted", raw))
    ema = float(case["ema"])
    qty = int(case.get("shares", 100))
    original = int(case.get("original", 100))
    same_day = bool(case.get("same_day", False))
    nav = 1_000_000.0

    pos = pd.DataFrame([{
        "ticker": ticker,
        "sector": "Industrials",
        "shares": qty,
        "avg_cost": 100.0,
        "initial_stop": 90.0,
        "initial_shares": original,
        "entry_date": (
            day if same_day else "2025-09-18"
        ),
    }])

    features = {
        "ema21": ema,
        "close": adjusted,
    }

    # Isolate incumbent exit decision from ranking,
    # order scheduling and unrelated compliance checks.
    with (
        patch.object(
            reference, "rankings",
            return_value=pd.DataFrame()
        ),
        patch.object(
            reference, "signal_features",
            return_value=features
        ),
        patch.object(
            reference, "generate_orders",
            return_value=pd.DataFrame()
        ),
        patch.object(
            reference, "compliance_report",
            return_value=pd.DataFrame()
        ),
    ):
        original_result = reference.decision(
            hist={ticker: None, "SPY": None},
            universe=pd.DataFrame(),
            asof=day,
            cash=nav - qty * raw,
            positions=pos,
            transactions=pd.DataFrame(
                columns=["date", "ticker"]
            ),
            transaction_count=0,
            prices={ticker: raw},
        )

    target = original_result["targets"]
    if len(target) != 1:
        raise AssertionError(
            f"UNEXPECTED_REFERENCE_TARGETS:{case['name']}"
        )

    expected_qty = int(target.iloc[0]["target_shares"])
    expected_reason = str(target.iloc[0]["reason"])

    independent = plan_mpb_exit(
        shares=qty,
        original_shares=original,
        entry_cost=100,
        initial_stop=90,
        close_raw=raw,
        ema21_adjusted=ema,
        close_adjusted=adjusted,
        nav=nav,
        same_day=same_day,
        policy=policy,
    )

    match_qty = independent.target_shares == expected_qty
    match_reason = independent.reason == expected_reason

    results.append({
        "case": case["name"],
        "reference_target": expected_qty,
        "research_target": independent.target_shares,
        "reference_reason": expected_reason,
        "research_reason": independent.reason,
        "match": match_qty and match_reason,
        "reference_strategy_issues": (
            original_result["strategy_issues"]
        ),
    })

mismatches = [r for r in results if not r["match"]]

summary = {
    "schema": "MPB_EXIT_DIFFERENTIAL_V1",
    "scope": (
        "Valid managed incumbent positions; synthetic "
        "features; frozen original decision core"
    ),
    "reference_source_sha256": snapshot["source_sha256"],
    "cases": len(results),
    "matched": len(results) - len(mismatches),
    "mismatches": mismatches,
    "status": "PASS" if not mismatches else "FAIL",
    "outcomes": results,
    "limitations": [
        "Signal features and rankings are stubbed.",
        "Order generation is not compared.",
        "Missing metadata and missing feature handling "
        "are not covered.",
        "Not a historical strategy backtest.",
    ],
}

report = ROOT / "audit/mpb_exit_differential.json"
report.parent.mkdir(exist_ok=True)
report.write_text(json.dumps(summary, indent=2) + "\n")

print("=== MPB ORIGINAL VS RESEARCH DIFFERENTIAL ===")
print(json.dumps({
    "status": summary["status"],
    "cases": summary["cases"],
    "matched": summary["matched"],
    "mismatches": mismatches,
    "report": str(report),
}, indent=2))

if mismatches:
    raise SystemExit(1)
