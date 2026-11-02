"""Attribute constraint observations across the trading day.

Independent reconstruction. Read-only; no strategy edits.
"""

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path.cwd()
AUDIT = ROOT / "audit"
BUNDLE = (
    Path.home()
    / "FMA_Competition/Market_Refresh_Runs"
    / "manual_full_20261031T061137Z_432cf6e9"
    / "market_bundle"
)
SOURCE = Path.home() / "FMA_Independent_Research/audit"

def read(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))

daily = read(AUDIT / "p3_lifecycle_v2_daily.csv")
trades = read(AUDIT / "p3_lifecycle_v2_trades.csv")
constraints = read(
    AUDIT / "p3_portfolio_constraints_daily.csv"
)
signals = read(SOURCE / "historical_signal_candidates.csv")
events = json.loads(
    (ROOT / "configs/verified_cash_dividends.json").read_text()
)

assert len(daily) == len(constraints) == 30

signal_map = {(s["date"], s["ticker"]): s for s in signals}
trade_map = defaultdict(list)
event_map = defaultdict(list)
prices = {}

for t in trades:
    trade_map[t["date"]].append(t)
for e in events:
    event_map[e["ex_date"]].append(e)

def px(ticker, day, field="Close", adjusted=False):
    key = ticker, adjusted
    if key not in prices:
        folder = "adjusted" if adjusted else "raw"
        prices[key] = {
            r["Date"]: r
            for r in read(
                BUNDLE / folder / f"{ticker}.csv"
            )
        }
    value = float(prices[key][day][field])
    if not math.isfinite(value) or value <= 0:
        raise ValueError("INVALID_PRICE")
    return value

def metrics(holdings, cash, receivable, day, field):
    market_values = {}
    sectors = defaultdict(float)
    risk_dollars = 0.0

    for ticker, p in holdings.items():
        price = px(ticker, day, field)
        mv = p["shares"] * price
        market_values[ticker] = mv
        sectors[p["sector"]] += mv
        risk_dollars += p["shares"] * (
            max(0.0, price - p["stop"]) + 0.01 * price
        )

    nav = cash + receivable + sum(market_values.values())
    if nav <= 0:
        raise RuntimeError("NONPOSITIVE_NAV")

    return {
        "risk": risk_dollars / nav,
        "sector": max(sectors.values(), default=0) / nav,
        "nav": nav,
    }

holdings = {}
findings = []

for row, expected in zip(daily, constraints):
    day = row["date"]
    assert day == expected["date"]

    for event in event_map[day]:
        ticker = event["ticker"]
        if ticker in holdings:
            holdings[ticker]["stop"] = max(
                0.01,
                holdings[ticker]["stop"]
                - float(event["amount_per_share"])
            )

    todays_trades = trade_map[day]
    ending_cash = float(row["cash"])
    receivable = float(row["receivable"])

    # Recover pre-auction cash from recorded cash movements.
    opening_cash = ending_cash
    for t in todays_trades:
        notional = int(t["shares"]) * float(
            t["execution_price"]
        )
        opening_cash += (
            notional + 10.0 if t["action"] == "BUY"
            else -(notional - 10.0)
        )

    before = metrics(
        holdings, opening_cash, receivable, day, "Open"
    )

    for t in todays_trades:
        ticker = t["ticker"]
        quantity = int(t["shares"])

        if t["action"] == "BUY":
            assert ticker not in holdings
            signal = signal_map[
                (t["signal_date"], ticker)
            ]
            signal_day = t["signal_date"]
            stop = (
                float(signal["planned_stop_adjusted"])
                * px(ticker, signal_day)
                / px(ticker, signal_day, adjusted=True)
            )
            for event in event_map[day]:
                if event["ticker"] == ticker:
                    stop = max(
                        0.01,
                        stop - float(event["amount_per_share"])
                    )
            holdings[ticker] = {
                "shares": quantity,
                "stop": stop,
                "sector": signal["sector"],
            }
        else:
            assert holdings[ticker]["shares"] >= quantity
            holdings[ticker]["shares"] -= quantity
            if holdings[ticker]["shares"] == 0:
                del holdings[ticker]

    after = metrics(
        holdings, ending_cash, receivable, day, "Open"
    )
    closing = metrics(
        holdings, ending_cash, receivable, day, "Close"
    )

    assert math.isclose(
        closing["risk"],
        float(expected["planned_risk_fraction"]),
        abs_tol=1e-9
    ), "RISK_AUDIT_MISMATCH"

    assert math.isclose(
        closing["sector"],
        float(expected["max_sector_weight"]),
        abs_tol=1e-9
    ), "SECTOR_AUDIT_MISMATCH"

    if closing["risk"] > 0.04 or closing["sector"] > 0.24:
        reasons = []
        for dimension, threshold in (
            ("risk", 0.04), ("sector", 0.24)
        ):
            if closing[dimension] <= threshold:
                continue
            if before[dimension] > threshold:
                timing = "PRE_AUCTION_EXISTING"
            elif after[dimension] > threshold:
                timing = "AFTER_AUCTION"
            else:
                timing = "INTRADAY_CROSSING"
            reasons.append(dimension + ":" + timing)

        findings.append({
            "date": day,
            "trades": len(todays_trades),
            "risk_pre_open_pct": round(
                before["risk"] * 100, 4
            ),
            "risk_post_open_pct": round(
                after["risk"] * 100, 4
            ),
            "risk_close_pct": round(
                closing["risk"] * 100, 4
            ),
            "sector_pre_open_pct": round(
                before["sector"] * 100, 4
            ),
            "sector_post_open_pct": round(
                after["sector"] * 100, 4
            ),
            "sector_close_pct": round(
                closing["sector"] * 100, 4
            ),
            "timing": reasons,
        })

assert len(findings) == 15
assert sum(
    x["trades"] == 0 and x["risk_close_pct"] > 4
    for x in findings
) == 8

summary = {
    "schema": "CONSTRAINT_TIMING_AUDIT_V1",
    "status": "PASS",
    "sessions": len(daily),
    "exception_days": len(findings),
    "results": findings,
    "limitations": [
        "Risk assessed at three snapshots, not tick-level.",
        "Opening auction fills are simulated assumptions.",
        "Does not prove causality of individual orders.",
        "Not an official competition-rule compliance audit.",
    ]
}

report = AUDIT / "p3_constraint_timing_summary.json"
report.write_text(json.dumps(summary, indent=2) + "\n")

print("=== CONSTRAINT TIMING AUDIT ===")
for item in findings:
    print(
        item["date"],
        "| trades:", item["trades"],
        "| risk:", item["risk_pre_open_pct"],
        "->", item["risk_post_open_pct"],
        "->", item["risk_close_pct"],
        "|", ", ".join(item["timing"])
    )
print("STATUS:", summary["status"])
print("REPORT:", report)
