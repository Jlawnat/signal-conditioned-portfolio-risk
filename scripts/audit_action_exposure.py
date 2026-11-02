"""Portfolio-aware corporate-action exposure inventory.

Read-only. Provider-factor agreement is not official verification.
"""

import csv
import json
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path.cwd()
AUDIT = ROOT / "audit"
BUNDLE = (
    Path.home()
    / "FMA_Competition/Market_Refresh_Runs"
    / "manual_full_20261031T061137Z_432cf6e9"
    / "market_bundle"
)

def read(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))

inventory = read(
    AUDIT / "corporate_actions_inventory_v1.csv"
)
curated = json.loads(
    (ROOT / "configs/verified_cash_dividends.json").read_text()
)

events = defaultdict(list)
for r in inventory:
    events[(r["ticker"], r["ex_date"])].append(r)

curated_keys = {
    (r["ticker"], r["ex_date"]) for r in curated
}

price_cache = {}

def record(ticker, day, kind):
    key = (ticker, kind)
    if key not in price_cache:
        price_cache[key] = {
            r["Date"]: r
            for r in read(
                BUNDLE / kind / f"{ticker}.csv"
            )
        }
    return price_cache[key][day]

def factor(ticker, day):
    a = float(record(ticker, day, "adjusted")["Close"])
    r = float(record(ticker, day, "raw")["Close"])
    if r <= 0 or a <= 0:
        raise RuntimeError("INVALID_MARKET_PRICE")
    return a / r

def classify(ticker, day, previous):
    provider = events.get((ticker, day), [])

    prior_raw = float(
        record(ticker, previous, "raw")["Close"]
    )
    actual_ratio = factor(ticker, day) / factor(
        ticker, previous
    )

    if not provider:
        if abs(actual_ratio - 1) > 0.00002:
            return (
                "FACTOR_CHANGE_NO_PROVIDER_EVENT",
                None, actual_ratio
            )
        return None, None, actual_ratio

    types = {e["event_type"] for e in provider}

    if len(provider) != 1 or "splits" in types:
        return (
            "SPLIT_OR_COMPOSITE_ACTION",
            provider[0], actual_ratio
        )

    item = provider[0]
    amount = float(item["provider_amount_or_ratio"])

    if amount <= 0 or amount >= prior_raw:
        status = "INVALID_DIVIDEND_AMOUNT"
    else:
        expected_ratio = 1 / (1 - amount / prior_raw)
        discrepancy = abs(
            actual_ratio / expected_ratio - 1
        )

        if discrepancy > 0.0005:
            status = "PROVIDER_FACTOR_MISMATCH"
        elif (ticker, day) in curated_keys:
            status = "CURATED_FACTOR_MATCH"
        else:
            status = "PROVIDER_FACTOR_MATCH_UNVERIFIED"

    return status, item, actual_ratio

records = []

for policy in "ABC":
    prefix = f"p3_lifecycle_v3_{policy}"

    summary = json.loads(
        (AUDIT / f"{prefix}_summary.json").read_text()
    )

    if (
        summary["status"] != "PASS"
        or summary["sessions_completed"] != 30
    ):
        raise RuntimeError(
            f"INCOMPLETE_RUN:{policy}"
        )

    daily = read(AUDIT / f"{prefix}_daily.csv")
    trades = read(AUDIT / f"{prefix}_trades.csv")

    trades_by_day = defaultdict(list)
    for t in trades:
        trades_by_day[t["date"]].append(t)

    holdings = {}
    previous = None

    for row in daily:
        day = row["date"]
        todays_trades = trades_by_day[day]

        # Holdings before this session's opening fills.
        held_before = dict(holdings)
        buys = {
            t["ticker"]
            for t in todays_trades
            if t["action"] == "BUY"
        }

        affected = set(held_before) | buys

        if previous is not None:
            for ticker in sorted(affected):
                status, event, ratio = classify(
                    ticker, day, previous
                )

                if status is None:
                    continue

                records.append({
                    "policy": policy,
                    "ticker": ticker,
                    "date": day,
                    "held_shares_before_open": (
                        held_before.get(ticker, 0)
                    ),
                    "buy_executed_at_open": ticker in buys,
                    "status": status,
                    "event_type": (
                        event["event_type"] if event
                        else "UNKNOWN"
                    ),
                    "provider_amount": (
                        event["provider_amount_or_ratio"]
                        if event else ""
                    ),
                    "factor_ratio": round(ratio, 9),
                })

        # Apply executed trading activity after entitlement.
        for trade in todays_trades:
            ticker = trade["ticker"]
            q = int(trade["shares"])

            if trade["action"] == "BUY":
                if ticker in holdings:
                    raise RuntimeError("DUPLICATE_BUY")
                holdings[ticker] = q
            elif trade["action"] == "SELL":
                if holdings.get(ticker, 0) < q:
                    raise RuntimeError("INVALID_SELL")
                holdings[ticker] -= q
                if holdings[ticker] == 0:
                    del holdings[ticker]
            else:
                raise RuntimeError("UNKNOWN_ACTION")

        if len(holdings) != int(row["holdings"]):
            raise RuntimeError("HOLDINGS_REPLAY_MISMATCH")

        previous = day

out = AUDIT / "corporate_action_exposure_30d.csv"
fields = [
    "policy", "ticker", "date",
    "held_shares_before_open",
    "buy_executed_at_open",
    "status", "event_type",
    "provider_amount", "factor_ratio",
]

with out.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(records)

distinct = sorted({
    (r["ticker"], r["date"], r["event_type"], r["status"])
    for r in records
})

report = {
    "schema": "CORPORATE_ACTION_EXPOSURE_V1",
    "sessions_per_policy": 30,
    "exposure_records": len(records),
    "distinct_relevant_actions": len(distinct),
    "status_counts": dict(
        Counter(r["status"] for r in records)
    ),
    "by_policy": {
        p: dict(Counter(
            r["status"]
            for r in records if r["policy"] == p
        )) for p in "ABC"
    },
    "events_to_review": [
        {
            "ticker": ticker,
            "date": day,
            "type": kind,
            "status": status,
        }
        for ticker, day, kind, status in distinct
    ],
    "limitations": [
        "Only the completed 30-session executed paths.",
        "Future 282-session portfolios may hold other names.",
        "Provider-factor matching is internal consistency.",
        "Payment dates are not independently checked.",
        "Split handling is not implemented.",
    ],
}

(AUDIT / "corporate_action_exposure_summary.json").write_text(
    json.dumps(report, indent=2) + "\n"
)

print("=== PORTFOLIO-AWARE ACTION EXPOSURE ===")
print(json.dumps(report, indent=2))
print("DETAIL:", out)
