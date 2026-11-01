import csv
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path.home() / "FMA_Independent_Research"
AUDIT = ROOT / "audit"
BUNDLE = (Path.home() / "FMA_Competition"
          / "Market_Refresh_Runs"
          / "manual_full_20261031T061137Z_432cf6e9"
          / "market_bundle")

with (AUDIT / "p3_tplus1_price_probe.csv").open(newline="") as f:
    rows = list(csv.DictReader(f))

manifest = json.loads((BUNDLE / "manifest.json").read_text())
panels = manifest["panels"]
cache = {}

def load_prices(ticker, kind):
    key = (ticker, kind)
    if key not in cache:
        path = BUNDLE / kind / f"{ticker}.csv"
        with path.open(newline="") as f:
            cache[key] = {
                r["Date"]: r for r in csv.DictReader(f)
            }
    return cache[key]

def event_date(key):
    try:
        ts = float(key)
        if 1_000_000_000 <= ts <= 2_500_000_000:
            return datetime.fromtimestamp(
                ts, ZoneInfo("America/New_York")
            ).date().isoformat()
    except (ValueError, TypeError, OverflowError):
        pass
    value = str(key)[:10]
    return value if len(value) == 10 and value[4] == "-" else None

def amount(value):
    if isinstance(value, dict):
        value = value.get("amount", value.get("dividend"))
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

exceptions = []

for r in rows:
    flagged = (
        r["status"] != "PRICE_ALIGNMENT_OK"
        or r["next_open_below_stop"] == "True"
    )
    if not flagged:
        continue

    output = dict(r)
    output["provider_event_types"] = ""
    output["event_reconciliation"] = "NOT_APPLICABLE"
    output["factor_change_bps"] = ""
    output["reconciliation_error_bps"] = ""

    if r["status"] == "CORPORATE_ACTION_REVIEW":
        ticker = r["ticker"]
        next_day = r["next_date"]
        record = panels.get(
            f"adjusted/{ticker}.csv", {}
        )
        actions = (
            record.get("attributes", {})
            .get("corporate_action_events", {})
        )

        matched = []
        dividends = []
        for kind in ("dividends", "splits"):
            events = actions.get(kind, {}) or {}
            if not isinstance(events, dict):
                continue
            for key, value in events.items():
                if event_date(key) == next_day:
                    matched.append(kind)
                    if kind == "dividends":
                        dividends.append(amount(value))

        output["provider_event_types"] = (
            ",".join(sorted(set(matched)))
            if matched else "NONE"
        )

        raw = load_prices(ticker, "raw")
        adj = load_prices(ticker, "adjusted")
        t = r["signal_date"]
        f_t = (
            float(adj[t]["Close"]) / float(raw[t]["Close"])
        )
        f_next = (
            float(adj[next_day]["Close"])
            / float(raw[next_day]["Close"])
        )
        observed = f_next / f_t - 1
        output["factor_change_bps"] = round(
            observed * 10000, 5
        )

        if "splits" in matched:
            verdict = "SPLIT_REVIEW_REQUIRED"
        elif "dividends" in matched and all(
            d is not None for d in dividends
        ):
            dividend = sum(dividends)
            previous_close = float(raw[t]["Close"])
            if previous_close <= dividend:
                verdict = "INVALID_DIVIDEND_RATIO"
            else:
                expected = (
                    1 / (1 - dividend / previous_close) - 1
                )
                error_bps = abs(
                    observed - expected
                ) * 10000
                output["reconciliation_error_bps"] = round(
                    error_bps, 5
                )
                verdict = (
                    "INTERNAL_NUMERIC_PASS"
                    if error_bps <= 5
                    else "INTERNAL_NUMERIC_MISMATCH"
                )
        elif matched:
            verdict = "PROVIDER_EVENT_REVIEW_REQUIRED"
        else:
            verdict = "NO_MATCHING_PROVIDER_EVENT"

        output["event_reconciliation"] = verdict

    exceptions.append(output)

columns = list(rows[0]) + [
    "provider_event_types",
    "event_reconciliation",
    "factor_change_bps",
    "reconciliation_error_bps",
]

output_file = AUDIT / "p3_tplus1_exception_triage.csv"
with output_file.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()
    writer.writerows(exceptions)

summary = {
    "schema": "FMA_TPLUS1_EXCEPTION_TRIAGE_V1",
    "total_signal_events": len(rows),
    "exception_rows_unique": len(exceptions),
    "status_counts": dict(
        Counter(r["status"] for r in rows)
    ),
    "corporate_action_reconciliation": dict(
        Counter(
            r["event_reconciliation"]
            for r in exceptions
            if r["status"] == "CORPORATE_ACTION_REVIEW"
        )
    ),
    "open_below_signal_stop": sum(
        r["next_open_below_stop"] == "True"
        for r in rows
    ),
    "no_next_session_dates": sorted({
        r["signal_date"] for r in rows
        if r["status"] == "NO_NEXT_MARKET_SESSION"
    }),
    "note": (
        "Provider-event matching is not independent "
        "corporate-action verification. All cases remain "
        "subject to an explicit execution policy."
    ),
}

report = AUDIT / "p3_tplus1_exception_triage_summary.json"
report.write_text(json.dumps(summary, indent=2) + "\n")

print("=== T+1 EXCEPTION TRIAGE ===")
print(json.dumps(summary, indent=2))
print("CSV:", output_file)
