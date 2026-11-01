from pathlib import Path
from datetime import date
import csv
import json

home = Path.home()
root = (
    home / "FMA_Competition"
    / "Market_Refresh_Runs"
    / "manual_full_20261031T061137Z_432cf6e9"
    / "market_bundle"
)
out = home / "FMA_Independent_Research" / "audit"
out.mkdir(parents=True, exist_ok=True)

def dates_of(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        key = next(
            (x for x in columns if x.strip().lower() == "date"),
            None
        )
        if key is None:
            raise ValueError(f"Missing date column: {path}")
        return {
            date.fromisoformat(row[key].strip()[:10])
            for row in reader
        }

with (root / "universe.csv").open(
    newline="", encoding="utf-8-sig"
) as f:
    reader = csv.DictReader(f)
    ticker_key = next(
        (x for x in reader.fieldnames or []
         if x.strip().lower() in ("ticker", "symbol")),
        None
    )
    if ticker_key is None:
        raise ValueError("Missing ticker column")
    universe = [
        row[ticker_key].strip().upper() for row in reader
    ]

if len(universe) != 503 or len(set(universe)) != 503:
    raise ValueError("Unexpected stock universe")

raw_dir = root / "raw"
adj_dir = root / "adjusted"
sessions = sorted(dates_of(raw_dir / "SPY.csv"))

window = 270
if len(sessions) < window:
    raise ValueError("Insufficient SPY reference history")

counts = [0] * len(sessions)
ticker_rows = []

for ticker in universe:
    raw_path = raw_dir / f"{ticker}.csv"
    adj_path = adj_dir / f"{ticker}.csv"

    if not raw_path.exists() or not adj_path.exists():
        ticker_rows.append({
            "ticker": ticker,
            "eligible_days": 0,
            "first_eligible_date": "",
            "last_eligible_date": "",
            "status": "MISSING_PANEL"
        })
        continue

    common = dates_of(raw_path) & dates_of(adj_path)
    flags = [int(d in common) for d in sessions]

    rolling = sum(flags[:window])
    eligible_dates = []

    for i in range(window - 1, len(sessions)):
        if i > window - 1:
            rolling += flags[i] - flags[i - window]

        if rolling == window:
            counts[i] += 1
            eligible_dates.append(sessions[i])

    ticker_rows.append({
        "ticker": ticker,
        "eligible_days": len(eligible_dates),
        "first_eligible_date": (
            eligible_dates[0].isoformat()
            if eligible_dates else ""
        ),
        "last_eligible_date": (
            eligible_dates[-1].isoformat()
            if eligible_dates else ""
        ),
        "status": (
            "HAS_ELIGIBLE_DATES"
            if eligible_dates else "NO_ELIGIBLE_DATES"
        )
    })

daily_rows = []
for i in range(window - 1, len(sessions)):
    n = counts[i]
    daily_rows.append({
        "date": sessions[i].isoformat(),
        "eligible_stocks": n,
        "universe_size": len(universe),
        "coverage_pct": round(100 * n / len(universe), 4),
        "meets_95pct_gate": n / len(universe) >= 0.95
    })

def save_csv(name, records):
    with (out / name).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

save_csv("historical_coverage.csv", daily_rows)
save_csv("historical_eligibility_by_ticker.csv", ticker_rows)

passing = [r for r in daily_rows if r["meets_95pct_gate"]]

summary = {
    "universe": len(universe),
    "spy_reference_sessions": len(sessions),
    "warmup_sessions": window,
    "evaluated_dates": len(daily_rows),
    "first_evaluated_date": daily_rows[0]["date"],
    "last_evaluated_date": daily_rows[-1]["date"],
    "first_95pct_date": (
        passing[0]["date"] if passing else None
    ),
    "dates_meeting_95pct": len(passing),
    "latest_eligible_stocks": daily_rows[-1]["eligible_stocks"],
    "lowest_eligible_stocks": min(counts[window-1:]),
    "highest_eligible_stocks": max(counts[window-1:]),
    "limitations": [
        "Current fixed universe, not historical PIT membership",
        "SPY dates used as the reference calendar",
        "No corporate-action or price authenticity certification",
        "No portfolio backtest performed"
    ]
}

with (out / "historical_coverage_summary.json").open("w") as f:
    json.dump(summary, f, indent=2)

print(json.dumps(summary, indent=2))
print("Saved to:", out)
