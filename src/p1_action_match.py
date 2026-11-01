from pathlib import Path
from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo
from collections import defaultdict, Counter
import json
import csv

home = Path.home()
root = (
    home / "FMA_Competition"
    / "Market_Refresh_Runs"
    / "manual_full_20261031T061137Z_432cf6e9"
    / "market_bundle"
)
out = home / "FMA_Independent_Research" / "audit"

manifest = json.loads(
    (root / "manifest.json").read_text(encoding="utf-8")
)

# Convert provider Unix timestamps to US market calendar dates.
ny = ZoneInfo("America/New_York")

def event_date(key):
    try:
        timestamp = float(key)
        if timestamp > 1e12:
            timestamp /= 1000
        return datetime.fromtimestamp(
            timestamp, tz=timezone.utc
        ).astimezone(ny).date()
    except (ValueError, TypeError, OverflowError, OSError):
        return None

events = defaultdict(list)
event_counts = Counter()
invalid_event_timestamps = 0
verification = Counter()

for name, panel in manifest.get("panels", {}).items():
    if not name.startswith("adjusted/"):
        continue
    ticker = Path(name).stem.upper()
    attrs = panel.get("attributes", {})
    verification[str(attrs.get(
        "corporate_actions_verified", "MISSING"
    ))] += 1

    actions = attrs.get("corporate_action_events", {})
    if not isinstance(actions, dict):
        continue

    for kind in ("dividends", "splits"):
        records = actions.get(kind, {})
        if not isinstance(records, dict):
            continue

        for timestamp in records:
            d = event_date(timestamp)
            if d is None:
                invalid_event_timestamps += 1
                continue
            events[ticker].append((d, kind))
            event_counts[kind] += 1

input_file = out / "price_adjustment_flags.csv"
output_file = out / "corporate_action_event_matches.csv"

matches = []
counts = Counter()
by_reason = defaultdict(Counter)

with input_file.open(newline="", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        ticker = row["ticker"].upper()
        observed = date.fromisoformat(row["date"][:10])
        reason = row["reason"]

        relevant = events.get(ticker, [])
        exact = [
            (d, k) for d, k in relevant
            if d == observed
        ]
        nearby = [
            (d, k) for d, k in relevant
            if 0 < abs((d - observed).days) <= 1
        ]

        if exact:
            status = "EXACT_PROVIDER_EVENT"
            selected = exact
        elif nearby:
            status = "NEAR_PROVIDER_EVENT_REVIEW"
            selected = nearby
        else:
            status = "NO_MATCHING_PROVIDER_EVENT"
            selected = []

        result = dict(row)
        result["match_status"] = status
        result["event_types"] = "|".join(
            sorted({k for _, k in selected})
        )
        result["event_dates"] = "|".join(
            sorted({d.isoformat() for d, _ in selected})
        )

        matches.append(result)
        counts[status] += 1
        by_reason[reason][status] += 1

fields = (
    list(matches[0])
    if matches else [
        "ticker", "date", "reason", "match_status",
        "event_types", "event_dates"
    ]
)

with output_file.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(matches)

summary = {
    "audit": "P1_CORPORATE_ACTION_EVENT_MATCHING",
    "total_price_flag_rows": len(matches),
    "unique_flag_dates": len({
        (r["ticker"], r["date"]) for r in matches
    }),
    "provider_event_counts": dict(event_counts),
    "invalid_event_timestamps": invalid_event_timestamps,
    "corporate_actions_verified": dict(verification),
    "match_counts": dict(counts),
    "matches_by_reason": {
        reason: dict(c)
        for reason, c in by_reason.items()
    },
    "limitations": [
        "Matching is against the same provider's metadata",
        "Event timestamps interpreted in America/New_York",
        "Exact matching does not establish event authenticity",
        "Nearby matches require manual review",
        "No comparison of expected and observed adjustment amounts",
        "Split-adjusted raw prices may not jump on split dates",
        "Missing event metadata does not prove a price error",
        "No trading or portfolio backtest performed"
    ]
}

summary_path = out / "corporate_action_match_summary.json"
summary_path.write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
)

print(json.dumps(summary, indent=2))
print("\nReports:")
print(output_file)
print(summary_path)
