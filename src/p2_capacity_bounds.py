import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path.home() / "FMA_Independent_Research"
AUDIT = ROOT / "audit"

def read_csv(filename):
    with (AUDIT / filename).open(newline="") as f:
        return list(csv.DictReader(f))

daily = read_csv("historical_signal_daily.csv")
signals = read_csv("historical_signal_candidates.csv")
validation = json.loads(
    (AUDIT / "signal_differential_summary.json").read_text()
)

assert validation["status"] == "PASS"
assert len(daily) == 282
assert len(signals) == 1229

# Original FMA constraints; still an optimistic relaxation.
NAME_CAP = 0.072 / 1.01
SINGLE_RISK_CAP = 0.005
PORTFOLIO_RISK_CAP = 0.04
SECTOR_CAP = 0.24
MAX_POSITIONS = 14
CASH_CAP = 0.95
RISK_BUFFER = 0.01 + 0.0005
DEPLOYMENT_TARGET = 0.90

by_date = defaultdict(list)

for row in signals:
    fraction = float(row["stop_fraction"])
    if not (0.015 <= fraction <= 0.10):
        raise ValueError("Unexpected stop fraction")

    risk_per_dollar = fraction + RISK_BUFFER

    # Upper bound on capital allocated to this name.
    # Ignoring fees and integer shares makes it optimistic.
    cap = min(
        NAME_CAP,
        SINGLE_RISK_CAP / risk_per_dollar,
    )

    by_date[row["date"]].append({
        "ticker": row["ticker"],
        "sector": row["sector"],
        "cap": cap,
        "risk_per_dollar": risk_per_dollar,
    })

def relaxed_risk_knapsack(items):
    """Maximum possible investment using the 4% risk budget,
    ignoring sector and position-count restrictions."""
    remaining = PORTFOLIO_RISK_CAP
    invested = 0.0

    for item in sorted(items, key=lambda x: x["risk_per_dollar"]):
        rate = item["risk_per_dollar"]
        allocation = min(item["cap"], remaining / rate)
        invested += allocation
        remaining -= allocation * rate

        if remaining <= 1e-12:
            break

    return invested

def capacity_bounds(items):
    sectors = defaultdict(float)

    for item in items:
        sectors[item["sector"]] += item["cap"]

    # Independent upper bounds. Their minimum remains an upper bound.
    name_bound = sum(x["cap"] for x in items)
    slot_bound = sum(
        sorted((x["cap"] for x in items), reverse=True)
        [:MAX_POSITIONS]
    )
    sector_bound = sum(
        min(SECTOR_CAP, value)
        for value in sectors.values()
    )
    risk_bound = relaxed_risk_knapsack(items)

    upper = min(
        1.0,
        CASH_CAP,
        name_bound,
        slot_bound,
        sector_bound,
        risk_bound,
    )

    return {
        "name_bound": name_bound,
        "slot_bound": slot_bound,
        "sector_bound": sector_bound,
        "risk_bound": risk_bound,
        "capital_upper_bound": upper,
        "eligible_sectors": len(sectors),
    }

results = []

for record in daily:
    date = record["date"]
    items = by_date[date]

    if len(items) != int(record["eligible_signals"]):
        raise AssertionError(f"Signal count mismatch: {date}")

    bounds = capacity_bounds(items)
    results.append({
        "date": date,
        "signals": len(items),
        **bounds,
        "classification": (
            "PROVEN_INFEASIBLE_UNDER_RELAXATION"
            if bounds["capital_upper_bound"] <
               DEPLOYMENT_TARGET - 1e-10
            else "NOT_RULED_OUT"
        ),
    })

# Basic mathematical consistency: these are upper bounds.
for row in results:
    assert row["capital_upper_bound"] >= -1e-12
    assert row["capital_upper_bound"] <= 0.95 + 1e-12
    assert (
        row["capital_upper_bound"]
        <= row["name_bound"] + 1e-12
    )

output_csv = AUDIT / "historical_capacity_bounds.csv"
with output_csv.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0]))
    writer.writeheader()
    writer.writerows(results)

upper_values = [r["capital_upper_bound"] for r in results]
impossible = sum(
    r["classification"] == "PROVEN_INFEASIBLE_UNDER_RELAXATION"
    for r in results
)

count_only_impossible = sum(
    int(r["eligible_signals"]) < math.ceil(0.9 / 0.072)
    for r in daily
)

assert impossible >= count_only_impossible

summary = {
    "schema": "FMA_HISTORICAL_CAPACITY_BOUNDS_V1",
    "status": "EXPLORATORY_UPPER_BOUND_ANALYSIS",
    "sessions": len(results),
    "historical_signal_events": len(signals),
    "deployment_target": DEPLOYMENT_TARGET,
    "count_only_proven_impossible": count_only_impossible,
    "constraint_bound_proven_impossible": impossible,
    "additional_impossible_sessions": (
        impossible - count_only_impossible
    ),
    "not_ruled_out_sessions": len(results) - impossible,
    "mean_optimistic_capacity_upper_bound": (
        statistics.mean(upper_values)
    ),
    "median_optimistic_capacity_upper_bound": (
        statistics.median(upper_values)
    ),
    "maximum_optimistic_capacity_upper_bound": max(upper_values),
    "limitations": [
        "Zero incumbent positions and no auxiliary assets.",
        "Optimistic fractional relaxation; not a MILP solution.",
        "Ignores fixed commissions and integer-share rounding.",
        "Ignores some liquidity and order-lifecycle restrictions.",
        "90% is a hypothetical immediate-deployment scenario.",
        "Not a daily FMA competition compliance test.",
        "Fixed-current-constituent exploratory sample, not PIT.",
        "Cannot prove feasibility when upper bound exceeds 90%.",
        "Not a returns backtest or causal analysis.",
    ],
}

output_json = AUDIT / "historical_capacity_bounds_summary.json"
output_json.write_text(json.dumps(summary, indent=2) + "\n")

print("=== HISTORICAL CAPACITY BOUNDS ===")
print(json.dumps(summary, indent=2))
print("Report:", output_csv)
