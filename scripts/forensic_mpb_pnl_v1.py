"""Independent V5-U Policy A security-level P&L reconstruction."""

import csv
import json
import math
import sys
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

sys.path.insert(0, str(ROOT / "src"))
from portfolio.provider_actions import (
    index_actions,
    checked_dividend_amount,
)

def read(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))

summary = json.loads(
    (AUDIT / "p3_lifecycle_v5u_A_summary.json").read_text()
)
audit = json.loads(
    (AUDIT / "p3_lifecycle_v5u_A_independent_audit.json").read_text()
)

if summary["status"] != "PASS" or audit["status"] != "PASS":
    raise RuntimeError("BASELINE_NOT_AUDITED")

daily = read(AUDIT / "p3_lifecycle_v5u_A_daily.csv")
trades = read(AUDIT / "p3_lifecycle_v5u_A_trades.csv")

if len(daily) != 282 or len(trades) != 313:
    raise RuntimeError("UNEXPECTED_BASELINE_LENGTH")

by_day = defaultdict(list)
for trade in trades:
    by_day[trade["date"]].append(trade)

actions = index_actions(BUNDLE / "manifest.json")
prices = {}

def px(ticker, day, field="Close", kind="raw"):
    key = (ticker, kind)
    if key not in prices:
        prices[key] = {
            r["Date"]: r
            for r in read(BUNDLE / kind / f"{ticker}.csv")
        }
    return float(prices[key][day][field])

def dividend(ticker, previous_day, day):
    prior_factor = (
        px(ticker, previous_day, kind="adjusted")
        / px(ticker, previous_day)
    )
    current_factor = (
        px(ticker, day, kind="adjusted")
        / px(ticker, day)
    )
    ratio = current_factor / prior_factor
    event = actions.get((ticker, day))

    if event is None:
        if abs(ratio - 1) > 1e-6:
            raise RuntimeError(
                f"UNEXPLAINED_FACTOR:{ticker}:{day}"
            )
        return 0.0

    if event["splits"] or event["other"]:
        raise RuntimeError(
            f"UNSUPPORTED_ACTION:{ticker}:{day}"
        )

    if not event["dividends"]:
        if abs(ratio - 1) > 1e-6:
            raise RuntimeError(
                f"UNEXPLAINED_EVENT:{ticker}:{day}"
            )
        return 0.0

    return float(checked_dividend_amount(
        event, px(ticker, previous_day), ratio
    ))

holdings = {}
previous_day = None
previous_nav = 1_000_000.0

ticker_pnl = defaultdict(float)
ticker_cost = defaultdict(float)
ticker_dividend = defaultdict(float)
daily_report = []
monthly_pnl = defaultdict(lambda: defaultdict(float))

for row in daily:
    day = row["date"]
    before = holdings.copy()
    pnl = defaultdict(float)
    dividends = defaultdict(float)
    costs = defaultdict(float)

    # Overnight price move for shares held before open.
    if previous_day is not None:
        for ticker, qty in before.items():
            pnl[ticker] += qty * (
                px(ticker, day, "Open")
                - px(ticker, previous_day)
            )

            entitlement = qty * dividend(
                ticker, previous_day, day
            )
            pnl[ticker] += entitlement
            dividends[ticker] += entitlement

    # Opening fills and actual assumed execution costs.
    for trade in by_day[day]:
        ticker = trade["ticker"]
        qty = int(trade["shares"])
        cost = float(trade["execution_cost"])

        pnl[ticker] -= cost
        costs[ticker] += cost

        if trade["action"] == "BUY":
            if ticker in holdings:
                raise RuntimeError("DUPLICATE_BUY")
            holdings[ticker] = qty

        elif trade["action"] == "SELL":
            if holdings.get(ticker, 0) < qty:
                raise RuntimeError("INVALID_SELL")

            holdings[ticker] -= qty
            if holdings[ticker] == 0:
                del holdings[ticker]
        else:
            raise RuntimeError("UNKNOWN_TRADE_ACTION")

    # Intraday price move for shares held after open.
    for ticker, qty in holdings.items():
        pnl[ticker] += qty * (
            px(ticker, day) - px(ticker, day, "Open")
        )

    calculated = sum(pnl.values())
    current_nav = float(row["nav"])
    observed = current_nav - previous_nav

    if not math.isclose(
        calculated, observed,
        rel_tol=0,
        abs_tol=0.05
    ):
        raise RuntimeError(
            f"DAILY_PNL_BRIDGE_FAILED:{day}:"
            f"calc={calculated:.4f}:"
            f"observed={observed:.4f}"
        )

    for ticker, value in pnl.items():
        ticker_pnl[ticker] += value
        monthly_pnl[day[:7]][ticker] += value

    for ticker, value in costs.items():
        ticker_cost[ticker] += value

    for ticker, value in dividends.items():
        ticker_dividend[ticker] += value

    daily_report.append({
        "date": day,
        "pnl_usd": round(observed, 2),
        "return_pct": round(
            100 * observed / previous_nav, 4
        ),
        "worst_tickers": [
            {"ticker": t, "pnl_usd": round(v, 2)}
            for t, v in sorted(
                pnl.items(), key=lambda x: x[1]
            )[:5]
        ],
    })

    previous_day = day
    previous_nav = current_nav

def ranked(items, reverse=False, n=12):
    return [
        {
            "ticker": ticker,
            "net_pnl_usd": round(value, 2),
        }
        for ticker, value in sorted(
            items.items(),
            key=lambda x: x[1],
            reverse=reverse
        )[:n]
    ]

worst_months = {}
for month in ("2025-12", "2026-03", "2026-08"):
    data = monthly_pnl[month]
    worst_months[month] = {
        "total_pnl_usd": round(sum(data.values()), 2),
        "worst_tickers": ranked(data, n=8),
    }

report = {
    "schema": "MPB_POLICY_A_PNL_FORENSICS_V1",
    "status": "PASS",
    "sessions_reconciled": len(daily_report),
    "terminal_nav_usd": round(previous_nav, 2),
    "net_pnl_usd": round(sum(ticker_pnl.values()), 2),
    "execution_cost_usd": round(sum(ticker_cost.values()), 2),
    "dividend_accrual_usd": round(
        sum(ticker_dividend.values()), 2
    ),
    "top_12_losing_tickers": ranked(ticker_pnl),
    "top_12_profitable_tickers": ranked(
        ticker_pnl, reverse=True
    ),
    "worst_8_days": sorted(
        daily_report,
        key=lambda x: x["return_pct"]
    )[:8],
    "selected_loss_months": worst_months,
    "limitations": [
        "Reconstructs raw-price P&L and dividend accrual.",
        "Provider actions are not independently certified.",
        "Does not establish signal correctness or causality.",
        "Not a point-in-time universe validation.",
    ],
}

out = AUDIT / "p3_v5u_A_pnl_forensics.json"
out.write_text(json.dumps(report, indent=2) + "\n")

print("=== MPB POLICY A FORENSIC PNL AUDIT ===")
for key, value in report.items():
    if key not in ("limitations", "schema"):
        print(key + ":", json.dumps(value, indent=2))
print("REPORT:", out)
