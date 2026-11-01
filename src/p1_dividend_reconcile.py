from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from collections import Counter
import csv
import json

home = Path.home()
root = (home / "FMA_Competition" / "Market_Refresh_Runs"
        / "manual_full_20261031T061137Z_432cf6e9"
        / "market_bundle")
out = home / "FMA_Independent_Research" / "audit"

manifest = json.loads((root / "manifest.json").read_text())
with (out / "corporate_action_event_matches.csv").open(
    newline="", encoding="utf-8-sig"
) as f:
    flags = list(csv.DictReader(f))

ny = ZoneInfo("America/New_York")
cache = {}

def as_date(timestamp):
    t = float(timestamp)
    if t > 1e12:
        t /= 1000
    return datetime.fromtimestamp(
        t, tz=timezone.utc
    ).astimezone(ny).date().isoformat()

def dividend_amount(value):
    if isinstance(value, dict):
        value = value.get("amount", value.get("dividend"))
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def previous_close(ticker, day):
    if ticker not in cache:
        path = root / "raw" / f"{ticker}.csv"
        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            cols = {x.lower(): x for x in reader.fieldnames}
            rows = sorted(
                (r[cols["date"]][:10], float(r[cols["close"]]))
                for r in reader
            )
        cache[ticker] = rows

    rows = cache[ticker]
    for i, (d, _) in enumerate(rows):
        if d == day:
            return rows[i-1][1] if i > 0 else None
    return None

results = []
for row in flags:
    if row["reason"] != "ADJUSTMENT_FACTOR_CHANGE_OVER_1PCT":
        continue

    ticker, day = row["ticker"], row["date"]
    panel = manifest["panels"].get(f"adjusted/{ticker}.csv", {})
    actions = panel.get("attributes", {}).get(
        "corporate_action_events", {}
    )

    divs = actions.get("dividends", {})
    splits = actions.get("splits", {})
    exact = [
        dividend_amount(value)
        for stamp, value in divs.items()
        if as_date(stamp) == day
    ]
    split_same_day = any(
        as_date(stamp) == day for stamp in splits
    )

    previous = previous_close(ticker, day)
    observed = float(row["factor_change"])
    valid = [v for v in exact if v is not None]
    amount = sum(valid) if len(valid) == len(exact) else None

    expected = None
    difference_bp = None

    if split_same_day:
        status = "SPLIT_SAME_DAY_REVIEW"
    elif not exact:
        status = "NO_DIVIDEND_EVENT"
    elif amount is None:
        status = "UNREADABLE_DIVIDEND_AMOUNT"
    elif previous is None or previous <= 0:
        status = "MISSING_PREVIOUS_CLOSE"
    elif not (0 < amount < previous):
        status = "INVALID_DIVIDEND_RATIO"
    else:
        expected = 1 / (1 - amount / previous) - 1
        difference_bp = (observed - expected) * 10000
        status = (
            "INTERNAL_NUMERIC_PASS"
            if abs(difference_bp) <= 5
            else "NUMERIC_DISCREPANCY"
        )

    results.append({
        "ticker": ticker,
        "date": day,
        "dividend_amount": amount,
        "previous_raw_close": previous,
        "observed_factor_change": observed,
        "expected_factor_change": expected,
        "difference_basis_points": difference_bp,
        "status": status
    })

csv_path = out / "dividend_reconciliation.csv"
with csv_path.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0]))
    writer.writeheader()
    writer.writerows(results)

summary = {
    "events_checked": len(results),
    "status_counts": dict(Counter(r["status"] for r in results)),
    "tolerance_basis_points": 5,
    "note": (
        "Same-provider numerical consistency only. "
        "Not independent corporate-action verification."
    )
}
json_path = out / "dividend_reconciliation_summary.json"
json_path.write_text(json.dumps(summary, indent=2))

print(json.dumps(summary, indent=2))
print("Reports:", csv_path, json_path)
