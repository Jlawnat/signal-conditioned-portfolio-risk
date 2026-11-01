import csv
import hashlib
import json
from decimal import Decimal as D
from pathlib import Path

ROOT = Path.home() / "FMA_Independent_Research"
AUDIT = ROOT / "audit"
BUNDLE = (
    Path.home() / "FMA_Competition/Market_Refresh_Runs"
    / "manual_full_20261031T061137Z_432cf6e9"
    / "market_bundle"
)

INITIAL_CASH = D("1000000")
FEE = D("10")
SLIP = D("0.0005")
HOLD_SESSIONS = 5

fixture = json.loads(
    (AUDIT / "p3_first_historical_fill.json").read_text()
)

assert fixture["status"] == "PASS"
assert fixture["purpose"] == "SOFTWARE_VALIDATION_NOT_BACKTEST"

ticker = fixture["signal"]["ticker"]
signal_date = fixture["signal"]["date"]
entry_date = fixture["next_session_fill"]["date"]
shares = int(fixture["order_fixed_at_T"]["shares"])

assert ticker == "CHRW"
assert shares == 331

def load_panel(path):
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    dates = [r["Date"] for r in rows]
    assert dates == sorted(set(dates))
    return {r["Date"]: r for r in rows}

raw_path = BUNDLE / "raw" / f"{ticker}.csv"
adj_path = BUNDLE / "adjusted" / f"{ticker}.csv"

assert hashlib.sha256(
    raw_path.read_bytes()
).hexdigest() == fixture["source_sha256"]["raw_price_panel"]

raw = load_panel(raw_path)
adj = load_panel(adj_path)

spy = load_panel(BUNDLE / "raw/SPY.csv")
sessions = list(spy)

idx = sessions.index(entry_date)
assert idx > 0 and sessions[idx - 1] == signal_date

hold_dates = sessions[idx:idx + HOLD_SESSIONS]
exit_date = sessions[idx + HOLD_SESSIONS]

all_dates = [signal_date] + hold_dates + [exit_date]

for date in all_dates:
    assert date in raw and date in adj, (
        "MISSING_HISTORICAL_PRICE:" + date
    )

def value(date, field):
    x = D(raw[date][field])
    assert x.is_finite() and x > 0
    return x

# Explicitly reject corporate-action windows until
# dividend and split accounting has been implemented.
factors = [
    D(adj[date]["Close"]) / value(date, "Close")
    for date in all_dates
]
for previous, current in zip(factors, factors[1:]):
    if abs(current / previous - D("1")) > D("0.000001"):
        raise RuntimeError(
            "CORPORATE_ACTION_LEDGER_SUPPORT_REQUIRED"
        )

q = D(shares)
entry_open = value(entry_date, "Open")

assert abs(
    entry_open
    - D(str(fixture["next_session_fill"]["reference_open"]))
) < D("0.0001")

entry_execution = entry_open * (D("1") + SLIP)
entry_cost = q * entry_open * SLIP + FEE
cash = INITIAL_CASH - q * entry_execution - FEE

assert cash >= 0
entry_open_nav = cash + q * entry_open
assert INITIAL_CASH - entry_open_nav == entry_cost

daily = []
previous_mark = entry_open
previous_nav = entry_open_nav

for date in hold_dates:
    close = value(date, "Close")
    current_nav = cash + q * close
    market_pnl = q * (close - previous_mark)

    assert current_nav - previous_nav == market_pnl
    assert current_nav == cash + q * close

    daily.append({
        "date": date,
        "ticker": ticker,
        "shares": shares,
        "cash": str(cash),
        "close": str(close),
        "nav": str(current_nav),
        "market_pnl_since_last_mark": str(market_pnl),
    })

    previous_mark = close
    previous_nav = current_nav

# Exit instruction is predetermined at the final
# holding-session close, without using the next open.
exit_signal_date = hold_dates[-1]
assert exit_date > exit_signal_date

exit_open = value(exit_date, "Open")
nav_before_exit = cash + q * exit_open

exit_execution = exit_open * (D("1") - SLIP)
exit_cost = q * exit_open * SLIP + FEE
cash += q * exit_execution - FEE

assert nav_before_exit - cash == exit_cost
assert cash >= 0

# All holdings are closed after the exit.
final_nav = cash

total_cost = entry_cost + exit_cost
market_pnl = q * (exit_open - entry_open)

assert final_nav - INITIAL_CASH == market_pnl - total_cost

csv_path = AUDIT / "p3_multisession_daily.csv"
with csv_path.open("w", newline="") as f:
    writer = csv.DictWriter(
        f, fieldnames=list(daily[0])
    )
    writer.writeheader()
    writer.writerows(daily)

summary = {
    "schema": "FMA_MULTISESSION_ACCOUNTING_V1",
    "status": "PASS",
    "purpose": "SOFTWARE_VALIDATION_NOT_BACKTEST",
    "ticker": ticker,
    "entry_signal_date": signal_date,
    "entry_fill_date": entry_date,
    "exit_instruction_date": exit_signal_date,
    "exit_fill_date": exit_date,
    "held_sessions": len(hold_dates),
    "shares": shares,
    "entry_execution_cost": str(entry_cost),
    "exit_execution_cost": str(exit_cost),
    "total_execution_cost": str(total_cost),
    "cash_and_nav_identity": "PASS",
    "daily_mark_to_market_identity": "PASS",
    "round_trip_pnl_identity": "PASS",
    "corporate_action_window": "NO_FACTOR_CHANGE",
    "final_cash": str(cash),
    "limitations": [
        "One historical accounting fixture, not a backtest.",
        "Fixed five-session holding period is a test rule.",
        "Not the original FMA stop or profit-taking lifecycle.",
        "Opening fill and fixed slippage are assumptions.",
        "Dividend/split windows are rejected, not modeled.",
        "No multiple holdings, pending or partial fills.",
        "No portfolio risk optimisation or auxiliary assets."
    ],
}

report = AUDIT / "p3_multisession_summary.json"
report.write_text(json.dumps(summary, indent=2) + "\n")

print("=== MULTISESSION ACCOUNTING TEST ===")
print(json.dumps(summary, indent=2))
print("Daily ledger:", csv_path)
