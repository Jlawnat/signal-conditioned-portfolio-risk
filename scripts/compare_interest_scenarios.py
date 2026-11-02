"""Read-only ACT/365 cash-interest sensitivity.

No trading, compounding, or cash reinvestment.
"""

import csv
import json
from datetime import date
from pathlib import Path

ROOT = Path("audit")
START_NAV = 1_000_000.0
RATE = 0.03


def read_csv(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


results = {}

for version in ("v4", "v5u"):
    results[version] = {}

    common_dates = None

    for policy in "ABC":
        path = ROOT / (
            f"p3_lifecycle_{version}_{policy}_daily.csv"
        )
        rows = read_csv(path)

        dates = [
            date.fromisoformat(r["date"])
            for r in rows
        ]

        if len(rows) != 282 or dates != sorted(set(dates)):
            raise RuntimeError("INVALID_SESSION_DATA")

        if common_dates is None:
            common_dates = dates
        elif dates != common_dates:
            raise RuntimeError("DATE_MISMATCH")

        shadow_interest = 0.0

        for i in range(1, len(rows)):
            days = (dates[i] - dates[i-1]).days
            cash = float(rows[i-1]["cash"])

            if cash < 0 or days <= 0:
                raise RuntimeError("INVALID_CASH_OR_DATE")

            shadow_interest += cash * RATE * days / 365

        original = float(rows[-1]["nav"])

        results[version][policy] = {
            "original_nav": round(original, 2),
            "shadow_interest": round(shadow_interest, 2),
            "illustrative_nav": round(
                original + shadow_interest, 2
            ),
            "original_return_pct": round(
                100 * (original / START_NAV - 1), 4
            ),
            "illustrative_return_pct": round(
                100 * (
                    (original + shadow_interest)
                    / START_NAV - 1
                ), 4
            ),
        }

print("=== V4 VS V5-U CASH INTEREST SENSITIVITY ===")

for version in ("v4", "v5u"):
    print(f"\nVERSION: {version.upper()}")

    for policy in "ABC":
        r = results[version][policy]
        print(
            policy,
            "original_return_pct:",
            r["original_return_pct"],
            "shadow_3pct_return:",
            r["illustrative_return_pct"],
            "shadow_interest_usd:",
            r["shadow_interest"],
        )

    a = results[version]["A"]["illustrative_nav"]

    print("illustrative_B_minus_A_usd:", round(
        results[version]["B"]["illustrative_nav"] - a, 2
    ))
    print("illustrative_C_minus_A_usd:", round(
        results[version]["C"]["illustrative_nav"] - a, 2
    ))

report = {
    "schema": "CASH_INTEREST_SCENARIOS_V1",
    "status": "PASS",
    "results": results,
    "limitations": [
        "Not an integrated backtest.",
        "Interest does not affect future buying power.",
        "No compounding or interest-on-interest.",
        "First study day not accrued.",
        "3 percent is a hypothetical cash rate.",
        "Unverified dividend payments remain unresolved."
    ]
}

out = ROOT / "p3_cash_interest_scenarios.json"
out.write_text(json.dumps(report, indent=2) + "\n")

print("\nSTATUS: PASS")
print("REPORT:", out)
