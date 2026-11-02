"""Historical multi-asset MPB lifecycle integration pilot.

Research software validation, not final strategy backtest.
Frozen FMA is used read-only for reference feature generation.
"""

import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE_AUDIT = Path.home() / "FMA_Independent_Research/audit"
BUNDLE = (
    Path.home()
    / "FMA_Competition/Market_Refresh_Runs"
    / "manual_full_20261031T061137Z_432cf6e9"
    / "market_bundle"
)
FMA = (
    Path.home()
    / "FMA_Competition/fma_mpb_v41_20261013"
    / "fma_mpb_v41"
)

sys.path.insert(0, str(ROOT / "src"))
from portfolio.exit_policy import ExitParameters, plan_mpb_exit
from portfolio.corporate_actions import (
    DividendLedger, load_events, factor_reconciles
)

snapshot = json.loads(
    (ROOT / "configs/mpb_exit_reference.json").read_text()
)
for filename, expected in snapshot["source_sha256"].items():
    actual = hashlib.sha256(
        (FMA / filename).read_bytes()
    ).hexdigest()
    if actual != expected:
        raise RuntimeError("FROZEN_SOURCE_HASH_MISMATCH")

sys.path.insert(0, str(FMA))
import momentum_pullback_breakout as reference
from config import CONTEST, STRAT

CFG = reference.CFG
POLICY = ExitParameters.from_json(
    ROOT / "configs/mpb_exit_reference.json"
)
EVENTS = load_events(
    ROOT / "configs/verified_cash_dividends.json"
)

START_CASH = 1_000_000.0
SLIP = STRAT.assumed_slippage_bps / 10000
FEE = float(CONTEST.commission_per_trade)
SESSIONS = int(sys.argv[1]) if len(sys.argv) > 1 else 12

assert 1 <= SESSIONS <= 282

def read_csv(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))

signals = read_csv(
    SOURCE_AUDIT / "historical_signal_candidates.csv"
)
assert len(signals) == 1229

by_day = defaultdict(list)
for s in signals:
    by_day[s["date"]].append(s)

for records in by_day.values():
    records.sort(
        key=lambda s: (-float(s["score"]), s["ticker"])
    )

cache = {}

def panel(ticker, kind):
    key = (ticker, kind)
    if key not in cache:
        path = BUNDLE / kind / f"{ticker}.csv"
        df = pd.read_csv(path, parse_dates=["Date"])
        df = df.set_index("Date").sort_index()
        if df.index.has_duplicates:
            raise RuntimeError("DUPLICATE_PANEL_DATES")
        cols = ["Open", "High", "Low", "Close", "Volume"]
        cache[key] = df[cols].astype(float)
    return cache[key]

def price(ticker, day, field="Close", kind="raw"):
    v = float(panel(ticker, kind).at[pd.Timestamp(day), field])
    if not math.isfinite(v) or v <= 0:
        raise RuntimeError("INVALID_PRICE:" + ticker + ":" + day)
    return v

def factor(ticker, day):
    return (
        price(ticker, day, kind="adjusted")
        / price(ticker, day)
    )

def features(ticker, day):
    asof = pd.Timestamp(day)

    # Physically truncate both panels to prohibit future
    # observations from entering the feature calculation.
    stock = panel(ticker, "adjusted").loc[:asof]
    spy = panel("SPY", "adjusted").loc[:asof]
    return reference.signal_features(stock, spy, asof)

spy_calendar = [
    t.strftime("%Y-%m-%d")
    for t in panel("SPY", "raw").index
]
start = spy_calendar.index("2025-09-18")
days = spy_calendar[start:start + SESSIONS]
assert len(days) == SESSIONS

cash = START_CASH
positions = {}
pending = []
trades = []
daily = []
ledger = DividendLedger()
previous_nav = START_CASH
previous_day = None
blocker = None
rejections = []
plans_count = 0

def mark(day, field):
    return (
        cash
        + sum(
            p["shares"] * price(t, day, field)
            for t, p in positions.items()
        )
        + float(ledger.outstanding())
    )

for day in days:
    try:
        # A payment converts an existing receivable to cash.
        cash += float(ledger.settle(day))

        # Process ex-date actions before the opening auction.
        affected = set(positions)
        affected.update(
            o["ticker"] for o in pending
            if o["action"] == "BUY"
        )

        for ticker in sorted(affected):
            if previous_day is None:
                continue

            f0 = factor(ticker, previous_day)
            f1 = factor(ticker, day)

            if abs(f1 / f0 - 1) <= 1e-6:
                continue

            event = EVENTS.get((ticker, day))
            if (
                event is None
                or event.declared_on > previous_day
                or not factor_reconciles(
                    event, f0, f1,
                    price(ticker, previous_day)
                )
            ):
                raise RuntimeError(
                    "UNVERIFIED_CORPORATE_ACTION:"
                    + ticker + ":" + day
                )

            if ticker in positions:
                p = positions[ticker]
                ledger.accrue(
                    event, day, int(p["shares"])
                )
                p["initial_stop"] = max(
                    0.01,
                    p["initial_stop"] - float(event.amount)
                )

            for o in pending:
                if o["ticker"] == ticker and o["action"] == "BUY":
                    o["stop"] = max(
                        0.01, o["stop"] - float(event.amount)
                    )

        open_before = mark(day, "Open")
        overnight_pnl = open_before - previous_nav

        # A same-opening buy cannot depend on uncertain
        # proceeds from another same-opening sell.
        opening_buy_budget = cash
        opening_buy_spent = 0.0
        cost_today = 0.0

        orders = sorted(
            pending,
            key=lambda o: 0 if o["action"] == "SELL" else 1
        )
        pending = []

        seen_today = set()

        for order in orders:
            ticker = order["ticker"]
            side = order["action"]
            qty = int(order["shares"])

            if (
                order["signal_date"] != previous_day
                or qty <= 0
                or ticker in seen_today
            ):
                raise RuntimeError("INVALID_PENDING_ORDER")

            seen_today.add(ticker)
            opening = price(ticker, day, "Open")
            execution = opening * (
                1 - SLIP if side == "SELL" else 1 + SLIP
            )
            execution_cost = qty * opening * SLIP + FEE

            if side == "SELL":
                p = positions.get(ticker)
                if p is None or qty > p["shares"]:
                    raise RuntimeError("INVALID_SELL_QUANTITY")

                cash += qty * execution - FEE
                p["shares"] -= qty

                if p["shares"] == 0:
                    del positions[ticker]

            elif side == "BUY":
                debit = qty * execution + FEE

                if ticker in positions:
                    raise RuntimeError("UNSUPPORTED_POSITION_TOPUP")

                if (
                    debit + opening_buy_spent
                    > opening_buy_budget + 1e-7
                ):
                    rejections.append({
                        "date": day,
                        "ticker": ticker,
                        "reason": "OPENING_CASH_BUDGET",
                    })
                    continue

                if (
                    qty * opening / open_before
                    > STRAT.order_entry_position_cap + 1e-9
                ):
                    rejections.append({
                        "date": day,
                        "ticker": ticker,
                        "reason": "OPENING_POSITION_CAP",
                    })
                    continue

                opening_buy_spent += debit
                cash -= debit

                positions[ticker] = {
                    "shares": qty,
                    "initial_shares": qty,
                    "avg_cost": execution,
                    "initial_stop": order["stop"],
                    "entry_date": day,
                    "sector": order["sector"],
                }

                if execution <= order["stop"]:
                    raise RuntimeError(
                        "FILLED_BELOW_STOP_REQUIRES_POLICY:"
                        + ticker
                    )

            else:
                raise RuntimeError("UNKNOWN_ORDER_ACTION")

            cost_today += execution_cost

            trades.append({
                "date": day,
                "signal_date": order["signal_date"],
                "ticker": ticker,
                "action": side,
                "shares": qty,
                "execution_price": execution,
                "execution_cost": execution_cost,
                "reason": order["reason"],
            })

        open_after = mark(day, "Open")

        assert math.isclose(
            open_before - open_after,
            cost_today,
            abs_tol=0.0001,
        ), "OPEN_EXECUTION_NAV_IDENTITY_FAILED"

        intraday_pnl = sum(
            p["shares"] * (
                price(t, day) - price(t, day, "Open")
            )
            for t, p in positions.items()
        )

        nav = mark(day, "Close")

        assert math.isclose(
            nav,
            previous_nav + overnight_pnl
            + intraday_pnl - cost_today,
            abs_tol=0.0001,
        ), "DAILY_NAV_IDENTITY_FAILED"

        assert cash >= -0.0001
        assert len(positions) <= STRAT.target_positions

        daily.append({
            "date": day,
            "nav": nav,
            "cash": cash,
            "receivable": float(ledger.outstanding()),
            "holdings": len(positions),
            "overnight_pnl": overnight_pnl,
            "intraday_pnl": intraday_pnl,
            "execution_cost": cost_today,
        })

        # At the close, plan future orders using only
        # information available through this date.
        if day != days[-1]:
            sectors = defaultdict(float)
            used_risk = 0.0

            for ticker, p in positions.items():
                close = price(ticker, day)
                sectors[p["sector"]] += p["shares"] * close
                used_risk += p["shares"] * (
                    max(0.0, close - p["initial_stop"])
                    + CFG.gap_buffer * close
                )

            # Exit orders are planned but do not release
            # capital or position slots until actually filled.
            for ticker, p in sorted(positions.items()):
                f = features(ticker, day)

                if not f:
                    raise RuntimeError(
                        "MISSING_HOLDING_FEATURES:" + ticker
                    )

                result = plan_mpb_exit(
                    shares=int(p["shares"]),
                    original_shares=int(p["initial_shares"]),
                    entry_cost=float(p["avg_cost"]),
                    initial_stop=float(p["initial_stop"]),
                    close_raw=price(ticker, day),
                    ema21_adjusted=float(f["ema21"]),
                    close_adjusted=float(f["close"]),
                    nav=nav,
                    same_day=(p["entry_date"] == day),
                    policy=POLICY,
                )

                if result.sell_shares > 0:
                    pending.append({
                        "action": "SELL",
                        "signal_date": day,
                        "ticker": ticker,
                        "shares": result.sell_shares,
                        "reason": result.reason,
                    })

            projected_cash = cash
            projected_risk = used_risk
            projected_sector = dict(sectors)
            planned_buys = 0

            for s in by_day.get(day, []):
                ticker = s["ticker"]
                sector = s["sector"]

                if ticker in positions:
                    continue
                if len(positions) + planned_buys >= STRAT.target_positions:
                    break
                if len(trades) + len(pending) >= (
                    CONTEST.transaction_limit
                    - STRAT.reserve_transactions
                ):
                    break
                if sector in ("", "Unknown", "nan"):
                    continue

                close = price(ticker, day)
                stop = (
                    float(s["planned_stop_adjusted"])
                    * close / price(ticker, day, kind="adjusted")
                )

                if not 0 < stop < close:
                    continue

                per_share = (
                    close - stop
                    + close * (CFG.gap_buffer + SLIP)
                )

                budget = min(
                    CFG.risk_per_position * nav,
                    max(
                        0.0,
                        CFG.portfolio_planned_risk_cap * nav
                        - projected_risk,
                    ),
                )

                frame = panel(ticker, "raw")
                prior = frame.loc[:pd.Timestamp(day)].iloc[:-1]
                if len(prior) < 20:
                    continue

                average_volume = float(
                    prior.tail(20)["Volume"].mean()
                )

                limits = [
                    math.floor(max(0, budget - 2*FEE) / per_share),
                    math.floor(
                        min(
                            STRAT.position_buffer_cap,
                            STRAT.order_entry_position_cap,
                            CONTEST.max_position_weight
                        ) * nav / (close * (1+CFG.gap_buffer))
                    ),
                    math.floor(
                        max(
                            0.0,
                            STRAT.max_sector_weight * nav
                            - projected_sector.get(sector, 0)
                        ) / close
                    ),
                    math.floor(
                        average_volume * CFG.max_participation
                    ),
                    math.floor(
                        max(
                            0.0,
                            projected_cash
                            - STRAT.cash_operating_target_dollars - FEE
                        ) / (close * (1 + CFG.gap_buffer))
                    ),
                ]

                q = max(0, min(limits))

                if q * close < STRAT.min_rebalance_dollars:
                    continue

                pending.append({
                    "action": "BUY",
                    "signal_date": day,
                    "ticker": ticker,
                    "shares": q,
                    "sector": sector,
                    "stop": stop,
                    "reason": s["setup"],
                })

                projected_cash -= (
                    q * close * (1 + CFG.gap_buffer) + FEE
                )
                projected_risk += q * per_share + 2 * FEE
                projected_sector[sector] = (
                    projected_sector.get(sector, 0) + q * close
                )
                planned_buys += 1

            plans_count += len(pending)

        previous_nav = nav
        previous_day = day

    except (RuntimeError, ValueError, KeyError) as exc:
        blocker = {"date": day, "reason": str(exc)}
        break

OUT = ROOT / "audit"
OUT.mkdir(exist_ok=True)

def write_csv(filename, records):
    if not records:
        return
    with (OUT / filename).open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(records[0])
        )
        writer.writeheader()
        writer.writerows(records)

write_csv("p3_lifecycle_v2_daily.csv", daily)
write_csv("p3_lifecycle_v2_trades.csv", trades)

buys = sum(t["action"] == "BUY" for t in trades)
sells = sum(t["action"] == "SELL" for t in trades)

summary = {
    "schema": "FMA_MPB_LIFECYCLE_V2",
    "purpose": "HISTORICAL_SOFTWARE_INTEGRATION_NOT_FINAL_BACKTEST",
    "status": "BLOCKED" if blocker else "PASS",
    "sessions_requested": SESSIONS,
    "sessions_completed": len(daily),
    "simulated_buys": buys,
    "simulated_sells": sells,
    "orders_planned": plans_count,
    "holdings_at_end": len(positions),
    "cash_rejections": rejections,
    "dividend_receivable": str(ledger.outstanding()),
    "blocker": blocker,
    "reference_feature_dependency": True,
    "limitations": [
        "Frozen original reference generates technical features.",
        "Entry selection is from previously validated signal CSV.",
        "Opening-market fills are hypothetical.",
        "Same-auction sell proceeds cannot finance opening buys.",
        "Non-verified corporate actions are blocked.",
        "Dividend-adjusted stops are a research assumption.",
        "No auxiliary portfolio allocation.",
        "No partial fills, daily intrabar stop execution, or taxes.",
        "Not a formally verified strategy-performance backtest."
    ],
}

(OUT / "p3_lifecycle_v2_summary.json").write_text(
    json.dumps(summary, indent=2) + "\n"
)

print("=== MPB MULTI-ASSET LIFECYCLE V2 ===")
print(json.dumps(summary, indent=2))
print("Daily:", OUT / "p3_lifecycle_v2_daily.csv")
print("Trades:", OUT / "p3_lifecycle_v2_trades.csv")
