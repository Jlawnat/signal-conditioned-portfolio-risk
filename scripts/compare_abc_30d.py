"""Exploratory 30-session A/B/C comparison.

Rebuilds holdings and marked-stop risk from executed trades.
No strategy modification; not an out-of-sample evaluation.
"""

import csv
import json
import math
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

signals = {
    (r["date"], r["ticker"]): r
    for r in read(SOURCE / "historical_signal_candidates.csv")
}

events = json.loads(
    (ROOT / "configs/verified_cash_dividends.json").read_text()
)
actions = defaultdict(list)
for e in events:
    actions[e["ex_date"]].append(e)

prices = {}

def close(ticker, day, adjusted=False):
    key = (ticker, adjusted)
    if key not in prices:
        folder = "adjusted" if adjusted else "raw"
        prices[key] = {
            r["Date"]: float(r["Close"])
            for r in read(BUNDLE / folder / f"{ticker}.csv")
        }
    return prices[key][day]

results = []
common_dates = None

for policy in "ABC":
    prefix = f"p3_lifecycle_v3_{policy}"
    summary = json.loads(
        (AUDIT / f"{prefix}_summary.json").read_text()
    )
    replay = json.loads(
        (AUDIT / f"{prefix}_independent_audit.json").read_text()
    )

    if not (
        summary["status"] == "PASS"
        and summary["sessions_completed"] == 30
        and replay["status"] == "PASS"
        and replay["sessions_replayed"] == 30
    ):
        raise RuntimeError(f"INCOMPLETE_OR_UNAUDITED:{policy}")

    daily = read(AUDIT / f"{prefix}_daily.csv")
    trades = read(AUDIT / f"{prefix}_trades.csv")

    if len(daily) != 30:
        raise RuntimeError("UNEXPECTED_SESSION_COUNT")

    dates = [r["date"] for r in daily]
    if common_dates is None:
        common_dates = dates
    elif dates != common_dates:
        raise RuntimeError("POLICY_DATE_MISMATCH")

    by_day = defaultdict(list)
    for trade in trades:
        by_day[trade["date"]].append(trade)

    positions = {}
    maximum_drawdown = 0.0
    running_peak = 1_000_000.0
    risk_series = []
    budget_series = []
    exposure_series = []
    cash_series = []
    above_4 = 0
    above_policy = 0
    above_sector = 0
    maximum_risk_excess = 0.0

    for row in daily:
        day = row["date"]
        nav = float(row["nav"])
        cash = float(row["cash"])
        receivable = float(row["receivable"])
        budget = float(row["risk_budget_fraction"])

        for action in actions[day]:
            ticker = action["ticker"]
            if ticker in positions:
                positions[ticker]["stop"] = max(
                    0.01,
                    positions[ticker]["stop"]
                    - float(action["amount_per_share"])
                )

        for t in by_day[day]:
            ticker = t["ticker"]
            qty = int(t["shares"])

            if t["action"] == "BUY":
                if ticker in positions:
                    raise RuntimeError("DUPLICATE_POSITION")

                signal_day = t["signal_date"]
                s = signals[(signal_day, ticker)]
                stop = (
                    float(s["planned_stop_adjusted"])
                    * close(ticker, signal_day)
                    / close(ticker, signal_day, True)
                )

                for action in actions[day]:
                    if action["ticker"] == ticker:
                        stop = max(
                            0.01,
                            stop - float(action["amount_per_share"])
                        )

                positions[ticker] = {
                    "shares": qty,
                    "stop": stop,
                    "sector": s["sector"],
                }
            elif t["action"] == "SELL":
                if (
                    ticker not in positions
                    or qty > positions[ticker]["shares"]
                ):
                    raise RuntimeError("INVALID_SELL")

                positions[ticker]["shares"] -= qty
                if positions[ticker]["shares"] == 0:
                    del positions[ticker]
            else:
                raise RuntimeError("UNKNOWN_TRADE_SIDE")

        if len(positions) != int(row["holdings"]):
            raise RuntimeError("HOLDINGS_COUNT_MISMATCH")

        risk_dollars = 0.0
        market_value = 0.0
        sector_values = defaultdict(float)

        for ticker, p in positions.items():
            px = close(ticker, day)
            mv = p["shares"] * px
            market_value += mv
            sector_values[p["sector"]] += mv

            risk_dollars += p["shares"] * (
                max(0, px - p["stop"]) + 0.01 * px
            )

        if not math.isclose(
            cash + receivable + market_value,
            nav, abs_tol=0.0001
        ):
            raise RuntimeError("NAV_RECONSTRUCTION_MISMATCH")

        risk = risk_dollars / nav
        largest_sector = max(
            sector_values.values(), default=0
        ) / nav

        risk_series.append(risk)
        budget_series.append(budget)
        exposure_series.append(market_value / nav)
        cash_series.append(cash / nav)

        above_4 += risk > 0.04 + 1e-9
        above_policy += risk > budget + 1e-9
        above_sector += largest_sector > 0.24 + 1e-9
        maximum_risk_excess = max(
            maximum_risk_excess, risk - budget
        )

        running_peak = max(running_peak, nav)
        maximum_drawdown = max(
            maximum_drawdown,
            1 - nav / running_peak
        )

    results.append({
        "policy": policy,
        "sessions": len(daily),
        "buys": sum(t["action"] == "BUY" for t in trades),
        "sells": sum(t["action"] == "SELL" for t in trades),
        "overlay_fills": sum(
            "risk_budget_overlay" in t["reason"]
            for t in trades
        ),
        "ending_nav_usd": round(float(daily[-1]["nav"]), 2),
        "total_return_pct": round(
            100 * (float(daily[-1]["nav"]) / 1_000_000 - 1), 4
        ),
        "max_drawdown_pct": round(
            100 * maximum_drawdown, 4
        ),
        "mean_invested_pct": round(
            100 * sum(exposure_series) / len(daily), 4
        ),
        "mean_cash_pct": round(
            100 * sum(cash_series) / len(daily), 4
        ),
        "mean_mark_to_stop_risk_pct": round(
            100 * sum(risk_series) / len(daily), 4
        ),
        "max_mark_to_stop_risk_pct": round(
            100 * max(risk_series), 4
        ),
        "mean_policy_budget_pct": round(
            100 * sum(budget_series) / len(daily), 4
        ),
        "days_above_fixed_4pct": above_4,
        "days_above_own_policy_budget": above_policy,
        "days_above_24pct_sector": above_sector,
        "max_excess_vs_own_budget_pp": round(
            100 * maximum_risk_excess, 4
        ),
        "total_execution_cost_usd": round(
            sum(float(t["execution_cost"]) for t in trades), 2
        ),
        "accounting_audit": "PASS",
    })

output = AUDIT / "p3_abc_30d_comparison.json"
output.write_text(json.dumps({
    "schema": "EXPLORATORY_ABC_COMPARISON_V1",
    "sessions": 30,
    "results": results,
    "limitations": [
        "Short exploratory historical sample.",
        "Survivorship-biased current-constituent universe.",
        "Historical period previously inspected.",
        "Execution fills and costs are simulated.",
        "Mark-to-stop risk is not initial capital-at-risk.",
        "Results are not independent out-of-sample evidence.",
    ],
}, indent=2) + "\n")

print("=== A/B/C 30-DAY COMPARISON ===")
print(json.dumps(results, indent=2))
print("REPORT:", output)
