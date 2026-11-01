import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

AUDIT = Path.home() / "FMA_Independent_Research/audit"

def load(name):
    path = AUDIT / name
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    return rows, hashlib.sha256(path.read_bytes()).hexdigest()

prices, price_hash = load("p3_tplus1_price_probe.csv")
exceptions, exception_hash = load(
    "p3_tplus1_exception_triage.csv"
)

exception_map = {
    (r["signal_date"], r["ticker"]): r
    for r in exceptions
}
assert len(exception_map) == len(exceptions) == 38
assert len(prices) == 1229

results = []

for r in prices:
    key = (r["signal_date"], r["ticker"])
    source_status = r["status"]
    below_stop = (
        r.get("next_open_below_stop", "").lower() == "true"
    )

    if source_status == "NO_NEXT_MARKET_SESSION":
        gate = "RIGHT_CENSORED"
    elif source_status == "CORPORATE_ACTION_REVIEW":
        event = exception_map[key]
        if event["event_reconciliation"] != "INTERNAL_NUMERIC_PASS":
            raise ValueError("Unresolved event: " + str(key))
        gate = "DIVIDEND_EXECUTION_POLICY_REQUIRED"
    elif below_stop:
        gate = "OPEN_BELOW_REFERENCE_STOP_REVIEW"
    elif source_status == "PRICE_ALIGNMENT_OK":
        gate = "PRICE_DATA_READY_NOT_FILLED"
    else:
        raise ValueError("Unknown status: " + str(key))

    results.append({
        "signal_date": r["signal_date"],
        "ticker": r["ticker"],
        "next_date": r["next_date"],
        "gate": gate,
        "reference_stop_raw": r["stop_raw_at_signal"],
        "next_raw_open": r["next_raw_open"],
        "simulated_fill": False,
    })

counts = Counter(r["gate"] for r in results)

expected = {
    "PRICE_DATA_READY_NOT_FILLED": 1191,
    "DIVIDEND_EXECUTION_POLICY_REQUIRED": 13,
    "OPEN_BELOW_REFERENCE_STOP_REVIEW": 4,
    "RIGHT_CENSORED": 21,
}
assert dict(counts) == expected, (counts, expected)

output = AUDIT / "p3_pretrade_gate.csv"
with output.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0]))
    writer.writeheader()
    writer.writerows(results)

summary = {
    "schema": "FMA_PRETRADE_GATE_V1",
    "status": "PASS",
    "signal_events": len(results),
    "classification_counts": dict(counts),
    "simulated_fills": 0,
    "source_sha256": {
        "price_probe": price_hash,
        "exception_triage": exception_hash,
    },
    "next_requirements": [
        "Freeze executable T+1 timing convention",
        "Implement dividend and split handling",
        "Define stop-gap treatment without look-ahead",
        "Validate portfolio-level order sizing and cash",
        "Test multi-session transaction accounting",
    ],
    "note": (
        "Pretrade classification only. No historical "
        "trade or strategy return is inferred."
    ),
}

report = AUDIT / "p3_pretrade_gate_summary.json"
report.write_text(json.dumps(summary, indent=2) + "\n")

print("=== PRETRADE GATE ===")
print(json.dumps(summary, indent=2))
print("CSV:", output)
