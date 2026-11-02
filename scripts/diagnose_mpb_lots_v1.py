"""Independent Policy A trade-lifecycle quality diagnostic."""

import csv
import json
import statistics
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
BUNDLE = (
    Path.home()
    / "FMA_Competition/Market_Refresh_Runs"
    / "manual_full_20261031T061137Z_432cf6e9"
    / "market_bundle"
)
FEE = 10.0

def read_csv(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))

trades = read_csv(
    AUDIT / "p3_lifecycle_v5u_A_trades.csv"
)
daily = read_csv(
    AUDIT / "p3_lifecycle_v5u_A_daily.csv"
)
forensics = json.loads(
    (AUDIT / "p3_v5u_A_pnl_forensics.json").read_text()
)

assert len(trades) == 313
assert len(daily) == 282
assert forensics["status"] == "PASS"

active = {}
lots = []
exit_reasons = Counter()

for t in trades:
    ticker = t["ticker"]
    side = t["action"]
    q = int(t["shares"])
    px = float(t["execution_price"])
    cost = float(t["execution_cost"])
    day = t["date"]

    if q <= 0 or px <= 0 or cost < FEE:
        raise RuntimeError("INVALID_FILL")

    if side == "BUY":
        if ticker in active:
            raise RuntimeError("UNSUPPORTED_TOPUP")

        lot = {
            "ticker": ticker,
            "entry_date": day,
            "entry_price": px,
            "original_qty": q,
            "remaining": q,
            "realized_net": 0.0,
            "exit_date": None,
            "sell_reasons": [],
        }
        lots.append(lot)
        active[ticker] = lot

    elif side == "SELL":
        lot = active.get(ticker)
        if lot is None or q > lot["remaining"]:
            raise RuntimeError(
                f"INVALID_SELL:{ticker}:{day}"
            )

        entry_fee_alloc = (
            FEE * q / lot["original_qty"]
        )

        # Prices already include adverse slippage.
        # Subtract commission only, not execution_cost.
        realized = (
            q * (px - lot["entry_price"])
            - FEE - entry_fee_alloc
        )

        lot["realized_net"] += realized
        lot["remaining"] -= q
        lot["exit_date"] = day
        lot["sell_reasons"].append(t["reason"])
        exit_reasons[t["reason"]] += 1

        if lot["remaining"] == 0:
            del active[ticker]
    else:
        raise RuntimeError("UNKNOWN_ACTION")

def final_close(ticker, day):
    path = BUNDLE / "raw" / f"{ticker}.csv"
    for r in read_csv(path):
        if r["Date"] == day:
            return float(r["Close"])
    raise RuntimeError(f"MISSING_FINAL_PRICE:{ticker}")

last_day = daily[-1]["date"]

for lot in lots:
    q = lot["remaining"]
    lot["unrealized_net"] = 0.0

    if q:
        mark = final_close(lot["ticker"], last_day)
        residual_fee = FEE * q / lot["original_qty"]
        lot["unrealized_net"] = (
            q * (mark - lot["entry_price"])
            - residual_fee
        )

    lot["total_net"] = (
        lot["realized_net"] + lot["unrealized_net"]
    )

completed = [
    x for x in lots if x["remaining"] == 0
]
open_lots = [
    x for x in lots if x["remaining"] > 0
]

wins = [
    x for x in completed if x["total_net"] > 0
]
losses = [
    x for x in completed if x["total_net"] < 0
]

gross_profit = sum(x["total_net"] for x in wins)
gross_loss = -sum(x["total_net"] for x in losses)

holding_days = [
    (
        date.fromisoformat(x["exit_date"])
        - date.fromisoformat(x["entry_date"])
    ).days
    for x in completed
]

trade_pnl = sum(x["total_net"] for x in lots)
dividends = float(
    forensics["dividend_accrual_usd"]
)
reconstructed_nav = (
    1_000_000 + trade_pnl + dividends
)
reported_nav = float(daily[-1]["nav"])
bridge_error = reconstructed_nav - reported_nav

if abs(bridge_error) > 0.10:
    raise RuntimeError(
        f"NAV_BRIDGE_FAILED:{bridge_error:.6f}"
    )

def preview(items, reverse=False):
    ordered = sorted(
        items,
        key=lambda x: x["total_net"],
        reverse=reverse
    )
    return [
        {
            "ticker": x["ticker"],
            "entry": x["entry_date"],
            "exit": x["exit_date"],
            "quantity": x["original_qty"],
            "net_pnl_usd": round(x["total_net"], 2),
            "reasons": x["sell_reasons"],
        }
        for x in ordered[:10]
    ]

result = {
    "schema": "MPB_TRADE_LIFECYCLE_DIAGNOSTIC_V1",
    "status": "PASS",
    "buy_entries": len(lots),
    "completed_entry_lifecycles": len(completed),
    "partially_or_fully_open_lifecycles": len(open_lots),
    "completed_winners": len(wins),
    "completed_losers": len(losses),
    "completed_win_rate_pct": round(
        len(wins) / len(completed) * 100, 3
    ) if completed else None,
    "gross_winning_pnl_usd": round(gross_profit, 2),
    "gross_losing_pnl_usd": round(gross_loss, 2),
    "profit_factor_completed": round(
        gross_profit / gross_loss, 4
    ) if gross_loss else None,
    "avg_completed_win_usd": round(
        gross_profit / len(wins), 2
    ) if wins else None,
    "avg_completed_loss_usd": round(
        -gross_loss / len(losses), 2
    ) if losses else None,
    "median_holding_calendar_days": (
        statistics.median(holding_days)
        if holding_days else None
    ),
    "mean_holding_calendar_days": (
        round(statistics.mean(holding_days), 2)
        if holding_days else None
    ),
    "completed_net_pnl_usd": round(
        sum(x["total_net"] for x in completed), 2
    ),
    "open_lifecycles_total_pnl_usd": round(
        sum(x["total_net"] for x in open_lots), 2
    ),
    "trade_pnl_excluding_dividends_usd": round(
        trade_pnl, 2
    ),
    "dividend_accrual_usd": round(dividends, 2),
    "nav_bridge_error_usd": round(bridge_error, 4),
    "sell_order_reasons": dict(exit_reasons),
    "worst_completed_lifecycles": preview(completed),
    "best_completed_lifecycles": preview(
        completed, reverse=True
    ),
    "open_lifecycles": preview(open_lots),
    "limitations": [
        "Completed win rate excludes open lifecycles.",
        "Slippage is embedded in execution prices.",
        "Only $10 commissions are deducted separately.",
        "Dividends are reconciled at portfolio level.",
        "No claim of point-in-time or signal parity.",
        "Not a causal strategy improvement test.",
    ],
}

path = AUDIT / "p3_v5u_A_trade_lifecycles.json"
path.write_text(json.dumps(result, indent=2) + "\n")

print("=== MPB TRADE LIFECYCLE QUALITY ===")
for key, value in result.items():
    if key not in ("schema", "limitations"):
        print(
            key + ":",
            json.dumps(value, indent=2)
        )
print("REPORT:", path)
