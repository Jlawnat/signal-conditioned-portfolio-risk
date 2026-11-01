import ast
import hashlib
import json
import math
from pathlib import Path

ROOT = Path.home() / "FMA_Independent_Research"
FMA = Path.home() / "FMA_Competition/fma_mpb_v41_20261013/fma_mpb_v41"

GAP = 0.01
SLIPPAGE = 0.0005
FEE = 10.0
PER_POSITION_CAP = 0.005
PORTFOLIO_CAP = 0.04
POSITION_WEIGHT_CAP = 0.072

checks = []

def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)

def close(a, b):
    return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-8)

def source_tree(filename):
    return ast.parse((FMA / filename).read_text())

def config_value(filename, class_name, field):
    tree = source_tree(filename)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if (isinstance(item, ast.AnnAssign)
                    and isinstance(item.target, ast.Name)
                    and item.target.id == field):
                    return ast.literal_eval(item.value)
    raise ValueError(f"Missing config: {class_name}.{field}")

# Confirm the frozen source still defines the values used here.
parameters = [
    ("momentum_pullback_breakout.py", "PullbackConfig",
     "risk_per_position", PER_POSITION_CAP),
    ("momentum_pullback_breakout.py", "PullbackConfig",
     "portfolio_planned_risk_cap", PORTFOLIO_CAP),
    ("momentum_pullback_breakout.py", "PullbackConfig",
     "gap_buffer", GAP),
    ("config.py", "StrategyConfig",
     "assumed_slippage_bps", 5.0),
    ("config.py", "StrategyConfig",
     "position_buffer_cap", POSITION_WEIGHT_CAP),
    ("config.py", "ContestConfig",
     "commission_per_trade", FEE),
]

for filename, cls, field, expected in parameters:
    actual = config_value(filename, cls, field)
    check(f"CONFIG_{field}", close(actual, expected))

# Static AST check against the actual frozen _risk_for formula.
tree = source_tree("competition_deployment.py")
matches = [
    n for n in tree.body
    if isinstance(n, ast.FunctionDef) and n.name == "_risk_for"
]
check("HELPER_EXISTS", len(matches) == 1)
check("HELPER_SINGLE_RETURN",
      len(matches[0].body) == 1
      and isinstance(matches[0].body[0], ast.Return))

expected_expr = ast.parse(
    "q*(max(0.,px-stop)"
    "+px*(CFG.gap_buffer+STRAT.assumed_slippage_bps/10000))"
    "+(2*CONTEST.commission_per_trade if q else 0)",
    mode="eval"
).body

check(
    "HELPER_FORMULA_MATCH",
    ast.dump(matches[0].body[0].value) == ast.dump(expected_expr)
)

# Standalone model: no import or execution of frozen FMA modules.
def supplemental_risk(q, price, stop):
    return (
        q * (max(0.0, price - stop) + price * (GAP + SLIPPAGE))
        + (2 * FEE if q else 0)
    )

def mpb_new_risk(q, price, stop):
    if q == 0:
        return 0.0
    if not (isinstance(q, int) and q > 0 and 0 < stop < price):
        raise ValueError("Invalid new-position inputs")
    return q * ((price - stop) + price * (GAP + SLIPPAGE)) + 2 * FEE

def mpb_held_risk(q, price, stop):
    if not (isinstance(q, int) and q >= 0 and price > 0 and stop > 0):
        raise ValueError("Invalid holding inputs")
    return q * (max(0.0, price - stop) + GAP * price)

def unmanaged_holding_risk_fraction():
    # Original MPB reserves the full portfolio cap when
    # holding risk metadata cannot be safely managed.
    return PORTFOLIO_CAP

def risk_budget_dollars(nav, risk_already_used_fraction):
    return nav * min(
        PER_POSITION_CAP,
        max(0.0, PORTFOLIO_CAP - risk_already_used_fraction)
    )

def shares_from_risk_budget(nav, used_fraction, price, stop):
    per_share = (price - stop) + price * (GAP + SLIPPAGE)
    if not (nav > 0 and 0 < stop < price and per_share > 0):
        raise ValueError("Invalid sizing inputs")
    budget = risk_budget_dollars(nav, used_fraction)
    return max(0, math.floor((budget - 2 * FEE) / per_share))

# Reference example: $1m NAV, $100 price, $95 stop.
nav, price, stop, q = 1_000_000.0, 100.0, 95.0, 100

check("MPB_NEW_RISK",
      close(mpb_new_risk(q, price, stop), 625.0))
check("MPB_HELD_RISK",
      close(mpb_held_risk(q, price, stop), 600.0))
check("SUPPLEMENTAL_RISK",
      close(supplemental_risk(q, price, stop), 625.0))
check("NEW_AND_SUPPLEMENTAL_MATCH",
      close(mpb_new_risk(q, price, stop),
            supplemental_risk(q, price, stop)))

check("ZERO_SHARES", close(supplemental_risk(0, price, stop), 0))
check("NEW_ZERO_SHARES", close(mpb_new_risk(0, price, stop), 0))

check("SINGLE_POSITION_BUDGET",
      close(risk_budget_dollars(nav, 0), 5000.0))
check("REMAINING_PORTFOLIO_BUDGET",
      close(risk_budget_dollars(nav, 0.039), 1000.0))
check("EXHAUSTED_RISK_BUDGET",
      shares_from_risk_budget(nav, 0.04, price, stop) == 0)

risk_shares = shares_from_risk_budget(nav, 0, price, stop)
check("INTEGER_RISK_SIZING", risk_shares == 823)
check("RISK_CAP_RESPECTED",
      mpb_new_risk(risk_shares, price, stop) <= 5000.0)
check("NEXT_SHARE_EXCEEDS_RISK_CAP",
      mpb_new_risk(risk_shares + 1, price, stop) > 5000.0)

position_shares = math.floor(
    POSITION_WEIGHT_CAP * nav / (price * (1 + GAP))
)
check("POSITION_CAP_SIZING", position_shares == 712)

check("UNMANAGED_HOLDING_BLOCK",
      close(unmanaged_holding_risk_fraction(), 0.04))

try:
    mpb_new_risk(10, 100, 105)
except ValueError:
    check("INVALID_NEW_STOP_REJECTED", True)
else:
    raise AssertionError("Invalid stop was accepted")

source_hashes = {
    name: hashlib.sha256((FMA / name).read_bytes()).hexdigest()
    for name in [
        "config.py",
        "momentum_pullback_breakout.py",
        "competition_deployment.py",
    ]
}

result = {
    "schema": "FMA_RISK_MODEL_CHECK_V1",
    "status": "PASS",
    "checks_passed": len(checks),
    "checks": checks,
    "reference_example": {
        "nav": nav,
        "price": price,
        "stop": stop,
        "shares": q,
        "new_risk_dollars": mpb_new_risk(q, price, stop),
        "held_risk_dollars": mpb_held_risk(q, price, stop),
        "risk_limited_shares": risk_shares,
        "position_cap_limited_shares": position_shares,
    },
    "source_sha256": source_hashes,
    "limitation": (
        "Static source-formula and standalone numerical checks only. "
        "Not a full engine execution, lifecycle validation, "
        "or independent backtest."
    ),
}

output = ROOT / "audit/p1_risk_model_check.json"
output.write_text(json.dumps(result, indent=2) + "\n")

print(json.dumps({
    "status": result["status"],
    "checks_passed": result["checks_passed"],
    "reference_example": result["reference_example"],
    "report": str(output),
}, indent=2))
