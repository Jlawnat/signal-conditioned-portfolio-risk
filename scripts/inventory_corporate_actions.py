"""Inventory historical corporate actions from local provider data.

Provider metadata is discovery evidence, NOT independent
official verification. No live trading or policy mutation.
"""

import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path.cwd()
AUDIT = ROOT / "audit"
AUDIT.mkdir(exist_ok=True)

BUNDLE = (
    Path.home()
    / "FMA_Competition/Market_Refresh_Runs"
    / "manual_full_20261031T061137Z_432cf6e9"
    / "market_bundle"
)
SIGNALS = (
    Path.home()
    / "FMA_Independent_Research/audit"
    / "historical_signal_candidates.csv"
)

START = "2025-09-18"
END = "2026-10-30"

manifest = json.loads(
    (BUNDLE / "manifest.json").read_text()
)
registered = json.loads(
    (ROOT / "configs/verified_cash_dividends.json").read_text()
)

with SIGNALS.open(newline="") as f:
    signal_symbols = {
        r["ticker"] for r in csv.DictReader(f)
    }

registry = {}
for event in registered:
    key = (event["ticker"], event["ex_date"])
    if key in registry:
        raise RuntimeError("DUPLICATE_CURATED_EVENT")
    registry[key] = event

def date_from_provider_key(value):
    try:
        number = float(value)
        if 1_000_000_000 <= number <= 2_500_000_000:
            return datetime.fromtimestamp(
                number,
                ZoneInfo("America/New_York")
            ).date().isoformat()
    except (ValueError, TypeError, OverflowError):
        pass
    return str(value)[:10]

rows = []
seen = set()

for file_key, panel in manifest["panels"].items():
    if not (
        file_key.startswith("adjusted/")
        and file_key.endswith(".csv")
    ):
        continue

    ticker = Path(file_key).stem

    actions = (
        panel.get("attributes", {})
        .get("corporate_action_events", {})
    )

    for event_type in ("dividends", "splits"):
        entries = actions.get(event_type, {})

        if not isinstance(entries, dict):
            raise RuntimeError(
                f"UNEXPECTED_EVENT_FORMAT:{ticker}:{event_type}"
            )

        for provider_key, payload in entries.items():
            ex_date = date_from_provider_key(provider_key)
            if not START <= ex_date <= END:
                continue

            identity = (ticker, ex_date, event_type)
            if identity in seen:
                raise RuntimeError(
                    f"DUPLICATE_EVENT:{identity}"
                )
            seen.add(identity)

            amount = (
                payload.get("amount")
                if isinstance(payload, dict)
                else payload
            )

            registered_event = registry.get(
                (ticker, ex_date)
            )

            if event_type == "splits":
                status = "SPLIT_UNMODELED"
            elif registered_event is None:
                status = "PROVIDER_ONLY_UNVERIFIED"
            else:
                try:
                    match = abs(
                        float(amount)
                        - float(
                            registered_event["amount_per_share"]
                        )
                    ) < 1e-8
                except (ValueError, TypeError, KeyError):
                    match = False

                status = (
                    "CURATED_REGISTERED"
                    if match
                    else "REGISTERED_AMOUNT_MISMATCH"
                )

            rows.append({
                "ticker": ticker,
                "ex_date": ex_date,
                "event_type": event_type,
                "provider_amount_or_ratio": str(amount),
                "in_mpb_signal_universe": (
                    ticker in signal_symbols
                ),
                "status": status,
                "official_declaration_verified": (
                    status == "CURATED_REGISTERED"
                ),
                "provider_payload": json.dumps(
                    payload, sort_keys=True
                ),
            })

rows.sort(
    key=lambda r: (
        r["ex_date"], r["ticker"], r["event_type"]
    )
)

out = AUDIT / "corporate_actions_inventory_v1.csv"

with out.open("w", newline="") as f:
    writer = csv.DictWriter(
        f, fieldnames=[
            "ticker",
            "ex_date",
            "event_type",
            "provider_amount_or_ratio",
            "in_mpb_signal_universe",
            "status",
            "official_declaration_verified",
            "provider_payload",
        ]
    )
    writer.writeheader()
    writer.writerows(rows)

priority = [
    r for r in rows
    if r["in_mpb_signal_universe"]
    and r["status"] != "CURATED_REGISTERED"
]

summary = {
    "schema": "CORPORATE_ACTION_INVENTORY_V1",
    "scope": [START, END],
    "manifest_stock_panels": sum(
        k.startswith("adjusted/")
        and k.endswith(".csv")
        for k in manifest["panels"]
    ),
    "mpb_signal_symbols": len(signal_symbols),
    "total_provider_events": len(rows),
    "event_type_counts": dict(
        Counter(r["event_type"] for r in rows)
    ),
    "status_counts": dict(
        Counter(r["status"] for r in rows)
    ),
    "unverified_events_in_signal_universe": len(priority),
    "first_20_priority_events": [
        {
            k: r[k]
            for k in (
                "ticker",
                "ex_date",
                "event_type",
                "provider_amount_or_ratio",
                "status",
            )
        }
        for r in priority[:20]
    ],
    "limitations": [
        "Provider event metadata is not official verification.",
        "An event in the signal universe may never be held.",
        "An event not in the signal universe may still matter "
        "to future auxiliary allocation.",
        "Dividend payment dates need separate verification.",
        "Splits require explicit share and cost-basis accounting.",
        "Factor changes without manifest records are "
        "not yet independently enumerated.",
    ],
}

report = AUDIT / "corporate_actions_inventory_summary.json"
report.write_text(json.dumps(summary, indent=2) + "\n")

print("=== FULL-HISTORY CORPORATE ACTION INVENTORY ===")
print(json.dumps(summary, indent=2))
print("INVENTORY:", out)
