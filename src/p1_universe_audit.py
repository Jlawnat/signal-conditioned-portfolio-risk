from pathlib import Path
from datetime import date
from collections import Counter
import csv
import json

root = (
    Path.home() / "FMA_Competition"
    / "Market_Refresh_Runs"
    / "manual_full_20261031T061137Z_432cf6e9"
    / "market_bundle"
)
out = Path.home() / "FMA_Independent_Research" / "audit"
out.mkdir(parents=True, exist_ok=True)

with (root / "universe.csv").open(newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    headers = reader.fieldnames or []
    rows = list(reader)

ticker_col = next(
    (h for h in headers if h.strip().lower() in ("ticker", "symbol")),
    None
)
if ticker_col is None:
    raise SystemExit(f"Unknown universe columns: {headers}")

universe = [
    (r.get(ticker_col) or "").strip().upper()
    for r in rows
]
if not all(universe) or len(universe) != len(set(universe)):
    raise SystemExit("Universe has blank or duplicate tickers")

raw_dir = root / "raw"
adj_dir = root / "adjusted"

raw_files = {p.stem.upper(): p for p in raw_dir.glob("*.csv")}
adj_files = {p.stem.upper(): p for p in adj_dir.glob("*.csv")}

def dates_of(path):
    if path is None:
        return set()
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        column = next(
            (h for h in (reader.fieldnames or [])
             if h.strip().lower() == "date"),
            None
        )
        if column is None:
            raise ValueError(f"Missing date column: {path}")
        return {
            date.fromisoformat(row[column].strip()[:10])
            for row in reader
        }

if "SPY" not in raw_files or "SPY" not in adj_files:
    raise SystemExit("SPY reference panels are missing")

spy_raw = dates_of(raw_files["SPY"])
spy_adj = dates_of(adj_files["SPY"])
if spy_raw != spy_adj or len(spy_raw) < 270:
    raise SystemExit("SPY calendar mismatch or insufficient history")

reference = sorted(spy_raw)[-270:]
latest = reference[-1]

results = []
for ticker in universe:
    rp = raw_files.get(ticker)
    ap = adj_files.get(ticker)
    raw = dates_of(rp)
    adjusted = dates_of(ap)
    common = raw & adjusted

    missing = sum(d not in common for d in reference)

    if rp is None or ap is None:
        status = "MISSING_PANEL"
    elif raw != adjusted:
        status = "RAW_ADJUSTED_DATE_MISMATCH"
    elif missing:
        status = "INCOMPLETE_LAST_270_SPY_DATES"
    else:
        status = "CALENDAR_WARMUP_PASS"

    results.append({
        "ticker": ticker,
        "raw_exists": rp is not None,
        "adjusted_exists": ap is not None,
        "raw_days": len(raw),
        "adjusted_days": len(adjusted),
        "missing_last_270": missing,
        "status": status
    })

with (out / "universe_lineage.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0]))
    writer.writeheader()
    writer.writerows(results)

support = sorted((set(raw_files) | set(adj_files)) - set(universe))
summary = {
    "universe_count": len(universe),
    "raw_panel_count": len(raw_files),
    "adjusted_panel_count": len(adj_files),
    "reference_calendar": "SPY",
    "reference_end": latest.isoformat(),
    "reference_sessions": len(reference),
    "status_counts": dict(Counter(x["status"] for x in results)),
    "support_or_non_universe_symbols": support,
    "limitations": [
        "Fixed current universe, not PIT membership",
        "SPY dates used as a proxy exchange calendar",
        "No corporate-action validation",
        "No independent provider verification",
        "No backtesting performed"
    ]
}

with (out / "universe_coverage_summary.json").open("w") as f:
    json.dump(summary, f, indent=2)

print(json.dumps(summary, indent=2))
print("Saved audit reports to:", out)
