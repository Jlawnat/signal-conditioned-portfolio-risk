"""Independent end-of-day portfolio constraint audit.

Uses previously generated execution records.
Reports observed limits; does not assert strategy performance.
"""

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
SOURCE = Path.home() / "FMA_Independent_Research/audit"
BUNDLE = (
    Path.home()
    / "FMA_Competition/Market_Refresh_Runs"
    / "manual_full_20261031T061137Z_432cf6e9"
    / "market_bundle"
)

POSITION_LIMIT = 0.10
SECTOR_LIMIT = 0.24
RISK_BUDGET = 0.04
MAX_HOLDINGS = 14
MAX_TRANSACTIONS = 400
GAP_BUFFER = 0.01

def read_csv(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))

daily_path = AUDIT / "p3_lifecycle_v2_daily.csv"
trades_path = AUDIT / "p3_lifecycle_v2_trades.csv"
signal_path = SOURCE / "historical_signal_candidates.csv"

daily = read_csv(daily_path)
trades = read_csv(trades_path)
signals = read_csv(signal_path)

assert daily and trades and signals

signal_lookup = {}
for s in signals:
    key = (s["date"], s["ticker"])
    if key in signal_lookup:
        raise RuntimeError("DUPLICATE_SIGNAL")
    signal_lookup[key] = s

by_day = defaultdict(list)
for trade in trades:
    by_day[trade["date"]].append(trade)

events = json.loads(
    (ROOT / "configs/verified_cash_dividends.json").read_text()
)
events_by_ex_date = defaultdict(list)
for event in events:
    events_by_ex_date[event["ex_date"]].append(event)

price_cache = {}

def price(ticker, day, adjusted=False):
    key = (ticker, adjusted)
    if key not in price_cache:
        folder = "adjusted" if adjusted else "raw"
        file = BUNDLE / folder / f"{ticker}.csv"
        price_cache[key] = {
            r["Date"]: r for r in read_csv(file)
        }
    return float(price_cache[key][day]["Close"])

positions = {}
observations = []

for row in daily:
    day = row["date"]
    nav = float(row["nav"])

    assert nav > 0

    # Adjust stops for previously held shares on ex-date.
    for event in events_by_ex_date.get(day, []):
        ticker = event["ticker"]
        if ticker in positions:
            positions[ticker]["stop"] = max(
                0.01,
                positions[ticker]["stop"]
                - float(event["amount_per_share"])
            )

    # Reconstruct actual filled shares.
    for trade in by_day.get(day, []):
        ticker = trade["ticker"]
        qty = int(trade["shares"])
        action = trade["action"]

        if action == "BUY":
            assert ticker not in positions

            key = (trade["signal_date"], ticker)
            if key not in signal_lookup:
                raise RuntimeError(
                    "BUY_WITHOUT_VERIFIED_ENTRY_SIGNAL:"
                    + str(key)
                )

            signal = signal_lookup[key]
            t = trade["signal_date"]

            stop = (
                float(signal["planned_stop_adjusted"])
                * price(ticker, t)
                / price(ticker, t, adjusted=True)
            )

            # If the opening fill occurred on an ex-date,
            # convert the prior day's stop to ex-date units.
            for event in events_by_ex_date.get(day, []):
                if event["ticker"] == ticker:
                    stop = max(
                        0.01,
                        stop - float(event["amount_per_share"])
                    )

            positions[ticker] = {
                "shares": qty,
                "stop": stop,
                "sector": signal["sector"],
            }

        elif action == "SELL":
            assert ticker in positions
            assert positions[ticker]["shares"] >= qty
            positions[ticker]["shares"] -= qty

            if positions[ticker]["shares"] == 0:
                del positions[ticker]
        else:
            raise RuntimeError("UNKNOWN_TRADE_ACTION")

    assert len(positions) == int(row["holdings"]), (
        "HOLDING_RECONSTRUCTION_MISMATCH"
    )

    sector_values = defaultdict(float)
    name_weights = {}
    planned_risk_dollars = 0.0

    for ticker, p in positions.items():
        close = price(ticker, day)
        market_value = p["shares"] * close

        name_weights[ticker] = market_value / nav
        sector_values[p["sector"]] += market_value

        planned_risk_dollars += p["shares"] * (
            max(0.0, close - p["stop"])
            + GAP_BUFFER * close
        )

    sector_weights = {
        k: v / nav for k, v in sector_values.items()
    }

    max_name = max(name_weights.values(), default=0)
    max_sector = max(sector_weights.values(), default=0)
    risk_fraction = planned_risk_dollars / nav

    observations.append({
        "date": day,
        "holdings": len(positions),
        "transaction_count": sum(
            t["date"] <= day for t in trades
        ),
        "cash_fraction": float(row["cash"]) / nav,
        "max_position_weight": max_name,
        "max_sector_weight": max_sector,
        "planned_risk_fraction": risk_fraction,
        "position_limit_exceeded": max_name > POSITION_LIMIT + 1e-9,
        "sector_limit_exceeded": max_sector > SECTOR_LIMIT + 1e-9,
        "risk_budget_exceeded": risk_fraction > RISK_BUDGET + 1e-9,
        "holding_count_exceeded": len(positions) > MAX_HOLDINGS,
    })

out = AUDIT / "p3_portfolio_constraints_daily.csv"

with out.open("w", newline="") as f:
    writer = csv.DictWriter(
        f, fieldnames=list(observations[0])
    )
    writer.writeheader()
    writer.writerows(observations)

summary = {
    "schema": "FMA_PORTFOLIO_CONSTRAINT_AUDIT_V1",
    "sessions_audited": len(observations),
    "trades_audited": len(trades),
    "maximum_position_weight": max(
        x["max_position_weight"] for x in observations
    ),
    "maximum_sector_weight": max(
        x["max_sector_weight"] for x in observations
    ),
    "maximum_planned_risk_fraction": max(
        x["planned_risk_fraction"] for x in observations
    ),
    "days_above_position_limit": sum(
        x["position_limit_exceeded"] for x in observations
    ),
    "days_above_sector_limit": sum(
        x["sector_limit_exceeded"] for x in observations
    ),
    "days_above_risk_budget": sum(
        x["risk_budget_exceeded"] for x in observations
    ),
    "days_above_holding_limit": sum(
        x["holding_count_exceeded"] for x in observations
    ),
    "transaction_count_exceeds_400": len(trades) > MAX_TRANSACTIONS,
    "source_sha256": {
        "daily": hashlib.sha256(
            daily_path.read_bytes()
        ).hexdigest(),
        "trades": hashlib.sha256(
            trades_path.read_bytes()
        ).hexdigest(),
        "signals": hashlib.sha256(
            signal_path.read_bytes()
        ).hexdigest(),
    },
    "limitations": [
        "End-of-day observations, not pretrade validation.",
        "Risk budget uses original incumbent stop-risk convention.",
        "Price drift may cause ex-post risk target exceedances.",
        "Sector mapping is reconstructed from signal metadata.",
        "Does not verify full execution or optimizer feasibility.",
        "No supplemental allocation or dynamic risk budget.",
        "Not an investment performance study.",
    ],
}

needs_review = (
    summary["days_above_position_limit"] > 0
    or summary["days_above_sector_limit"] > 0
    or summary["days_above_risk_budget"] > 0
    or summary["days_above_holding_limit"] > 0
    or summary["transaction_count_exceeds_400"]
)

summary["status"] = (
    "REVIEW_REQUIRED" if needs_review else "PASS"
)

report = AUDIT / "p3_portfolio_constraints_summary.json"
report.write_text(json.dumps(summary, indent=2) + "\n")

print("=== PORTFOLIO CONSTRAINT AUDIT ===")
print(json.dumps(summary, indent=2))
print("Daily diagnostics:", out)
