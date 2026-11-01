import itertools
import json
import math
from pathlib import Path

ROOT = Path.home() / "FMA_Independent_Research"

# Synthetic test state. NOT real market data.
NAV = 1_000_000.0
PRICE = 10_000.0
STOP = 9_000.0
FEE = 10.0
GAP = 0.01
SLIPPAGE = 0.0005

POSITION_RISK_CAP = 0.005
POSITION_WEIGHT_CAP = 0.072
SECTOR_WEIGHT_CAP = 0.24
MIN_CASH = 50_000.0
MIN_ORDER_VALUE = 4_000.0
MAX_POSITIONS = 14
MAX_PARTICIPATION = 0.01
AVERAGE_DAILY_VOLUME = 1_000

# Existing position remains held. No automatic liquidation.
HELD_Q = 5
HELD_VALUE = HELD_Q * PRICE
CASH = NAV - HELD_VALUE

HELD_RISK = HELD_Q * (
    max(0.0, PRICE - STOP) + GAP * PRICE
)

CANDIDATES = {
    "MPB_1": "Technology",
    "MPB_2": "Healthcare",
    "AUX_1": "Financials",
    "AUX_2": "Industrials",
}

PER_SHARE_NEW_RISK = (
    PRICE - STOP + PRICE * (GAP + SLIPPAGE)
)

MAX_NEW_SHARES = min(
    math.floor(
        (POSITION_RISK_CAP * NAV - 2 * FEE)
        / PER_SHARE_NEW_RISK
    ),
    math.floor(
        POSITION_WEIGHT_CAP * NAV
        / (PRICE * (1 + GAP))
    ),
    math.floor(
        AVERAGE_DAILY_VOLUME * MAX_PARTICIPATION
    ),
)

def allocations(pool):
    """Enumerate admissible integer-share toy allocations."""
    for quantities in itertools.product(
        range(MAX_NEW_SHARES + 1), repeat=len(pool)
    ):
        orders = dict(zip(pool, quantities))
        selected = sum(q > 0 for q in quantities)

        if selected + 1 > MAX_POSITIONS:
            continue

        if any(
            0 < q * PRICE < MIN_ORDER_VALUE
            for q in quantities
        ):
            continue

        sector_values = {"Existing": HELD_VALUE}
        for ticker, q in orders.items():
            sector = CANDIDATES[ticker]
            sector_values[sector] = (
                sector_values.get(sector, 0.0)
                + q * PRICE
            )

        if any(
            value / NAV > SECTOR_WEIGHT_CAP + 1e-12
            for value in sector_values.values()
        ):
            continue

        purchase_cost = sum(
            q * PRICE * (1 + GAP)
            + (FEE if q else 0)
            for q in quantities
        )
        if CASH - purchase_cost < MIN_CASH:
            continue

        invested = HELD_VALUE + sum(
            q * PRICE for q in quantities
        )
        planned_risk = HELD_RISK + sum(
            q * PER_SHARE_NEW_RISK
            + (2 * FEE if q else 0)
            for q in quantities
        )

        yield {
            "orders": orders,
            "invested": invested,
            "planned_risk": planned_risk,
            "remaining_cash_stressed": CASH - purchase_cost,
        }

def evaluate(pool, deployment, risk_cap):
    feasible_without_risk = list(allocations(pool))
    meeting_deployment = [
        a for a in feasible_without_risk
        if a["invested"] + 1e-8 >= deployment * NAV
    ]

    max_deployment = max(
        (a["invested"] for a in feasible_without_risk),
        default=0.0,
    ) / NAV

    if not meeting_deployment:
        return {
            "status": "STRUCTURALLY_INFEASIBLE",
            "max_deployment": max_deployment,
            "minimum_planned_risk": None,
            "orders": None,
        }

    best = min(
        meeting_deployment,
        key=lambda a: (a["planned_risk"],
                       tuple(a["orders"].values())),
    )

    status = (
        "FEASIBLE"
        if best["planned_risk"] <= risk_cap * NAV + 1e-8
        else "RISK_BUDGET_INFEASIBLE"
    )

    return {
        "status": status,
        "max_deployment": max_deployment,
        "minimum_planned_risk": best["planned_risk"],
        "minimum_risk_fraction": best["planned_risk"] / NAV,
        "orders": best["orders"],
    }

mpb = ["MPB_1", "MPB_2"]
full = list(CANDIDATES)

cases = {
    "A_MPB_ONLY_16_PERCENT": evaluate(mpb, 0.16, 0.04),
    "B_FULL_16_PERCENT_DYNAMIC": evaluate(full, 0.16, 0.02),
    "C_FULL_19_PERCENT_DYNAMIC": evaluate(full, 0.19, 0.02),
    "D_FULL_19_PERCENT_STATIC": evaluate(full, 0.19, 0.04),
}

assert cases["A_MPB_ONLY_16_PERCENT"]["status"] == \
       "STRUCTURALLY_INFEASIBLE"

assert cases["B_FULL_16_PERCENT_DYNAMIC"]["status"] == \
       "FEASIBLE"

assert cases["C_FULL_19_PERCENT_DYNAMIC"]["status"] == \
       "RISK_BUDGET_INFEASIBLE"

assert cases["D_FULL_19_PERCENT_STATIC"]["status"] == \
       "FEASIBLE"

assert math.isclose(
    cases["B_FULL_16_PERCENT_DYNAMIC"]["minimum_planned_risk"],
    17715.0,
)

assert math.isclose(
    cases["C_FULL_19_PERCENT_DYNAMIC"]["minimum_planned_risk"],
    21050.0,
)

# Test feasible-set monotonicity across deployment thresholds.
risk_10 = evaluate(full, 0.10, 0.04)["minimum_planned_risk"]
risk_16 = evaluate(full, 0.16, 0.04)["minimum_planned_risk"]
risk_19 = evaluate(full, 0.19, 0.04)["minimum_planned_risk"]
assert risk_10 <= risk_16 <= risk_19

# Existing holdings must remain in each scenario.
assert HELD_Q == 5
assert HELD_VALUE == 50_000.0

result = {
    "schema": "FMA_FEASIBILITY_TOY_V1",
    "status": "PASS",
    "synthetic_data_only": True,
    "existing_holding_shares": HELD_Q,
    "maximum_new_shares_per_asset": MAX_NEW_SHARES,
    "cases": cases,
    "deployment_monotonicity": "PASS",
    "limitations": [
        "Synthetic static portfolio, not historical data.",
        "No pending orders or live execution lifecycle.",
        "No empirical return or performance conclusions.",
        "Subset of FMA constraints for mathematical testing.",
        "No claim of confirmatory evidence.",
    ],
}

output = ROOT / "audit/p2_feasibility_toy.json"
output.write_text(json.dumps(result, indent=2) + "\n")

print(json.dumps({
    "status": result["status"],
    "maximum_new_shares_per_asset": MAX_NEW_SHARES,
    "cases": {
        name: {
            "status": case["status"],
            "minimum_planned_risk":
                case["minimum_planned_risk"],
        }
        for name, case in cases.items()
    },
    "report": str(output),
}, indent=2))
