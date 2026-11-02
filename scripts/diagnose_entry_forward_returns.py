"""Fixed-horizon entry signal diagnostic.

Observational only. No strategy or exit modification.
"""

import csv
import json
import statistics
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

ROOT = Path.cwd()
AUDIT = ROOT / "audit"
BUNDLE = (
    Path.home()
    / "FMA_Competition/Market_Refresh_Runs"
    / "manual_full_20261031T061137Z_432cf6e9"
    / "market_bundle"
)

def read_csv(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))

@lru_cache(None)
def prices(ticker, kind):
    path = BUNDLE / kind / f"{ticker}.csv"
    if not path.is_file():
        raise RuntimeError(f"MISSING_PRICE_FILE:{path}")
    return {
        r["Date"]: r for r in read_csv(path)
    }

def adjusted_open(ticker, day):
    r = prices(ticker, "raw")[day]
    a = prices(ticker, "adjusted")[day]
    raw_close = float(r["Close"])
    if raw_close <= 0:
        raise RuntimeError("INVALID_PRICE")
    return (
        float(r["Open"])
        * float(a["Close"]) / raw_close
    )

def adjusted_close(ticker, day):
    return float(prices(ticker, "adjusted")[day]["Close"])

trades = read_csv(
    AUDIT / "p3_lifecycle_v5u_A_trades.csv"
)
daily = read_csv(
    AUDIT / "p3_lifecycle_v5u_A_daily.csv"
)

dates = [r["date"] for r in daily]
date_index = {d: i for i, d in enumerate(dates)}
assert len(dates) == len(date_index) == 282

entries = [r for r in trades if r["action"] == "BUY"]
assert len(entries) == 158

horizons = (1, 5, 10, 20)
groups = defaultdict(list)
censored = defaultdict(int)

for t in entries:
    ticker = t["ticker"]
    setup = t["reason"]
    start = t["date"]
    i = date_index[start]

    for h in horizons:
        end_idx = i + h - 1

        if end_idx >= len(dates):
            censored[h] += 1
            continue

        end = dates[end_idx]

        try:
            stock_start = adjusted_open(ticker, start)
            stock_end = adjusted_close(ticker, end)
            spy_start = adjusted_open("SPY", start)
            spy_end = adjusted_close("SPY", end)
        except KeyError as exc:
            raise RuntimeError(
                f"MISSING_REQUIRED_SESSION:"
                f"{ticker}:{start}:{end}"
            ) from exc

        if min(
            stock_start, stock_end, spy_start, spy_end
        ) <= 0:
            raise RuntimeError("INVALID_NONPOSITIVE_PRICE")

        stock_return = 100 * (
            stock_end / stock_start - 1
        )
        spy_return = 100 * (
            spy_end / spy_start - 1
        )

        record = {
            "stock": stock_return,
            "spy": spy_return,
            "excess": stock_return - spy_return,
        }

        groups[("ALL", h)].append(record)
        groups[(setup, h)].append(record)

def summary(rows):
    return {
        "observations": len(rows),
        "mean_stock_return_pct": round(
            statistics.mean(x["stock"] for x in rows), 4
        ),
        "median_stock_return_pct": round(
            statistics.median(x["stock"] for x in rows), 4
        ),
        "positive_stock_rate_pct": round(
            100 * sum(x["stock"] > 0 for x in rows)
            / len(rows), 2
        ),
        "mean_spy_return_pct": round(
            statistics.mean(x["spy"] for x in rows), 4
        ),
        "mean_stock_minus_spy_pp": round(
            statistics.mean(x["excess"] for x in rows), 4
        ),
        "beat_spy_rate_pct": round(
            100 * sum(x["excess"] > 0 for x in rows)
            / len(rows), 2
        ),
    }

result = {
    "schema": "MPB_ENTRY_FORWARD_RETURNS_V1",
    "status": "PASS",
    "entry_count": len(entries),
    "horizon_definition": (
        "Entry-session adjusted open to adjusted close "
        "on the H-th trading session, including entry day"
    ),
    "results": {},
    "censored_near_end": dict(censored),
    "limitations": [
        "Not a trading strategy backtest.",
        "No exits, commissions, or slippage.",
        "Equal weight per entry event, not portfolio weight.",
        "Adjusted prices depend on provider quality.",
        "Current-universe survivorship bias remains.",
        "Overlapping observations are dependent.",
        "Historical inspection; not an OOS test.",
    ],
}

print("=== MPB ENTRY FORWARD RETURN DIAGNOSTIC ===")

for setup in ("ALL", "breakout", "pullback_reclaim"):
    print("\nSETUP:", setup)
    result["results"][setup] = {}

    for h in horizons:
        rows = groups[(setup, h)]

        if not rows:
            print(h, "sessions: NO_OBSERVATIONS")
            continue

        s = summary(rows)
        result["results"][setup][str(h)] = s

        print(
            f"{h:>2} sessions | n={s['observations']:>3} "
            f"| stock={s['mean_stock_return_pct']:+.3f}% "
            f"| SPY={s['mean_spy_return_pct']:+.3f}% "
            f"| excess={s['mean_stock_minus_spy_pp']:+.3f}pp "
            f"| positive={s['positive_stock_rate_pct']:.1f}% "
            f"| beat_SPY={s['beat_spy_rate_pct']:.1f}%"
        )

out = AUDIT / "p3_A_entry_forward_returns.json"
out.write_text(json.dumps(result, indent=2) + "\n")

print("\nCENSORED_NEAR_STUDY_END:", dict(censored))
print("STATUS: PASS")
print("REPORT:", out)
