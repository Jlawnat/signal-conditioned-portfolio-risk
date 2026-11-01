import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from portfolio.corporate_actions import (
    DividendLedger, load_events, factor_reconciles
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_AUDIT = Path.home() / "FMA_Independent_Research/audit"
AUDIT = ROOT / "audit"
AUDIT.mkdir(parents=True, exist_ok=True)

BUNDLE = (
    Path.home() / "FMA_Competition/Market_Refresh_Runs"
    / "manual_full_20261031T061137Z_432cf6e9"
    / "market_bundle"
)

START_CASH = 1_000_000.0
SLIP = 0.0005
GAP = 0.01
FEE = 10.0
CASH_TARGET = 50_000.0
NAME_CAP = 0.072
SECTOR_CAP = 0.24
PER_NAME_RISK = 0.005
TOTAL_RISK = 0.04
MAX_HOLDINGS = 14
MAX_TRANSACTIONS_FOR_PLANNING = 360
SESSIONS = 12

def rows(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))

signals_file = SOURCE_AUDIT / "historical_signal_candidates.csv"
signals = rows(signals_file)
validation = json.loads(
    (SOURCE_AUDIT / "signal_differential_summary.json").read_text()
)
assert validation["status"] == "PASS"
assert len(signals) == 1229

candidates = defaultdict(list)
for row in signals:
    candidates[row["date"]].append(row)

for date in candidates:
    candidates[date].sort(
        key=lambda x: (-float(x["score"]), x["ticker"])
    )

spy = rows(BUNDLE / "raw/SPY.csv")
calendar = [r["Date"] for r in spy]
start = calendar.index("2025-09-18")
dates = calendar[start:start + SESSIONS]
assert len(dates) == SESSIONS

EVENTS = load_events(
    ROOT / "configs/verified_cash_dividends.json"
)
ledger = DividendLedger()
dividend_accrued_total = 0.0
dividend_cash_received_total = 0.0

cache = {}

def panel(ticker, adjusted=False):
    key = (ticker, adjusted)
    if key not in cache:
        folder = "adjusted" if adjusted else "raw"
        path = BUNDLE / folder / f"{ticker}.csv"
        cache[key] = {r["Date"]: r for r in rows(path)}
    return cache[key]

def px(ticker, day, field="Close", adjusted=False):
    value = float(panel(ticker, adjusted)[day][field])
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"INVALID_PRICE:{ticker}:{day}")
    return value

def factor(ticker, day):
    return px(ticker, day, adjusted=True) / px(ticker, day)

cash = START_CASH
positions = {}
pending = []
transactions = []
daily = []
previous_nav = START_CASH
previous_date = None
blocker = None
rejected_cash = 0
stop_flags = 0
entry_gap_flags = 0

for day in dates:
    # Payment transfers a receivable to spendable cash;
    # it does NOT create a second dividend gain.
    paid_today = float(ledger.settle(day))
    cash += paid_today
    dividend_cash_received_total += paid_today

    accrued_today = 0.0

    def verified_factor_event(ticker):
        if previous_date is None:
            return None

        f0 = factor(ticker, previous_date)
        f1 = factor(ticker, day)

        if abs(f1 / f0 - 1) <= 1e-6:
            return None

        event = EVENTS.get((ticker, day))

        if event is None or not factor_reconciles(
            event, f0, f1,
            px(ticker, previous_date)
        ):
            raise ValueError(
                "UNVERIFIED_CORPORATE_ACTION:"
                + ticker + ":" + day
            )

        # An issuer's declaration must predate the
        # decision date for historical availability.
        if event.declared_on > previous_date:
            raise ValueError(
                "EVENT_INFORMATION_NOT_YET_PUBLIC:"
                + ticker + ":" + day
            )

        return event

    try:
        # Pre-existing holdings receive ex-date dividend
        # entitlement, before any opening buy orders fill.
        for ticker, position in positions.items():
            event = verified_factor_event(ticker)

            if event is not None:
                received = ledger.accrue(
                    event, day, int(position["shares"])
                )
                accrued_today += float(received)

                # Explicit research-only policy: adjust a
                # pre-dividend raw stop by the cash dividend.
                # Strategy sensitivity to this policy remains
                # to be tested.
                position["initial_stop"] = max(
                    0.01,
                    position["initial_stop"]
                    - float(event.amount)
                )

        # Pending orders were fixed at the prior close.
        # If their T+1 date is ex-dividend, adjust the
        # STOP unit, not their precommitted share quantity.
        for order in pending:
            event = verified_factor_event(order["ticker"])

            if event is not None:
                order["stop_raw"] = max(
                    0.01,
                    order["stop_raw"]
                    - float(event.amount)
                )

    except ValueError as exc:
        blocker = {
            "reason": str(exc),
            "date": day,
        }

    if blocker:
        break

    dividend_accrued_total += accrued_today

    # Overnight mark: positions already owned before open.
    open_before = cash + sum(
        p["shares"] * px(ticker, day, "Open")
        for ticker, p in positions.items()
    ) + float(ledger.outstanding())
    overnight_pnl = open_before - previous_nav

    fills_today = 0
    cost_today = 0.0

    # All orders were sized using the PREVIOUS close.
    for order in pending:
        assert order["signal_date"] == previous_date

        ticker = order["ticker"]
        q = order["shares"]
        opening = px(ticker, day, "Open")
        execution = opening * (1 + SLIP)
        debit = q * execution + FEE

        if debit > cash + 1e-8:
            rejected_cash += 1
            continue

        if ticker in positions:
            raise AssertionError("DUPLICATE_POSITION")

        cash -= debit
        positions[ticker] = {
            "shares": q,
            "entry_date": day,
            "avg_cost": execution,
            "initial_stop": order["stop_raw"],
            "sector": order["sector"],
            "allocation_role": "MPB",
        }

        cost_today += q * opening * SLIP + FEE
        fills_today += 1
        if opening <= order["stop_raw"]:
            entry_gap_flags += 1

        transactions.append({
            "signal_date": order["signal_date"],
            "date": day,
            "ticker": ticker,
            "action": "BUY",
            "shares": q,
            "reference_open": opening,
            "execution_price": execution,
            "commission": FEE,
        })

    pending = []

    open_after = cash + sum(
        p["shares"] * px(ticker, day, "Open")
        for ticker, p in positions.items()
    ) + float(ledger.outstanding())

    assert math.isclose(
        open_before - open_after,
        cost_today,
        abs_tol=1e-6,
    )

    intraday_pnl = sum(
        p["shares"] * (
            px(ticker, day, "Close")
            - px(ticker, day, "Open")
        )
        for ticker, p in positions.items()
    )

    nav = cash + sum(
        p["shares"] * px(ticker, day)
        for ticker, p in positions.items()
    ) + float(ledger.outstanding())

    assert math.isclose(
        nav,
        previous_nav + overnight_pnl
        + intraday_pnl - cost_today,
        abs_tol=1e-6,
    )
    assert cash >= -1e-8

    sectors = defaultdict(float)
    used_risk = 0.0
    unmanaged = False

    for ticker, p in positions.items():
        market_price = px(ticker, day)
        sectors[p["sector"]] += p["shares"] * market_price

        stop = p["initial_stop"]
        if market_price <= stop or stop >= p["avg_cost"]:
            stop_flags += 1
            unmanaged = True

        used_risk += p["shares"] * (
            max(0.0, market_price - stop)
            + GAP * market_price
        )

    planned = 0
    projected_cash = cash
    projected_risk = used_risk
    projected_sectors = dict(sectors)

    # This PILOT deliberately does not execute exits.
    # Once a holding requires stop management,
    # do not open any additional risk.
    if day != dates[-1] and not unmanaged:
        for signal in candidates.get(day, []):
            ticker = signal["ticker"]
            sector = signal["sector"]

            if ticker in positions:
                continue
            if len(positions) + planned >= MAX_HOLDINGS:
                break
            if len(transactions) + planned >= \
                    MAX_TRANSACTIONS_FOR_PLANNING:
                break
            if not sector or sector == "Unknown":
                continue

            reference = px(ticker, day)
            adjusted_close = px(
                ticker, day, adjusted=True
            )
            stop = (
                float(signal["planned_stop_adjusted"])
                * reference / adjusted_close
            )

            if not 0 < stop < reference:
                continue

            risk_per_share = (
                reference - stop
                + reference * (GAP + SLIP)
            )

            available_risk = min(
                PER_NAME_RISK * nav,
                max(0.0, TOTAL_RISK * nav - projected_risk)
            )

            prior_rows = rows(
                BUNDLE / "raw" / f"{ticker}.csv"
            )
            date_index = next(
                i for i, r in enumerate(prior_rows)
                if r["Date"] == day
            )
            assert date_index >= 20

            avg_volume = sum(
                float(r["Volume"])
                for r in prior_rows[date_index-20:date_index]
            ) / 20

            limits = [
                math.floor(max(0, available_risk - 2*FEE)
                           / risk_per_share),
                math.floor(NAME_CAP * nav
                           / (reference * (1 + GAP))),
                math.floor(
                    max(0.0, SECTOR_CAP * nav
                        - projected_sectors.get(sector, 0))
                    / reference
                ),
                math.floor(avg_volume * 0.01),
                math.floor(
                    max(0.0, projected_cash - CASH_TARGET - FEE)
                    / (reference * (1 + GAP))
                ),
            ]
            q = max(0, min(limits))

            if q * reference < 4000:
                continue

            pending.append({
                "signal_date": day,
                "ticker": ticker,
                "sector": sector,
                "shares": q,
                "stop_raw": stop,
            })

            projected_cash -= (
                q * reference * (1 + GAP) + FEE
            )
            projected_risk += (
                q * risk_per_share + 2 * FEE
            )
            projected_sectors[sector] = (
                projected_sectors.get(sector, 0)
                + q * reference
            )
            planned += 1

    daily.append({
        "date": day,
        "nav": nav,
        "cash": cash,
        "holdings": len(positions),
        "fills": fills_today,
        "pending_for_next_session": len(pending),
        "overnight_pnl": overnight_pnl,
        "intraday_pnl": intraday_pnl,
        "execution_cost": cost_today,
        "planned_risk_fraction": used_risk / nav,
        "dividend_accrued": accrued_today,
        "dividend_cash_received": paid_today,
        "dividend_receivable": float(
            ledger.outstanding()
        ),
    })

    previous_nav = nav
    previous_date = day

output = AUDIT / "p3_multiasset_pilot_daily.csv"

if daily:
    with output.open("w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=list(daily[0])
        )
        writer.writeheader()
        writer.writerows(daily)

summary = {
    "schema": "FMA_MULTI_ASSET_PILOT_V1",
    "status": "BLOCKED" if blocker else "PASS",
    "purpose": "MULTI_ASSET_SOFTWARE_VALIDATION_ONLY",
    "sessions_requested": SESSIONS,
    "sessions_completed": len(daily),
    "simulated_buy_fills": len(transactions),
    "distinct_positions_at_end": len(positions),
    "rejected_for_open_cash": rejected_cash,
    "entry_open_below_stop_flags": entry_gap_flags,
    "unmanaged_stop_flags": stop_flags,
    "corporate_action_blocker": blocker,
    "dividend_accrued_total": dividend_accrued_total,
    "dividend_cash_received_total": (
        dividend_cash_received_total
    ),
    "dividend_receivable_at_end": float(
        ledger.outstanding()
    ),
    "verified_dividend_events": len(ledger.claims),
    "daily_accounting_identity": "PASS",
    "source_signals_sha256": hashlib.sha256(
        signals_file.read_bytes()
    ).hexdigest(),
    "limitations": [
        "Not an FMA-strategy performance backtest.",
        "No stop, trend or profit-taking exits yet.",
        "Only MPB entries; no supplemental allocation.",
        "Audited cash dividends supported; splits and"
        " unverified dividends still blocked.",
        "Dividend-adjusted stops are research assumptions.",
        "Gross dividends; tax and withholding excluded.",
        "No partial fills.",
        "MOO opening execution is hypothetical.",
        "Portfolio risk is checked for planning, not a "
        "guarantee after overnight price changes.",
        "Fixed-current-constituent historical universe.",
        "Historical sample has prior research exposure.",
    ],
}

report = AUDIT / "p3_multiasset_pilot_summary.json"
report.write_text(json.dumps(summary, indent=2) + "\n")

print("=== MULTI-ASSET PILOT ===")
print(json.dumps(summary, indent=2))
print("Daily ledger:", output)
