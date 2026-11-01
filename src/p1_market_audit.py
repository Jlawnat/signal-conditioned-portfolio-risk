from pathlib import Path
from datetime import date
from collections import Counter
import csv
import hashlib
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

if not ROOT.is_dir():
    raise SystemExit(f"Market bundle missing: {ROOT}")

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def norm(value):
    return "".join(c for c in value.lower() if c.isalnum())

def kind_of(path):
    folders = [p.lower() for p in path.relative_to(ROOT).parts[:-1]]
    if any("adjust" in p for p in folders):
        return "adjusted"
    if any("raw" in p for p in folders):
        return "raw"
    return None

def inspect(path, kind):
    record = {
        "ticker": path.stem,
        "kind": kind,
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256(path),
        "rows": 0,
        "valid_dates": 0,
        "first_date": "",
        "last_date": "",
        "duplicate_dates": 0,
        "out_of_order": 0,
        "invalid_dates": 0,
        "invalid_numbers": 0,
        "invalid_ohlc": 0,
        "negative_volume": 0,
        "long_gaps": 0,
        "future_dates": 0,
        "under_270_rows": False,
        "status": "UNKNOWN"
    }
    dates = set()
    previous = None

    try:
        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            names = {norm(n): n for n in (reader.fieldnames or [])}
            required = ("date", "open", "high", "low", "close", "volume")

            if not all(x in names for x in required):
                record["status"] = "SCHEMA_UNKNOWN"
                return record, dates

            for row in reader:
                record["rows"] += 1

                try:
                    d = date.fromisoformat(row[names["date"]][:10])
                except (ValueError, TypeError, KeyError):
                    record["invalid_dates"] += 1
                    continue

                if d in dates:
                    record["duplicate_dates"] += 1
                dates.add(d)

                if previous is not None:
                    if d < previous:
                        record["out_of_order"] += 1
                    if (d - previous).days > 10:
                        record["long_gaps"] += 1
                previous = d

                if d > date(2026, 10, 30):
                    record["future_dates"] += 1

                try:
                    o, h, l, c, v = [
                        float(row[names[x]])
                        for x in ("open", "high", "low", "close", "volume")
                    ]
                    if not all(map(math.isfinite, (o, h, l, c, v))):
                        raise ValueError("Non-finite")

                    if min(o, h, l, c) <= 0 or h < max(o, c, l) or l > min(o, c):
                        record["invalid_ohlc"] += 1
                    if v < 0:
                        record["negative_volume"] += 1

                except (ValueError, TypeError, KeyError):
                    record["invalid_numbers"] += 1

    except (OSError, UnicodeError, csv.Error) as e:
        record["status"] = "READ_ERROR:" + type(e).__name__
        return record, dates

    record["valid_dates"] = len(dates)
    if dates:
        record["first_date"] = min(dates).isoformat()
        record["last_date"] = max(dates).isoformat()

    record["under_270_rows"] = len(dates) < 270

    errors = [
        record[x] for x in (
            "duplicate_dates", "out_of_order", "invalid_dates",
            "invalid_numbers", "invalid_ohlc",
            "negative_volume", "future_dates"
        )
    ]

    record["status"] = "FLAGGED" if any(errors) else "BASIC_CHECK_PASS"
    return record, dates

results = []
pairs = {}
unclassified = []

for path in sorted(ROOT.rglob("*.csv")):
    kind = kind_of(path)
    if kind is None:
        unclassified.append(str(path.relative_to(ROOT)))
        continue

    record, dates = inspect(path, kind)
    results.append(record)
    key = (path.stem.upper(), kind)
    pairs.setdefault(key, []).append(dates)

tickers = sorted(set(t for t, _ in pairs))
pair_results = []

for ticker in tickers:
    raw = pairs.get((ticker, "raw"), [])
    adj = pairs.get((ticker, "adjusted"), [])
    pair_results.append({
        "ticker": ticker,
        "raw_files": len(raw),
        "adjusted_files": len(adj),
        "dates_match": (
            len(raw) == len(adj) == 1 and raw[0] == adj[0]
        ),
        "date_difference_count": (
            len(raw[0] ^ adj[0])
            if len(raw) == len(adj) == 1 else ""
        )
    })

fields = list(results[0]) if results else []
with (OUT / "data_quality.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(results)

with (OUT / "pair_audit.csv").open("w", newline="") as f:
    writer = csv.DictWriter(
        f, fieldnames=[
            "ticker", "raw_files", "adjusted_files",
            "dates_match", "date_difference_count"
        ]
    )
    writer.writeheader()
    writer.writerows(pair_results)

summary = {
    "audit_type": "P1_READ_ONLY_MARKET_DATA",
    "source": str(ROOT),
    "csv_files_checked": len(results),
    "unique_tickers_in_panels": len(tickers),
    "file_status": dict(Counter(x["status"] for x in results)),
    "under_270_rows": sum(x["under_270_rows"] for x in results),
    "date_mismatched_or_unpaired": sum(
        not x["dates_match"] for x in pair_results
    ),
    "long_gap_flags": sum(x["long_gaps"] for x in results),
    "unclassified_csv": unclassified,
    "limitations": [
        "No exchange-calendar verification",
        "No point-in-time membership certification",
        "No corporate-action certification",
        "No independent market-price verification",
        "No historical backtest performed"
    ]
}

with (OUT / "data_quality_summary.json").open("w") as f:
    json.dump(summary, f, indent=2)

print(json.dumps(summary, indent=2))
print("\nReports saved to:", OUT)
