import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path.home() / "FMA_Independent_Research"
AUDIT = ROOT / "audit"
BUNDLE = (
    Path.home()
    / "FMA_Competition/Market_Refresh_Runs"
    / "manual_full_20261031T061137Z_432cf6e9"
    / "market_bundle"
)

NAV = 1_000_000.0
FEE = 10.0
SLIPPAGE = 0.0005
GAP_BUFFER = 0.01
SINGLE_RISK = 0.005
NAME_CAP = 0.072
SECTOR_CAP = 0.24
MIN_CASH = 50_000.0

def read_csv(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))

signals = read_csv(AUDIT / "historical_signal_candidates.csv")
gates = read_csv(AUDIT / "p3_pretrade_gate.csv")
gate_map = {
    (r["signal_date"], r["ticker"]): r
    for r in gates
}

assert len(signals) == len(gates) == 1229

cache = {}

def panel(ticker, kind):
    key = (ticker, kind)
    if key not in cache:
        rows = read_csv(BUNDLE / kind / f"{ticker}.csv")
        dates = [r["Date"] for r in rows]
        assert dates == sorted(set(dates))
        cache[key] = rows
    return cache[key]

def propose_from_signal_date(signal, raw_rows, adjusted_rows):
    """Order sizing from T-day and earlier data ONLY."""
    date = signal["date"]
    dates = [r["Date"] for r in raw_rows]
    i = dates.index(date)

    assert i >= 20
    raw = raw_rows[i]
    adj = next(r for r in adjusted_rows if r["Date"] == date)

    reference = float(raw["Close"])
    adj_close = float(adj["Close"])

    stop = (
        float(signal["planned_stop_adjusted"])
        * reference / adj_close
    )

    assert 0 < stop < reference

    previous_volume = [
        float(r["Volume"]) for r in raw_rows[i-20:i]
    ]
    avg_volume = sum(previous_volume) / 20.0

    per_share_risk = (
        reference - stop
        + reference * (GAP_BUFFER + SLIPPAGE)
    )

    limits = {
        "single_risk": math.floor(
            max(0, SINGLE_RISK * NAV - 2 * FEE)
            / per_share_risk
        ),
        "position": math.floor(
            NAME_CAP * NAV
            / (reference * (1 + GAP_BUFFER))
        ),
        "sector": math.floor(
            SECTOR_CAP * NAV / reference
        ),
        "volume": math.floor(avg_volume * 0.01),
        "cash": math.floor(
            (NAV - MIN_CASH - FEE)
            / (reference * (1 + GAP_BUFFER))
        ),
    }

    quantity = max(0, min(limits.values()))

    if quantity * reference < 4000:
        quantity = 0

    if quantity:
        planned_risk = (
            quantity * per_share_risk + 2 * FEE
        )
        assert planned_risk <= SINGLE_RISK * NAV + 1e-7
        assert (
            quantity * reference * (1 + GAP_BUFFER)
            <= NAME_CAP * NAV + 1e-7
        )
    else:
        planned_risk = 0.0

    return {
        "signal_date": date,
        "ticker": signal["ticker"],
        "allocation_role": "MPB",
        "action": "BUY",
        "shares": quantity,
        "reference_raw_close": reference,
        "initial_stop_raw": stop,
        "planned_risk_dollars": planned_risk,
        "sizing_limits": limits,
    }

def simulate_market_on_open(order, next_date, open_price):
    """All-or-nothing opening fill; no knowledge of open at T."""
    q = order["shares"]
    if q <= 0:
        return {"status": "NO_ORDER"}

    if next_date <= order["signal_date"]:
        raise ValueError("LOOKAHEAD_OR_INVALID_EXECUTION_DATE")

    if not math.isfinite(open_price) or open_price <= 0:
        raise ValueError("INVALID_OPEN_PRICE")

    execution_price = open_price * (1 + SLIPPAGE)
    total_debit = q * execution_price + FEE

    if total_debit > NAV:
        return {
            "status": "REJECT_INSUFFICIENT_OPEN_CASH",
            "shares_filled": 0,
            "cash_after": NAV,
        }

    cash_after = NAV - total_debit
    marked_at_open = cash_after + q * open_price
    execution_cost = q * open_price * SLIPPAGE + FEE

    assert math.isclose(
        NAV - marked_at_open,
        execution_cost,
        rel_tol=1e-10,
        abs_tol=1e-6,
    )

    return {
        "status": "SIMULATED_FILL",
        "date": next_date,
        "shares_filled": q,
        "reference_open": open_price,
        "execution_price": execution_price,
        "cash_after": cash_after,
        "nav_marked_at_open": marked_at_open,
        "execution_cost": execution_cost,
        "open_below_signal_stop": (
            open_price <= order["initial_stop_raw"]
        ),
    }

# Select a clean historical fixture to TEST the software.
# The next-day gate is NOT used as a trading decision.
fixture = None

for signal in signals:
    gate = gate_map[(signal["date"], signal["ticker"])]

    if gate["gate"] != "PRICE_DATA_READY_NOT_FILLED":
        continue

    raw = panel(signal["ticker"], "raw")
    adjusted = panel(signal["ticker"], "adjusted")

    order = propose_from_signal_date(signal, raw, adjusted)

    if order["shares"] > 0:
        fixture = (signal, gate, raw, order)
        break

if fixture is None:
    raise RuntimeError("NO_VALID_SOFTWARE_TEST_FIXTURE")

signal, gate, raw, order = fixture
next_date = gate["next_date"]
next_row = next(
    r for r in raw if r["Date"] == next_date
)

next_open = float(next_row["Open"])
next_close = float(next_row["Close"])

fill = simulate_market_on_open(
    order, next_date, next_open
)

if fill["status"] != "SIMULATED_FILL":
    raise RuntimeError("FIXTURE_NOT_AFFORDABLE_AT_OPEN")

q = fill["shares_filled"]
close_nav = fill["cash_after"] + q * next_close
market_change_after_open = q * (next_close - next_open)

assert math.isclose(
    close_nav - NAV,
    market_change_after_open - fill["execution_cost"],
    rel_tol=1e-10,
    abs_tol=1e-6,
)

# Check that an unanticipated price spike is rejected,
# rather than resizing shares using future open information.
rejection = simulate_market_on_open(
    order, next_date, 1_000_000_000.0
)
assert rejection["status"] == "REJECT_INSUFFICIENT_OPEN_CASH"
assert rejection["shares_filled"] == 0

# Check that opening below the stop is not silently
# excluded after observing the opening price.
stress = simulate_market_on_open(
    order, next_date,
    order["initial_stop_raw"] * 0.9
)
assert stress["status"] == "SIMULATED_FILL"
assert stress["open_below_signal_stop"]

result = {
    "schema": "FMA_HISTORICAL_FILL_FIXTURE_V1",
    "status": "PASS",
    "purpose": "SOFTWARE_VALIDATION_NOT_BACKTEST",
    "signal": {
        "date": signal["date"],
        "ticker": signal["ticker"],
        "setup": signal["setup"],
    },
    "order_fixed_at_T": order,
    "next_session_fill": fill,
    "next_session_close_nav": close_nav,
    "market_change_after_open": market_change_after_open,
    "checks": {
        "T_date_only_sizing": "PASS_BY_FUNCTION_INTERFACE",
        "open_cash_rejection": "PASS",
        "opening_below_stop_not_lookahead_cancelled": "PASS",
        "nav_execution_cost_identity": "PASS",
    },
    "source_sha256": {
        "raw_price_panel": hashlib.sha256(
            (BUNDLE / "raw"
             / f"{signal['ticker']}.csv").read_bytes()
        ).hexdigest()
    },
    "limitations": [
        "One historical trade fixture, not a strategy backtest.",
        "MOO fill with fixed 5bps slippage is an assumption.",
        "Stop-gap position management is not implemented.",
        "No same-day exit or pending/partial fills.",
        "No corporate actions in this selected fixture.",
        "No multi-period portfolio or auxiliary allocation.",
        "Fixture selection is for software validation only.",
    ],
}

report = AUDIT / "p3_first_historical_fill.json"
report.write_text(json.dumps(result, indent=2) + "\n")

print("=== FIRST HISTORICAL EXECUTION FIXTURE ===")
print(json.dumps({
    "status": result["status"],
    "signal": result["signal"],
    "shares_decided_at_T": order["shares"],
    "next_session_fill_status": fill["status"],
    "next_session_reference_open": next_open,
    "execution_cost": fill["execution_cost"],
    "nav_identity": result["checks"]["nav_execution_cost_identity"],
    "report": str(report),
}, indent=2))
