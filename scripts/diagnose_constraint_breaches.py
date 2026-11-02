"""Investigate end-of-day constraint exceptions.

Read-only diagnostic; does not change strategy or ledger.
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
SOURCE = Path.home() / "FMA_Independent_Research/audit"
BUNDLE = (
    Path.home() / "FMA_Competition/Market_Refresh_Runs"
    / "manual_full_20261031T061137Z_432cf6e9"
    / "market_bundle"
)

def read(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))

daily = read(AUDIT / "p3_portfolio_constraints_daily.csv")
trades = read(AUDIT / "p3_lifecycle_v2_trades.csv")
signals = read(SOURCE / "historical_signal_candidates.csv")
events = json.loads(
    (ROOT / "configs/verified_cash_dividends.json").read_text()
)

signal_map = {
    (s["date"], s["ticker"]): s for s in signals
}
trades_by_day = defaultdict(list)
events_by_day = defaultdict(list)

for t in trades:
    trades_by_day[t["date"]].append(t)

for e in events:
    events_by_day[e["ex_date"]].append(e)

prices = {}
def close(ticker, date, adjusted=False):
    key = (ticker, adjusted)
    if key not in prices:
        folder = "adjusted" if adjusted else "raw"
        prices[key] = {
            r["Date"]: float(r["Close"])
            for r in read(BUNDLE / folder / f"{ticker}.csv")
        }
    return prices[key][date]

holdings = {}
results = []

for row in daily:
    day = row["date"]
    nav = float(
        next(r["nav"] for r in read(
            AUDIT / "p3_lifecycle_v2_daily.csv"
        ) if r["date"] == day)
    )

    for event in events_by_day[day]:
        ticker = event["ticker"]
        if ticker in holdings:
            holdings[ticker]["stop"] = max(
                0.01,
                holdings[ticker]["stop"]
                - float(event["amount_per_share"])
            )

    todays_trades = trades_by_day[day]

    for trade in todays_trades:
        ticker = trade["ticker"]
        qty = int(trade["shares"])

        if trade["action"] == "BUY":
            signal = signal_map[
                (trade["signal_date"], ticker)
            ]
            t = trade["signal_date"]
            stop = (
                float(signal["planned_stop_adjusted"])
                * close(ticker, t)
                / close(ticker, t, adjusted=True)
            )

            for event in events_by_day[day]:
                if event["ticker"] == ticker:
                    stop = max(
                        0.01,
                        stop - float(event["amount_per_share"])
                    )

            holdings[ticker] = {
                "shares": qty,
                "sector": signal["sector"],
                "stop": stop,
            }
        else:
            holdings[ticker]["shares"] -= qty
            if holdings[ticker]["shares"] == 0:
                del holdings[ticker]

    risk = {}
    sectors = defaultdict(float)
    sector_members = defaultdict(list)

    for ticker, p in holdings.items():
        price = close(ticker, day)
        market_value = p["shares"] * price
        sectors[p["sector"]] += market_value / nav
        sector_members[p["sector"]].append(ticker)

        risk[ticker] = (
            p["shares"] * (
                max(0, price - p["stop"])
                + 0.01 * price
            ) / nav
        )

    risk_total = sum(risk.values())
    top_sector, top_sector_weight = max(
        sectors.items(), key=lambda x: x[1],
        default=("NONE", 0)
    )

    assert abs(
        risk_total - float(row["planned_risk_fraction"])
    ) < 1e-8, "RISK_RECONSTRUCTION_MISMATCH"

    assert abs(
        top_sector_weight - float(row["max_sector_weight"])
    ) < 1e-8, "SECTOR_RECONSTRUCTION_MISMATCH"

    if risk_total > 0.04 or top_sector_weight > 0.24:
        results.append({
            "date": day,
            "risk_pct": round(100 * risk_total, 4),
            "sector": top_sector,
            "sector_pct": round(
                100 * top_sector_weight, 4
            ),
            "sector_members": sorted(
                sector_members[top_sector]
            ),
            "top_risk_contributors": [
                {
                    "ticker": t,
                    "risk_pct_nav": round(100 * v, 4)
                }
                for t, v in sorted(
                    risk.items(),
                    key=lambda x: -x[1]
                )[:5]
            ],
            "trades_today": [
                t["action"] + " " + t["ticker"]
                for t in todays_trades
            ],
        })

summary = {
    "schema": "CONSTRAINT_BREACH_DIAGNOSTIC_V1",
    "status": "DIAGNOSTIC_COMPLETE",
    "breach_days": len(results),
    "details": results,
    "caveat": (
        "End-of-day contribution analysis. Does not "
        "establish whether a breach arose at order "
        "planning, at execution, or from market drift."
    )
}

output = AUDIT / "p3_constraint_breach_diagnostic.json"
output.write_text(json.dumps(summary, indent=2) + "\n")

print("=== CONSTRAINT BREACH DIAGNOSTIC ===")
print(json.dumps(summary, indent=2))
print("Report:", output)
