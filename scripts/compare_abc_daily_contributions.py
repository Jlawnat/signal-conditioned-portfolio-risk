"""Paired daily NAV difference analysis for A/B/C.

Exploratory descriptive attribution, not causal inference.
"""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
INITIAL_NAV = 1_000_000.0

def load_csv(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))

series = {}

for policy in "ABC":
    prefix = f"p3_lifecycle_v3_{policy}"
    summary = json.loads(
        (AUDIT / f"{prefix}_summary.json").read_text()
    )
    audit = json.loads(
        (AUDIT / f"{prefix}_independent_audit.json").read_text()
    )

    if summary["status"] != "PASS" or audit["status"] != "PASS":
        raise RuntimeError(f"UNAUDITED_POLICY:{policy}")

    rows = load_csv(AUDIT / f"{prefix}_daily.csv")
    if len(rows) != 30:
        raise RuntimeError("UNEXPECTED_SESSION_COUNT")

    series[policy] = rows

dates = [r["date"] for r in series["A"]]

for policy in "BC":
    if [r["date"] for r in series[policy]] != dates:
        raise RuntimeError("MISALIGNED_POLICY_DATES")

previous = {p: INITIAL_NAV for p in "ABC"}
results = []

for index, day in enumerate(dates):
    current = {
        p: float(series[p][index]["nav"])
        for p in "ABC"
    }
    pnl = {
        p: current[p] - previous[p]
        for p in "ABC"
    }

    results.append({
        "date": day,
        "pnl_A": round(pnl["A"], 2),
        "pnl_B": round(pnl["B"], 2),
        "pnl_C": round(pnl["C"], 2),
        "B_minus_A": round(pnl["B"] - pnl["A"], 2),
        "C_minus_A": round(pnl["C"] - pnl["A"], 2),
        "B_minus_C": round(pnl["B"] - pnl["C"], 2),
        "nav_A": round(current["A"], 2),
        "nav_B": round(current["B"], 2),
        "nav_C": round(current["C"], 2),
    })
    previous = current

comparisons = {}

for key in ("B_minus_A", "C_minus_A", "B_minus_C"):
    ranked = sorted(
        results, key=lambda r: r[key], reverse=True
    )

    comparisons[key] = {
        "total_nav_difference_usd": round(
            sum(r[key] for r in results), 2
        ),
        "days_positive": sum(
            r[key] > 0 for r in results
        ),
        "days_negative": sum(
            r[key] < 0 for r in results
        ),
        "largest_positive_contributions": [
            {"date": r["date"], "usd": r[key]}
            for r in ranked[:5]
        ],
        "largest_negative_contributions": [
            {"date": r["date"], "usd": r[key]}
            for r in ranked[-5:]
        ],
    }

# Verify the sum of paired daily P&L differences
# equals the difference in terminal NAV.
for pair, left, right in (
    ("B_minus_A", "B", "A"),
    ("C_minus_A", "C", "A"),
    ("B_minus_C", "B", "C"),
):
    actual = previous[left] - previous[right]
    recorded = comparisons[pair][
        "total_nav_difference_usd"
    ]
    if abs(actual - recorded) > 0.15:
        raise RuntimeError("PNL_DIFFERENCE_BRIDGE_FAILED")

report = {
    "schema": "ABC_PAIRED_DAILY_CONTRIBUTIONS_V1",
    "status": "PASS",
    "sessions": len(dates),
    "comparisons": comparisons,
    "caveat": (
        "Paired calendar-day NAV differences are "
        "descriptive, not causal factor attribution."
    ),
}

(AUDIT / "p3_abc_daily_contributions.json").write_text(
    json.dumps(report, indent=2) + "\n"
)

print("=== A/B/C DAILY CONTRIBUTION ANALYSIS ===")
print(json.dumps(report, indent=2))
