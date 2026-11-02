"""Independent replay audit of the V2 historical pilot."""

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
BUNDLE = (
    Path.home()
    / "FMA_Competition/Market_Refresh_Runs"
    / "manual_full_20261031T061137Z_432cf6e9"
    / "market_bundle"
)

INITIAL_CASH = 1_000_000.0
FEE = 10.0
SLIPPAGE = 0.0005

def load(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))

def equal(a, b):
    return math.isclose(
        float(a), float(b),
        rel_tol=1e-10, abs_tol=0.0001
    )

daily = load(AUDIT / "p3_lifecycle_v2_daily.csv")
trades = load(AUDIT / "p3_lifecycle_v2_trades.csv")
events = json.loads(
    (ROOT / "configs/verified_cash_dividends.json").read_text()
)

assert daily
assert [r["date"] for r in daily] == sorted(
    set(r["date"] for r in daily)
)

calendar = [
    r["Date"] for r in load(BUNDLE / "raw/SPY.csv")
]
next_day = dict(zip(calendar[:-1], calendar[1:]))

trade_days = defaultdict(list)
for trade in trades:
    trade_days[trade["date"]].append(trade)

price_cache = {}

def price(ticker, day, field):
    if ticker not in price_cache:
        price_cache[ticker] = {
            r["Date"]: r
            for r in load(BUNDLE / "raw" / f"{ticker}.csv")
        }
    return float(price_cache[ticker][day][field])

cash = INITIAL_CASH
holdings = {}
receivables = {}
paid_claims = set()
previous_nav = INITIAL_CASH
sell_details = []
maximum_weight = 0.0
concentration_days = 0
checks = 0

for row in daily:
    day = row["date"]

    # Settle previously accrued dividends only on or
    # after their independently specified payment dates.
    for event in events:
        key = (event["ticker"], event["ex_date"])
        if (
            key in receivables
            and key not in paid_claims
            and day >= event["pay_date"]
        ):
            cash += receivables[key]
            paid_claims.add(key)

    # Determine ex-date entitlement from holdings
    # BEFORE any opening fills on the ex-date.
    for event in events:
        if day == event["ex_date"]:
            key = (event["ticker"], event["ex_date"])
            assert key not in receivables
            shares = holdings.get(event["ticker"], 0)
            if shares:
                receivables[key] = (
                    shares * float(event["amount_per_share"])
                )

    outstanding = sum(
        amount for key, amount in receivables.items()
        if key not in paid_claims
    )

    initial_opening_cash = cash
    open_before = cash + outstanding + sum(
        q * price(t, day, "Open")
        for t, q in holdings.items()
    )
    overnight_pnl = open_before - previous_nav

    spent_on_buys = 0.0
    daily_cost = 0.0
    seen = set()

    for trade in trade_days[day]:
        ticker = trade["ticker"]
        action = trade["action"]
        qty = int(trade["shares"])

        assert qty > 0
        assert ticker not in seen
        seen.add(ticker)

        assert next_day[trade["signal_date"]] == day, (
            "INCORRECT_TPLUS1_EXECUTION"
        )

        opening = price(ticker, day, "Open")
        execution = float(trade["execution_price"])
        cost = float(trade["execution_cost"])

        assert action in ("BUY", "SELL")
        expected_execution = opening * (
            1 + SLIPPAGE if action == "BUY"
            else 1 - SLIPPAGE
        )
        expected_cost = qty * opening * SLIPPAGE + FEE

        assert equal(execution, expected_execution), (
            "EXECUTION_PRICE_MISMATCH"
        )
        assert equal(cost, expected_cost), (
            "EXECUTION_COST_MISMATCH"
        )

        if action == "BUY":
            assert ticker not in holdings
            debit = qty * execution + FEE
            spent_on_buys += debit
            cash -= debit
            holdings[ticker] = qty
        else:
            assert holdings.get(ticker, 0) >= qty
            cash += qty * execution - FEE
            holdings[ticker] -= qty
            if holdings[ticker] == 0:
                del holdings[ticker]
            sell_details.append({
                "date": day,
                "ticker": ticker,
                "shares": qty,
                "reason": trade["reason"]
            })

        daily_cost += cost

    # Buy orders may not use uncertain proceeds
    # from same-auction sells.
    assert spent_on_buys <= initial_opening_cash + 0.0001, (
        "SAME_AUCTION_SELL_PROCEEDS_USED_FOR_BUYS"
    )

    assert cash >= -0.0001
    assert equal(cash, row["cash"]), "CASH_REPLAY_MISMATCH"
    assert equal(outstanding, row["receivable"]), (
        "DIVIDEND_RECEIVABLE_MISMATCH"
    )
    assert len(holdings) == int(row["holdings"]), (
        "HOLDING_COUNT_MISMATCH"
    )

    market_value = sum(
        q * price(t, day, "Close")
        for t, q in holdings.items()
    )
    nav = cash + market_value + outstanding

    assert equal(nav, row["nav"]), "NAV_REPLAY_MISMATCH"

    intraday_pnl = sum(
        q * (
            price(t, day, "Close")
            - price(t, day, "Open")
        )
        for t, q in holdings.items()
    )

    assert equal(
        overnight_pnl, row["overnight_pnl"]
    ), "OVERNIGHT_PNL_MISMATCH"
    assert equal(
        intraday_pnl, row["intraday_pnl"]
    ), "INTRADAY_PNL_MISMATCH"
    assert equal(
        daily_cost, row["execution_cost"]
    ), "DAILY_EXECUTION_COST_MISMATCH"
    assert equal(
        nav,
        previous_nav + overnight_pnl
        + intraday_pnl - daily_cost
    ), "DAILY_PNL_BRIDGE_MISMATCH"

    max_weight_today = max(
        (
            q * price(t, day, "Close") / nav
            for t, q in holdings.items()
        ),
        default=0.0
    )
    maximum_weight = max(maximum_weight, max_weight_today)
    concentration_days += (
        max_weight_today > 0.10 + 1e-9
    )

    checks += 1
    previous_nav = nav

assert len(trades) == sum(
    len(trade_days[day]) for day in [r["date"] for r in daily]
)

result = {
    "schema": "FMA_INDEPENDENT_LIFECYCLE_AUDIT_V1",
    "status": "PASS",
    "sessions_replayed": checks,
    "trades_replayed": len(trades),
    "trade_actions": dict(Counter(
        t["action"] for t in trades
    )),
    "sells": sell_details,
    "holdings_reconstructed": len(holdings),
    "cash_identity": "PASS",
    "nav_identity": "PASS",
    "tplus1_execution": "PASS",
    "dividend_receivable_reconciliation": "PASS",
    "same_auction_cash_guard": "PASS",
    "maximum_observed_position_weight": maximum_weight,
    "days_with_position_weight_above_10pct": (
        concentration_days
    ),
    "scope": "ACCOUNTING_REPLAY_NOT_STRATEGY_VALIDATION"
}

print("=== INDEPENDENT LIFECYCLE AUDIT ===")
print(json.dumps(result, indent=2))

# Store the audit locally, without publishing market data.
(AUDIT / "p3_lifecycle_v2_independent_audit.json").write_text(
    json.dumps(result, indent=2) + "\n"
)
