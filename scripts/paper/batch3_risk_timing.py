"""Reconstruct selected V5-U breach transitions from stored fills; no simulation."""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "audit"
SOURCE = Path.home() / "FMA_Independent_Research/audit"
BUNDLE = (Path.home() / "FMA_Competition/Market_Refresh_Runs"
          / "manual_full_20261031T061137Z_432cf6e9/market_bundle")
sys.path.insert(0, str(ROOT / "src"))
from portfolio.provider_actions import index_actions, checked_dividend_amount  # noqa: E402


def rows(path):
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


signals = {(r["date"], r["ticker"]): r for r in rows(SOURCE / "historical_signal_candidates.csv")}
actions = index_actions(BUNDLE / "manifest.json")
cache = {}


def px(ticker, day, field="Close", adjusted=False):
    key = (ticker, adjusted)
    if key not in cache:
        folder = "adjusted" if adjusted else "raw"
        cache[key] = {r["Date"]: r for r in rows(BUNDLE / folder / f"{ticker}.csv")}
    return float(cache[key][day][field])


def dividend(ticker, previous, day):
    ratio = (px(ticker, day, adjusted=True) / px(ticker, day)) / (px(ticker, previous, adjusted=True) / px(ticker, previous))
    if abs(ratio - 1) <= 1e-6:
        return 0.0
    return float(checked_dividend_amount(actions.get((ticker, day)), px(ticker, previous), ratio))


def risk_dollars(holdings, day, field="Close"):
    return sum(p["shares"] * (max(0, px(t, day, field) - p["stop"]) + 0.01 * px(t, day, field))
               for t, p in holdings.items())


constraint = {r["policy"]: r for r in json.loads((AUDIT / "p3_abc_v5u_282_constraints.json").read_text())["results"]}
out = {}
for policy in "ABC":
    daily = rows(AUDIT / f"p3_lifecycle_v5u_{policy}_daily.csv")
    trades = rows(AUDIT / f"p3_lifecycle_v5u_{policy}_trades.csv")
    by_date = defaultdict(list)
    for trade in trades:
        by_date[trade["date"]].append(trade)
    selected = {r["date"] for r in constraint[policy]["largest_budget_breach_dates"][:3]}
    holdings = {}
    observations = []
    waiting = defaultdict(list)
    for index, row in enumerate(daily):
        date = row["date"]
        previous = daily[index - 1]["date"] if index else None
        if previous:
            for ticker, position in holdings.items():
                position["stop"] = max(0.01, position["stop"] - dividend(ticker, previous, date))
        for trade in by_date[date]:
            ticker, qty = trade["ticker"], int(trade["shares"])
            if trade["action"] == "BUY":
                s = signals[(trade["signal_date"], ticker)]
                sd = trade["signal_date"]
                stop = float(s["planned_stop_adjusted"]) * px(ticker, sd) / px(ticker, sd, adjusted=True)
                if previous:
                    stop -= dividend(ticker, previous, date)
                holdings[ticker] = {"shares": qty, "stop": max(0.01, stop)}
            else:
                holdings[ticker]["shares"] -= qty
                if holdings[ticker]["shares"] == 0:
                    del holdings[ticker]
        for item in waiting[date]:
            opening_nav = (float(row["cash"]) + float(row["receivable"])
                           + sum(p["shares"] * px(t, date, "Open") for t, p in holdings.items()))
            item["next_open_after_actual_fills_risk_pct"] = 100 * risk_dollars(holdings, date, "Open") / opening_nav
            item["next_close_risk_pct"] = 100 * risk_dollars(holdings, date) / float(row["nav"])
        if date not in selected or index + 1 == len(daily):
            continue
        next_row = daily[index + 1]
        next_date = next_row["date"]
        nav = float(row["nav"])
        before = 100 * risk_dollars(holdings, date) / nav
        planned_sells = [t for t in by_date[next_date] if t["action"] == "SELL" and t["signal_date"] == date]
        remaining = {t: p.copy() for t, p in holdings.items()}
        for sell in planned_sells:
            remaining[sell["ticker"]]["shares"] -= int(sell["shares"])
            if remaining[sell["ticker"]]["shares"] == 0:
                del remaining[sell["ticker"]]
        after_plan = 100 * risk_dollars(remaining, date) / nav
        item = {"date": date, "budget_pct": 100 * float(row["risk_budget_fraction"]),
                             "close_before_plan_risk_pct": before,
                             "hypothetical_close_after_next_day_executed_sells_pct": after_plan,
                             "next_date": next_date,
                             "next_open_sell_count": len(planned_sells),
                             "next_open_sell_reasons": [s["reason"] for s in planned_sells],
                             "next_close_risk_pct": None}
        observations.append(item)
        waiting[next_date].append(item)
    out[policy] = observations

path = ROOT / "paper/tables/v2/risk_timing_sample.json"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
