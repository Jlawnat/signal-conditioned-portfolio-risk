"""Read-only, full-history exploratory policy comparison."""

import csv
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
INITIAL_NAV = 1_000_000.0

def load_json(path):
    return json.loads(path.read_text())

def load_csv(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

results = []
source_hashes = {}
common_dates = None
daily_nav = {}

for policy in "ABC":
    prefix = f"p3_lifecycle_v4_{policy}"

    paths = {
        "summary": AUDIT / f"{prefix}_summary.json",
        "audit": AUDIT / f"{prefix}_independent_audit.json",
        "daily": AUDIT / f"{prefix}_daily.csv",
        "trades": AUDIT / f"{prefix}_trades.csv",
    }

    summary = load_json(paths["summary"])
    replay = load_json(paths["audit"])
    daily = load_csv(paths["daily"])
    trades = load_csv(paths["trades"])

    if not (
        summary["status"] == "PASS"
        and summary["sessions_completed"] == 282
        and summary["sessions_requested"] == 282
        and replay["status"] == "PASS"
        and replay["sessions_replayed"] == 282
        and replay["trades_replayed"] == len(trades)
        and len(daily) == 282
    ):
        raise RuntimeError(f"UNVERIFIED_RUN:{policy}")

    dates = [r["date"] for r in daily]
    if len(set(dates)) != 282 or dates != sorted(dates):
        raise RuntimeError("INVALID_SESSION_CALENDAR")

    if common_dates is None:
        common_dates = dates
    elif dates != common_dates:
        raise RuntimeError("POLICY_CALENDAR_MISMATCH")

    nav = [float(r["nav"]) for r in daily]
    cash = [float(r["cash"]) for r in daily]
    receivable = [float(r["receivable"]) for r in daily]
    budgets = [
        float(r["risk_budget_fraction"])
        for r in daily
    ]

    if not all(
        math.isfinite(v) and v > 0 for v in nav
    ):
        raise RuntimeError("INVALID_NAV")

    if any(
        c < -1e-6 or a < -1e-6 or c + a > v + 0.01
        for c, a, v in zip(cash, receivable, nav)
    ):
        raise RuntimeError("INVALID_ACCOUNT_COMPONENTS")

    previous_nav = [INITIAL_NAV] + nav[:-1]

    returns = [
        v / prior - 1
        for v, prior in zip(nav, previous_nav)
    ]

    running_peak = INITIAL_NAV
    maximum_drawdown = 0.0

    for value in nav:
        running_peak = max(running_peak, value)
        maximum_drawdown = max(
            maximum_drawdown, 1 - value / running_peak
        )

    daily_vol = statistics.stdev(returns)

    annualized_volatility = daily_vol * math.sqrt(252)

    # Descriptive Sharpe with a zero risk-free return.
    # Not a test of statistical significance.
    sharpe_zero_rf = (
        statistics.mean(returns) / daily_vol
        * math.sqrt(252)
        if daily_vol > 0 else None
    )

    invested = [
        (v - c - a) / v
        for v, c, a in zip(nav, cash, receivable)
    ]

    costs = sum(
        float(t["execution_cost"]) for t in trades
    )

    counts = Counter(t["action"] for t in trades)

    if (
        counts["BUY"] != summary["simulated_buys"]
        or counts["SELL"] != summary["simulated_sells"]
    ):
        raise RuntimeError("TRADE_COUNT_MISMATCH")

    daily_nav[policy] = nav

    results.append({
        "policy": policy,
        "sessions": len(daily),
        "ending_nav_usd": round(nav[-1], 2),
        "total_return_pct": round(
            100 * (nav[-1] / INITIAL_NAV - 1), 4
        ),
        "annualized_volatility_pct": round(
            100 * annualized_volatility, 4
        ),
        "sharpe_zero_risk_free": (
            round(sharpe_zero_rf, 4)
            if sharpe_zero_rf is not None else None
        ),
        "max_drawdown_pct": round(
            100 * maximum_drawdown, 4
        ),
        "mean_invested_pct": round(
            100 * statistics.mean(invested), 4
        ),
        "mean_cash_pct": round(
            100 * statistics.mean(
                c / v for c, v in zip(cash, nav)
            ), 4
        ),
        "mean_budget_pct": round(
            100 * statistics.mean(budgets), 4
        ),
        "execution_cost_usd": round(costs, 2),
        "buys": counts["BUY"],
        "sells": counts["SELL"],
        "provisional_events": summary[
            "provisional_event_count"
        ],
        "provisional_unpaid_receivable_usd": float(
            summary["provisional_unpaid_receivable"]
        ),
        "transactions_over_360": len(trades) > 360,
        "accounting_audit": "PASS",
    })

    source_hashes[policy] = {
        key: sha256(path) for key, path in paths.items()
    }

report = {
    "schema": "ABC_FULL_HISTORY_EXPLORATORY_V1",
    "start_date": common_dates[0],
    "end_date": common_dates[-1],
    "sessions": 282,
    "results": results,
    "terminal_nav_differences_usd": {
        "B_minus_A": round(
            daily_nav["B"][-1] - daily_nav["A"][-1], 2
        ),
        "C_minus_A": round(
            daily_nav["C"][-1] - daily_nav["A"][-1], 2
        ),
        "B_minus_C": round(
            daily_nav["B"][-1] - daily_nav["C"][-1], 2
        ),
    },
    "source_sha256": source_hashes,
    "limitations": [
        "Historical simulation, not actual trading.",
        "Current-constituent universe is not point-in-time.",
        "Previously inspected exploratory sample.",
        "Unverified corporate actions and unpaid receivables.",
        "Zero risk-free rate in descriptive Sharpe.",
        "Portfolio risk and sector constraints require audit.",
        "No auxiliary allocation or independent OOS test.",
    ],
}

output = AUDIT / "p3_abc_282d_comparison.json"
output.write_text(json.dumps(report, indent=2) + "\n")

print("=== FULL-HISTORY A/B/C COMPARISON ===")
print(json.dumps({
    "period": [
        report["start_date"], report["end_date"]
    ],
    "sessions": 282,
    "results": results,
    "terminal_nav_differences_usd": report[
        "terminal_nav_differences_usd"
    ],
}, indent=2))

print("REPORT:", output)
