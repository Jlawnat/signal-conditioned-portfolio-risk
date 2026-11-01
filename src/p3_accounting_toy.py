import copy
import json
from datetime import date
from decimal import Decimal as D
from pathlib import Path

OUT = Path.home() / "FMA_Independent_Research/audit"
FEE = D("10")
SLIP = D("0.0005")

def number(x):
    v = D(str(x))
    if not v.is_finite() or v <= 0:
        raise ValueError("INVALID_PRICE")
    return v

def nav(state, quotes):
    total = state["cash"]
    for ticker, pos in state["positions"].items():
        if ticker not in quotes:
            raise ValueError("MISSING_HOLDING_PRICE:" + ticker)
        total += pos["shares"] * number(quotes[ticker])
    return total

def fill(state, order, day, quotes):
    ticker = order["ticker"]
    side = order["action"]
    qty = order["shares"]

    if side not in ("BUY", "SELL"):
        raise ValueError("INVALID_SIDE")
    if type(qty) is not int or qty <= 0:
        raise ValueError("INVALID_QUANTITY")
    if date.fromisoformat(day) <= date.fromisoformat(
        order["signal_date"]
    ):
        raise ValueError("LOOKAHEAD_EXECUTION")
    if any(x["date"] == day and x["ticker"] == ticker
           for x in state["transactions"]):
        raise ValueError("SAME_DAY_REPEAT_TRADE")
    if ticker not in quotes:
        raise ValueError("MISSING_EXECUTION_PRICE")

    reference = number(quotes[ticker])
    before = nav(state, quotes)
    execution_price = reference * (
        1 + SLIP if side == "BUY" else 1 - SLIP
    )

    current = state["positions"].get(ticker)

    if side == "BUY":
        if current is not None:
            raise ValueError("TOP_UP_LIFECYCLE_NOT_IMPLEMENTED")
        role = order.get("allocation_role")
        if role == "MPB":
            if order.get("entry_confirmed") is not True:
                raise ValueError("UNCONFIRMED_MPB_ENTRY")
        elif role == "SUPPLEMENTAL":
            if order.get("eligibility_verified") is not True:
                raise ValueError("UNVERIFIED_SUPPLEMENTAL")
        else:
            raise ValueError("UNKNOWN_ALLOCATION_ROLE")

        stop = number(order["initial_stop"])
        if stop >= execution_price:
            raise ValueError("INVALID_INITIAL_STOP")
        if reference < D("5"):
            raise ValueError("BELOW_MIN_BUY_PRICE")

        cash_change = -(qty * execution_price + FEE)
        if state["cash"] + cash_change < 0:
            raise ValueError("INSUFFICIENT_CASH")
    else:
        if current is None or current["shares"] < qty:
            raise ValueError("INSUFFICIENT_SHARES")
        cash_change = qty * execution_price - FEE

    # Only mutate state after all validations succeed.
    state["cash"] += cash_change

    if side == "BUY":
        state["positions"][ticker] = {
            "shares": qty,
            "avg_cost": execution_price,
            "initial_stop": stop,
            "entry_date": day,
            "allocation_role": role,
        }
    else:
        current["shares"] -= qty
        if current["shares"] == 0:
            del state["positions"][ticker]

    record = {
        "date": day,
        "signal_date": order["signal_date"],
        "ticker": ticker,
        "action": side,
        "shares": qty,
        "reference_price": str(reference),
        "execution_price": str(execution_price),
        "commission": str(FEE),
        "slippage_cost": str(qty * reference * SLIP),
        "cash_after": str(state["cash"]),
    }
    state["transactions"].append(record)

    after = nav(state, quotes)
    expected_cost = qty * reference * SLIP + FEE
    assert before - after == expected_cost, (
        "NAV_ACCOUNTING_IDENTITY_FAILED"
    )

    return record

state = {
    "cash": D("800000"),
    "positions": {
        "AAA": {
            "shares": 200,
            "avg_cost": D("980"),
            "initial_stop": D("940"),
            "entry_date": "2025-09-02",
            "allocation_role": "MPB",
        }
    },
    "transactions": [],
}

quotes = {"AAA": "1020", "BBB": "500", "CCC": "500"}
day = "2025-09-19"

initial_nav = nav(state, quotes)
assert initial_nav == D("1004000")

sell = {
    "signal_date": "2025-09-18",
    "ticker": "AAA",
    "action": "SELL",
    "shares": 50,
}

buy = {
    "signal_date": "2025-09-18",
    "ticker": "BBB",
    "action": "BUY",
    "shares": 100,
    "initial_stop": "470",
    "allocation_role": "MPB",
    "entry_confirmed": True,
}

records = [
    fill(state, sell, day, quotes),
    fill(state, buy, day, quotes),
]

assert state["cash"] == D("800929.50")
assert state["positions"]["AAA"]["shares"] == 150
assert state["positions"]["BBB"]["shares"] == 100
assert nav(state, quotes) == D("1003929.50")
assert len(state["transactions"]) == 2

def must_reject(name, action):
    snapshot = copy.deepcopy(state)
    try:
        action()
    except ValueError:
        assert state == snapshot, name + "_MUTATED_STATE"
        return
    raise AssertionError(name + "_NOT_REJECTED")

must_reject(
    "REPEATED_SAME_DAY",
    lambda: fill(state, sell, day, quotes)
)

must_reject(
    "SAME_DAY_EXECUTION",
    lambda: fill(state, {
        **buy,
        "ticker": "CCC",
        "signal_date": day,
    }, day, quotes)
)

must_reject(
    "INSUFFICIENT_CASH",
    lambda: fill(state, {
        **buy,
        "ticker": "CCC",
        "shares": 100000,
    }, day, quotes)
)

must_reject(
    "UNCONFIRMED_ENTRY",
    lambda: fill(state, {
        **buy,
        "ticker": "CCC",
        "entry_confirmed": False,
    }, day, quotes)
)

try:
    nav(state, {"AAA": "1020"})
except ValueError as exc:
    assert str(exc) == "MISSING_HOLDING_PRICE:BBB"
else:
    raise AssertionError("MISSING_PRICE_NOT_REJECTED")

result = {
    "schema": "FMA_ACCOUNTING_TOY_V1",
    "status": "PASS",
    "synthetic_data_only": True,
    "initial_reference_nav": str(initial_nav),
    "final_reference_nav": str(nav(state, quotes)),
    "total_execution_cost": str(
        initial_nav - nav(state, quotes)
    ),
    "cash_after": str(state["cash"]),
    "transaction_count": len(state["transactions"]),
    "trades": records,
    "verified_properties": [
        "Cash and holdings accounting",
        "NAV conservation net of costs",
        "Sell then buy cash recycling",
        "No same-day execution of new signals",
        "No duplicate same-day trading",
        "Insufficient cash rejection",
        "Unconfirmed entry rejection",
        "Missing holding quote rejection",
        "Failed orders leave state unchanged",
    ],
    "not_yet_implemented": [
        "Original order-generator parity",
        "Dynamic portfolio risk and sector constraints",
        "Pending and partial orders",
        "Corporate actions and interest",
        "Historical market execution",
        "Multi-session lifecycle and return attribution",
    ],
}

path = OUT / "p3_accounting_toy_summary.json"
path.write_text(json.dumps(result, indent=2) + "\n")

print("=== ACCOUNTING CONTRACT TEST ===")
print(json.dumps({
    "status": result["status"],
    "initial_reference_nav": result["initial_reference_nav"],
    "final_reference_nav": result["final_reference_nav"],
    "total_execution_cost": result["total_execution_cost"],
    "cash_after": result["cash_after"],
    "transaction_count": result["transaction_count"],
    "properties_checked": len(result["verified_properties"]),
    "report": str(path),
}, indent=2))
