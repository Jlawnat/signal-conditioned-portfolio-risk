import csv
import json
import math
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path.home() / "FMA_Independent_Research"
AUDIT = ROOT / "audit"
BUNDLE = (
    Path.home()
    / "FMA_Competition/Market_Refresh_Runs"
    / "manual_full_20261031T061137Z_432cf6e9"
    / "market_bundle"
)

SAMPLE_SIZE = 1229

def read_rows(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))

signals = read_rows(
    AUDIT / "historical_signal_candidates.csv"
)
validation = json.loads(
    (AUDIT / "signal_differential_summary.json").read_text()
)

assert validation["status"] == "PASS"
assert validation["verified_reported_positives"] == 1229
assert len(signals) == 1229

spy = read_rows(BUNDLE / "raw/SPY.csv")
sessions = [r["Date"] for r in spy]
assert sessions == sorted(set(sessions))
next_session = dict(zip(sessions[:-1], sessions[1:]))

cache = {}

def panel(ticker, adjusted=False):
    key = (ticker, adjusted)
    if key not in cache:
        folder = "adjusted" if adjusted else "raw"
        path = BUNDLE / folder / f"{ticker}.csv"
        if not path.exists():
            cache[key] = {}
        else:
            rows = read_rows(path)
            dates = [r["Date"] for r in rows]
            assert dates == sorted(set(dates))
            cache[key] = {r["Date"]: r for r in rows}
    return cache[key]

def price(row, field):
    value = float(row[field])
    if not math.isfinite(value) or value <= 0:
        raise ValueError("INVALID_PRICE")
    return value

observations = []
errors = []

for signal in signals[:SAMPLE_SIZE]:
    ticker = signal["ticker"]
    day = signal["date"]
    following = next_session.get(day)

    if following is None:
        observations.append({
            "ticker": ticker,
            "signal_date": day,
            "status": "NO_NEXT_MARKET_SESSION"
        })
        continue

    raw = panel(ticker)
    adjusted = panel(ticker, adjusted=True)

    if not all(
        x in raw and x in adjusted
        for x in (day, following)
    ):
        observations.append({
            "ticker": ticker,
            "signal_date": day,
            "next_date": following,
            "status": "MISSING_PRICE_PANEL_DATE",
        })
        continue

    try:
        raw_close = price(raw[day], "Close")
        adjusted_close = price(adjusted[day], "Close")
        next_open = price(raw[following], "Open")
        next_raw_close = price(raw[following], "Close")
        next_adj_close = price(adjusted[following], "Close")
        adjusted_stop = float(
            signal["planned_stop_adjusted"]
        )

        if not math.isfinite(adjusted_stop):
            raise ValueError("INVALID_STOP")

        expected_adj_close = float(
            signal["close_adjusted"]
        )

        if not math.isclose(
            adjusted_close,
            expected_adj_close,
            rel_tol=1e-9,
            abs_tol=1e-8,
        ):
            raise ValueError("SIGNAL_CLOSE_SOURCE_MISMATCH")

        factor_t = adjusted_close / raw_close
        factor_next = next_adj_close / next_raw_close

        # Convert T-day adjusted stop to T-day raw units.
        raw_stop = adjusted_stop / factor_t

        factor_changed = not math.isclose(
            factor_t, factor_next,
            rel_tol=1e-6,
            abs_tol=1e-9,
        )

        # Diagnostic only: a gap below the reference stop
        # does not establish an executable stop fill.
        gap_below_stop = next_open <= raw_stop

        observation = {
            "ticker": ticker,
            "signal_date": day,
            "next_date": following,
            "status": (
                "CORPORATE_ACTION_REVIEW"
                if factor_changed else "PRICE_ALIGNMENT_OK"
            ),
            "signal_raw_close": raw_close,
            "signal_adjusted_close": adjusted_close,
            "stop_adjusted": adjusted_stop,
            "stop_raw_at_signal": raw_stop,
            "next_raw_open": next_open,
            "overnight_gap_return": (
                next_open / raw_close - 1
            ),
            "factor_changed": factor_changed,
            "next_open_below_stop": gap_below_stop,
        }

        observations.append(observation)

    except (ValueError, ZeroDivisionError) as exc:
        errors.append({
            "ticker": ticker,
            "date": day,
            "error": str(exc),
        })

statuses = Counter(
    r["status"] for r in observations
)

valid = [
    r for r in observations
    if r["status"] == "PRICE_ALIGNMENT_OK"
]

output = AUDIT / "p3_tplus1_price_probe.csv"

columns = [
    "ticker", "signal_date", "next_date", "status",
    "signal_raw_close", "signal_adjusted_close",
    "stop_adjusted", "stop_raw_at_signal",
    "next_raw_open", "overnight_gap_return",
    "factor_changed", "next_open_below_stop",
]

with output.open("w", newline="") as f:
    writer = csv.DictWriter(
        f, fieldnames=columns, extrasaction="ignore"
    )
    writer.writeheader()
    writer.writerows(observations)

summary = {
    "schema": "FMA_TPLUS1_PRICE_PROBE_V1",
    "status": "PASS" if not errors else "FAIL",
    "sampled_signal_events": SAMPLE_SIZE,
    "observations": len(observations),
    "source_errors": errors,
    "status_counts": dict(statuses),
    "clean_price_alignments": len(valid),
    "next_open_below_signal_stop": sum(
        r.get("next_open_below_stop", False)
        for r in observations
    ),
    "mean_overnight_gap_return_clean": (
        statistics.mean(
            r["overnight_gap_return"] for r in valid
        ) if valid else None
    ),
    "limitations": [
        "Historical price-alignment audit only.",
        "No simulated order fills or investment returns.",
        "T+1 open is not assumed to be automatically tradable.",
        "Adjustment-factor changes require event review.",
        "Only first 40 previously identified signal events.",
        "No full portfolio lifecycle or risk optimisation.",
    ],
}

report = AUDIT / "p3_tplus1_price_probe_summary.json"
report.write_text(json.dumps(summary, indent=2) + "\n")

print("=== T+1 PRICE ALIGNMENT AUDIT ===")
print(json.dumps(summary, indent=2))
print("Observations:", output)

if errors:
    raise SystemExit(1)
