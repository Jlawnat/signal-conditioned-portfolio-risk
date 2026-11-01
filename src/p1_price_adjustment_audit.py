from pathlib import Path
from collections import Counter
import csv
import json
import math

HOME = Path.home()
ROOT = (
    HOME / "FMA_Competition"
    / "Market_Refresh_Runs"
    / "manual_full_20261031T061137Z_432cf6e9"
    / "market_bundle"
)
OUT = HOME / "FMA_Independent_Research" / "audit"
OUT.mkdir(parents=True, exist_ok=True)

def read_prices(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        cols = {
            name.strip().lower(): name
            for name in (reader.fieldnames or [])
        }
        required = ("date", "open", "high", "low", "close")
        if not all(k in cols for k in required):
            raise ValueError(f"Missing columns in {path}")

        records = {}
        for row in reader:
            d = row[cols["date"]].strip()[:10]
            values = {
                k: float(row[cols[k]])
                for k in ("open", "high", "low", "close")
            }
            if not all(
                math.isfinite(v) and v > 0
                for v in values.values()
            ):
                raise ValueError(f"Invalid prices: {path}, {d}")
            records[d] = values
        return records

flags = []
summary = Counter()
raw_dir = ROOT / "raw"
adj_dir = ROOT / "adjusted"

for raw_file in sorted(raw_dir.glob("*.csv")):
    ticker = raw_file.stem
    adj_file = adj_dir / raw_file.name
    if not adj_file.exists():
        summary["missing_adjusted_panel"] += 1
        continue

    raw = read_prices(raw_file)
    adj = read_prices(adj_file)
    summary["pairs_checked"] += 1

    dates = sorted(set(raw) & set(adj))
    previous = None

    for d in dates:
        r, a = raw[d], adj[d]
        factors = [
            a[k] / r[k]
            for k in ("open", "high", "low", "close")
        ]
        factor = factors[-1]

        reasons = []

        if max(factors) / min(factors) - 1 > 0.0001:
            reasons.append("OHLC_FACTOR_INCONSISTENCY")

        if previous is not None:
            prev_r, prev_a, prev_factor = previous

            raw_change = r["close"] / prev_r - 1
            adj_change = a["close"] / prev_a - 1
            factor_change = factor / prev_factor - 1

            if abs(raw_change) > 0.35:
                reasons.append("LARGE_RAW_CLOSE_MOVE")
            if abs(adj_change) > 0.35:
                reasons.append("LARGE_ADJUSTED_CLOSE_MOVE")
            if abs(factor_change) > 0.01:
                reasons.append("ADJUSTMENT_FACTOR_CHANGE_OVER_1PCT")
        else:
            raw_change = None
            adj_change = None
            factor_change = None

        for reason in reasons:
            flags.append({
                "ticker": ticker,
                "date": d,
                "reason": reason,
                "raw_close": r["close"],
                "adjusted_close": a["close"],
                "adjustment_factor": factor,
                "raw_return": raw_change,
                "adjusted_return": adj_change,
                "factor_change": factor_change
            })
            summary[reason] += 1

        previous = (r["close"], a["close"], factor)

fields = [
    "ticker", "date", "reason",
    "raw_close", "adjusted_close",
    "adjustment_factor", "raw_return",
    "adjusted_return", "factor_change"
]

with (OUT / "price_adjustment_flags.csv").open(
    "w", newline=""
) as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(flags)

report = {
    "audit": "P1_PRICE_ADJUSTMENT_DIAGNOSTICS",
    "pairs_checked": summary["pairs_checked"],
    "flags_total": len(flags),
    "flag_counts": {
        k: v for k, v in summary.items()
        if k != "pairs_checked"
    },
    "limitations": [
        "Flags are diagnostics, not verified errors",
        "Dividend and split events not independently certified",
        "No external market-data comparison",
        "No historical portfolio backtest performed"
    ]
}

with (OUT / "price_adjustment_summary.json").open("w") as f:
    json.dump(report, f, indent=2)

print(json.dumps(report, indent=2))
print("Output:", OUT)
