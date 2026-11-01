import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

AUDIT = Path.home() / "FMA_Independent_Research/audit"

def read_csv(name):
    with (AUDIT / name).open(newline="") as f:
        return list(csv.DictReader(f))

daily = read_csv("historical_signal_daily.csv")
signals = read_csv("historical_signal_candidates.csv")
previous = read_csv("historical_capacity_bounds.csv")

assert len(daily) == len(previous) == 282
assert len(signals) == 1229

BUDGETS = [0.02, 0.03, 0.04]
DEPLOYMENTS = [0.10, 0.25, 0.50, 0.75, 0.90]

NAME_CAP = 0.072 / 1.01
POSITION_RISK = 0.005
SECTOR_CAP = 0.24
MAX_POSITIONS = 14
CASH_LIMIT = 0.95

by_date = defaultdict(list)

for r in signals:
    risk_rate = float(r["stop_fraction"]) + 0.0105
    cap = min(NAME_CAP, POSITION_RISK / risk_rate)
    by_date[r["date"]].append({
        "sector": r["sector"],
        "cap": cap,
        "risk_rate": risk_rate,
    })

def capacity(items, budget):
    sector = defaultdict(float)
    for x in items:
        sector[x["sector"]] += x["cap"]

    name_bound = sum(x["cap"] for x in items)
    slot_bound = sum(
        sorted((x["cap"] for x in items), reverse=True)
        [:MAX_POSITIONS]
    )
    sector_bound = sum(
        min(SECTOR_CAP, value)
        for value in sector.values()
    )

    remaining = budget
    risk_bound = 0.0

    for x in sorted(items, key=lambda z: z["risk_rate"]):
        allocation = min(
            x["cap"],
            max(0.0, remaining) / x["risk_rate"]
        )
        risk_bound += allocation
        remaining -= allocation * x["risk_rate"]

    return min(
        1.0, CASH_LIMIT, name_bound,
        slot_bound, sector_bound, risk_bound
    )

rows = []
prev_by_date = {x["date"]: x for x in previous}

for day in daily:
    date = day["date"]
    items = by_date[date]

    assert len(items) == int(day["eligible_signals"])

    for budget in BUDGETS:
        upper = capacity(items, budget)

        if budget == 0.04:
            old = float(
                prev_by_date[date]["capital_upper_bound"]
            )
            assert abs(old - upper) < 1e-10, (
                "Previous bounds disagree: " + date
            )

        rows.append({
            "date": date,
            "risk_budget": budget,
            "signals": len(items),
            "capacity_upper_bound": upper,
        })

path = AUDIT / "risk_deployment_surface.csv"

with path.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

grid = []
for budget in BUDGETS:
    values = [
        r["capacity_upper_bound"]
        for r in rows if r["risk_budget"] == budget
    ]

    for target in DEPLOYMENTS:
        impossible = sum(
            value < target - 1e-10 for value in values
        )
        grid.append({
            "risk_budget": budget,
            "deployment_target": target,
            "proven_impossible_sessions": impossible,
            "not_ruled_out_sessions": len(values)-impossible,
            "proven_impossible_pct": round(
                100 * impossible / len(values), 2
            ),
        })

summary = {
    "schema": "FMA_RISK_DEPLOYMENT_SURFACE_V1",
    "status": "EXPLORATORY_RELAXED_UPPER_BOUNDS",
    "historical_sessions": len(daily),
    "scenario_count": len(grid),
    "matched_previous_4pct_bounds": True,
    "scenario_grid": grid,
    "limitations": [
        "Zero existing positions and no auxiliary assets.",
        "Upper bounds prove impossibility only.",
        "Not exact feasible portfolio solutions.",
        "2% and 3% are hypothetical constant budgets.",
        "No historical multi-period portfolio simulation.",
        "Fixed-current-constituent research universe.",
    ],
}

output = AUDIT / "risk_deployment_surface_summary.json"
output.write_text(json.dumps(summary, indent=2) + "\n")

print("=== RISK DEPLOYMENT SURFACE ===")
print(json.dumps(summary, indent=2))
print("CSV:", path)
