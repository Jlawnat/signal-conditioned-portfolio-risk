"""Independent security-level accounting attribution.

Uses executed trades and raw prices; no strategy changes.
This is an accounting bridge, not causal factor attribution.
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

FOCUS_DAYS = [
    "2025-10-24",
    "2025-10-27",
    "2025-10-28",
    "2025-10-29",
]

def read(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))

price_cache = {}

def px(ticker, date, field):
    if ticker not in price_cache:
        price_cache[ticker] = {
            r["Date"]: r
            for r in read(BUNDLE / "raw" / f"{ticker}.csv")
        }
    return float(price_cache[ticker][date][field])

events = json.loads(
    (ROOT / "configs/verified_cash_dividends.json").read_text()
)
events_by_day = defaultdict(list)
for event in events:
    events_by_day[event["ex_date"]].append(event)

security_pnl = {}
daily_nav = {}

for policy in "ABC":
    prefix = f"p3_lifecycle_v3_{policy}"

    summary = json.loads(
        (AUDIT / f"{prefix}_summary.json").read_text()
    )
    audit = json.loads(
        (AUDIT / f"{prefix}_independent_audit.json").read_text()
    )

    if (
        summary["status"] != "PASS"
        or audit["status"] != "PASS"
        or summary["sessions_completed"] != 30
    ):
        raise RuntimeError("INCOMPLETE_POLICY:" + policy)

    daily = read(AUDIT / f"{prefix}_daily.csv")
    trades = read(AUDIT / f"{prefix}_trades.csv")

    by_day = defaultdict(list)
    for trade in trades:
        by_day[trade["date"]].append(trade)

    holdings = {}
    prev_date = None
    prev_nav = 1_000_000.0

    security_pnl[policy] = {}
    daily_nav[policy] = {}

    for row in daily:
        day = row["date"]
        before = holdings.copy()
        pnl = defaultdict(float)

        # Overnight price movement on previously held shares.
        if prev_date is not None:
            for ticker, shares in before.items():
                pnl[ticker] += shares * (
                    px(ticker, day, "Open")
                    - px(ticker, prev_date, "Close")
                )
        elif before:
            raise RuntimeError("INVALID_FIRST_DAY_HOLDINGS")

        # Ex-date dividend entitlement belongs to shares
        # held before the opening execution.
        for event in events_by_day[day]:
            ticker = event["ticker"]
            shares = before.get(ticker, 0)
            pnl[ticker] += (
                shares * float(event["amount_per_share"])
            )

        # Rebuild fills and attribute transaction costs.
        for trade in by_day[day]:
            ticker = trade["ticker"]
            qty = int(trade["shares"])

            pnl[ticker] -= float(trade["execution_cost"])

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
                raise RuntimeError("UNKNOWN_ACTION")

        # Post-opening holdings earn intraday price changes.
        for ticker, shares in holdings.items():
            pnl[ticker] += shares * (
                px(ticker, day, "Close")
                - px(ticker, day, "Open")
            )

        computed = sum(pnl.values())
        observed = float(row["nav"]) - prev_nav

        if not math.isclose(
            computed, observed,
            rel_tol=0,
            abs_tol=0.02,
        ):
            raise RuntimeError(
                f"SECURITY_PNL_NAV_BRIDGE_FAILED:"
                f"{policy}:{day}:"
                f"{computed:.5f}:{observed:.5f}"
            )

        security_pnl[policy][day] = dict(pnl)
        daily_nav[policy][day] = float(row["nav"])

        prev_date = day
        prev_nav = float(row["nav"])

report = {
    "schema": "ABC_SECURITY_PNL_ATTRIBUTION_V1",
    "status": "PASS",
    "focus_dates": FOCUS_DAYS,
    "comparisons": {},
}

for policy in ("B", "C"):
    contribution = defaultdict(float)

    for day in FOCUS_DAYS:
        a = security_pnl["A"][day]
        other = security_pnl[policy][day]

        for ticker in set(a) | set(other):
            contribution[ticker] += (
                other.get(ticker, 0.0)
                - a.get(ticker, 0.0)
            )

    expected = sum(
        (daily_nav[policy][day] -
         daily_nav[policy][
             list(daily_nav[policy]).index(day) - 1
         ] if False else 0)
        for day in []
    )

    # Use the independently bridged security contributions.
    focus_difference = sum(contribution.values())

    # Cross-check against NAV P&L differences on focus dates.
    dates = list(daily_nav[policy])
    nav_difference = 0.0
    for day in FOCUS_DAYS:
        i = dates.index(day)
        if i == 0:
            raise RuntimeError("INVALID_FOCUS_START")
        prev_day = dates[i - 1]
        nav_difference += (
            daily_nav[policy][day]
            - daily_nav[policy][prev_day]
            - daily_nav["A"][day]
            + daily_nav["A"][prev_day]
        )

    if not math.isclose(
        focus_difference, nav_difference,
        abs_tol=0.10,
    ):
        raise RuntimeError("PAIR_ATTRIBUTION_BRIDGE_FAILED")

    ranked = sorted(
        contribution.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    report["comparisons"][f"{policy}_minus_A"] = {
        "focus_nav_advantage_usd": round(
            focus_difference, 2
        ),
        "top_positive_tickers": [
            {"ticker": t, "usd": round(v, 2)}
            for t, v in ranked[:8]
        ],
        "top_negative_tickers": [
            {"ticker": t, "usd": round(v, 2)}
            for t, v in ranked[-8:]
        ],
    }

report["limitations"] = [
    "Security-level arithmetic P&L decomposition.",
    "Not causal identification of the risk overlay.",
    "Includes execution cost and accrued dividends.",
    "Different policies follow different holding paths.",
    "Short, previously inspected historical period.",
]

out = AUDIT / "p3_abc_security_pnl_attribution.json"
out.write_text(json.dumps(report, indent=2) + "\n")

print("=== A/B/C SECURITY PNL ATTRIBUTION ===")
print(json.dumps(report, indent=2))
print("REPORT:", out)
