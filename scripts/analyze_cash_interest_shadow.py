"""Cash interest shadow analysis; existing trades stay fixed."""

import csv
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"

def read(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))

rows_by_policy = {}
results = {}

for policy in "ABC":
    path = AUDIT / f"p3_lifecycle_v4_{policy}_daily.csv"
    rows = read(path)

    if len(rows) != 282:
        raise RuntimeError("EXPECTED_282_SESSIONS")

    rows_by_policy[policy] = rows
    dates = [date.fromisoformat(r["date"]) for r in rows]
    if dates != sorted(set(dates)):
        raise RuntimeError("INVALID_CALENDAR")

    interest = 0.0
    interval_days = 0

    for i in range(1, len(rows)):
        gap = (dates[i] - dates[i-1]).days
        prior_cash = float(rows[i-1]["cash"])

        if gap <= 0 or prior_cash < 0:
            raise RuntimeError("INVALID_ACCRUAL_INPUT")

        # ACT/365 simple interest, from prior close.
        # Excludes the first study date.
        # This interest is NOT added to tradable cash.
        interest += prior_cash * 0.03 * gap / 365
        interval_days += gap

    terminal_nav = float(rows[-1]["nav"])

    results[policy] = {
        "terminal_nav_original": round(terminal_nav, 2),
        "illustrative_cash_interest_3pct": round(
            interest, 2
        ),
        "illustrative_nav_plus_interest": round(
            terminal_nav + interest, 2
        ),
        "accrued_calendar_days": interval_days,
    }

if any(
    [r["date"] for r in rows_by_policy[p]]
    != [r["date"] for r in rows_by_policy["A"]]
    for p in "BC"
):
    raise RuntimeError("POLICY_CALENDAR_MISMATCH")

comparisons = {}
for p in "BC":
    comparisons[p + "_minus_A"] = {
        "original_nav_difference": round(
            results[p]["terminal_nav_original"]
            - results["A"]["terminal_nav_original"],
            2
        ),
        "shadow_interest_difference": round(
            results[p]["illustrative_cash_interest_3pct"]
            - results["A"]["illustrative_cash_interest_3pct"],
            2
        ),
        "illustrative_combined_difference": round(
            results[p]["illustrative_nav_plus_interest"]
            - results["A"]["illustrative_nav_plus_interest"],
            2
        ),
    }

report = {
    "schema": "CASH_SHADOW_INTEREST_V1",
    "status": "PASS",
    "rate_annual": 0.03,
    "basis": "ACT_365_PRIOR_CLOSE_CASH",
    "policies": results,
    "comparisons": comparisons,
    "limitations": [
        "Not a trading simulation.",
        "Interest does not become buying power.",
        "No interest-on-interest compounding.",
        "First study day is excluded.",
        "3pct is a hypothetical scenario, not a "
        "verified historical cash yield.",
        "Does not resolve provisional dividend pay dates.",
    ],
}

path = AUDIT / "p3_cash_shadow_interest.json"
path.write_text(json.dumps(report, indent=2) + "\n")

print("=== A/B/C CASH INTEREST SHADOW ===")
print(json.dumps({
    "policies": results,
    "comparisons": comparisons,
}, indent=2))
print("REPORT:", path)
