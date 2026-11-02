"""Independent 282-session A/B/C portfolio constraint audit.

Reconstructs holdings and mark-to-stop risk from fills.
Read-only; no changes to trading policies.
"""

import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path.cwd()
AUDIT = ROOT / "audit"
SOURCE = Path.home() / "FMA_Independent_Research/audit"
BUNDLE = (
    Path.home()
    / "FMA_Competition/Market_Refresh_Runs"
    / "manual_full_20261031T061137Z_432cf6e9"
    / "market_bundle"
)

sys.path.insert(0, str(ROOT / "src"))
from portfolio.provider_actions import (
    index_actions, checked_dividend_amount
)

def read(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))

signals = {
    (s["date"], s["ticker"]): s
    for s in read(
        SOURCE / "historical_signal_candidates.csv"
    )
}

actions = index_actions(BUNDLE / "manifest.json")
cache = {}

def px(ticker, day, adjusted=False):
    key = (ticker, adjusted)
    if key not in cache:
        folder = "adjusted" if adjusted else "raw"
        cache[key] = {
            r["Date"]: float(r["Close"])
            for r in read(
                BUNDLE / folder / f"{ticker}.csv"
            )
        }
    return cache[key][day]

def dividend_amount(ticker, previous, day):
    f0 = px(ticker, previous, True) / px(ticker, previous)
    f1 = px(ticker, day, True) / px(ticker, day)
    ratio = f1 / f0

    action = actions.get((ticker, day))

    if action and (action["splits"] or action["other"]):
        raise RuntimeError(
            "UNSUPPORTED_ACTION:" + ticker + ":" + day
        )

    if abs(ratio - 1) <= 1e-6:
        if action and action["dividends"]:
            raise RuntimeError(
                "EVENT_FACTOR_DISAGREEMENT:"
                + ticker + ":" + day
            )
        return 0.0

    return float(checked_dividend_amount(
        action, px(ticker, previous), ratio
    ))

results = []
common_dates = None

for policy in "ABC":
    prefix = f"p3_lifecycle_v4_{policy}"
    summary = json.loads(
        (AUDIT / f"{prefix}_summary.json").read_text()
    )
    replay = json.loads(
        (AUDIT / f"{prefix}_independent_audit.json").read_text()
    )
    daily = read(AUDIT / f"{prefix}_daily.csv")
    trades = read(AUDIT / f"{prefix}_trades.csv")

    if not (
        summary["status"] == "PASS"
        and replay["status"] == "PASS"
        and len(daily) == 282
    ):
        raise RuntimeError("INCOMPLETE_OR_UNAUDITED:" + policy)

    dates = [r["date"] for r in daily]
    if common_dates is None:
        common_dates = dates
    elif common_dates != dates:
        raise RuntimeError("POLICY_DATE_MISMATCH")

    by_day = defaultdict(list)
    for t in trades:
        by_day[t["date"]].append(t)

    holdings = {}
    previous = None
    observations = []

    for row in daily:
        day = row["date"]
        nav = float(row["nav"])
        cash = float(row["cash"])
        receivable = float(row["receivable"])
        budget = float(row["risk_budget_fraction"])

        # Ex-date changes to already-owned positions.
        if previous is not None:
            for ticker, p in holdings.items():
                amount = dividend_amount(
                    ticker, previous, day
                )
                if amount:
                    p["stop"] = max(
                        0.01, p["stop"] - amount
                    )

        # Replay executed fills, not planned orders.
        for trade in by_day[day]:
            ticker = trade["ticker"]
            qty = int(trade["shares"])

            if trade["action"] == "BUY":
                if ticker in holdings:
                    raise RuntimeError("DUPLICATE_POSITION")

                signal_day = trade["signal_date"]
                s = signals[(signal_day, ticker)]
                stop = (
                    float(s["planned_stop_adjusted"])
                    * px(ticker, signal_day)
                    / px(ticker, signal_day, True)
                )

                if previous is not None:
                    stop -= dividend_amount(
                        ticker, previous, day
                    )

                holdings[ticker] = {
                    "shares": qty,
                    "stop": max(0.01, stop),
                    "sector": s["sector"],
                }

            elif trade["action"] == "SELL":
                if (
                    ticker not in holdings
                    or holdings[ticker]["shares"] < qty
                ):
                    raise RuntimeError("INVALID_SELL")

                holdings[ticker]["shares"] -= qty
                if holdings[ticker]["shares"] == 0:
                    del holdings[ticker]
            else:
                raise RuntimeError("UNKNOWN_TRADE_ACTION")

        if len(holdings) != int(row["holdings"]):
            raise RuntimeError("HOLDING_COUNT_MISMATCH")

        sectors = defaultdict(float)
        market_value = 0.0
        risk_dollars = 0.0
        max_name = 0.0

        for ticker, p in holdings.items():
            price = px(ticker, day)
            value = p["shares"] * price

            market_value += value
            sectors[p["sector"]] += value
            max_name = max(max_name, value / nav)

            risk_dollars += p["shares"] * (
                max(0.0, price - p["stop"])
                + 0.01 * price
            )

        if not math.isclose(
            cash + receivable + market_value,
            nav, abs_tol=0.02
        ):
            raise RuntimeError(
                "NAV_RECONSTRUCTION_MISMATCH:"
                + policy + ":" + day
            )

        risk = risk_dollars / nav
        sector = max(sectors.values(), default=0) / nav

        observations.append({
            "date": day,
            "risk": risk,
            "budget": budget,
            "sector": sector,
            "max_name": max_name,
            "invested": market_value / nav,
            "holdings": len(holdings),
            "excess": max(0.0, risk - budget),
        })

        previous = day

    def count(predicate):
        return sum(predicate(r) for r in observations)

    result = {
        "policy": policy,
        "sessions": len(observations),
        "days_above_own_budget": count(
            lambda r: r["risk"] > r["budget"] + 1e-9
        ),
        "days_above_fixed_4pct": count(
            lambda r: r["risk"] > 0.04 + 1e-9
        ),
        "days_above_sector_24pct": count(
            lambda r: r["sector"] > 0.24 + 1e-9
        ),
        "days_above_position_10pct": count(
            lambda r: r["max_name"] > 0.10 + 1e-9
        ),
        "days_above_14_holdings": count(
            lambda r: r["holdings"] > 14
        ),
        "max_risk_pct": round(
            100 * max(r["risk"] for r in observations), 4
        ),
        "mean_risk_pct": round(
            100 * sum(r["risk"] for r in observations)
            / len(observations), 4
        ),
        "max_sector_pct": round(
            100 * max(r["sector"] for r in observations), 4
        ),
        "mean_invested_pct": round(
            100 * sum(r["invested"] for r in observations)
            / len(observations), 4
        ),
        "max_excess_over_own_budget_pp": round(
            100 * max(r["excess"] for r in observations), 4
        ),
        "largest_budget_breach_dates": [
            {
                "date": r["date"],
                "risk_pct": round(r["risk"] * 100, 4),
                "budget_pct": round(r["budget"] * 100, 4),
            }
            for r in sorted(
                observations,
                key=lambda r: -r["excess"]
            )[:5]
        ],
    }
    results.append(result)

report = {
    "schema": "ABC_282_CONSTRAINT_AUDIT_V1",
    "status": "PASS",
    "results": results,
    "scope": "END_OF_DAY_OBSERVATIONAL_RISK_AUDIT",
    "limitations": [
        "No pretrade order compliance validation.",
        "Stop-based risk is not initial investment loss.",
        "Unverified dividend settlement assumptions remain.",
        "Not an out-of-sample strategy test.",
    ],
}

out = AUDIT / "p3_abc_282_constraints.json"
out.write_text(json.dumps(report, indent=2) + "\n")

print("=== A/B/C 282-DAY CONSTRAINT AUDIT ===")
print(json.dumps(results, indent=2))
print("REPORT:", out)
