import ast
import csv
import hashlib
import json
import math
import random
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

ROOT = Path.home() / "FMA_Independent_Research"
FMA = (Path.home() / "FMA_Competition"
       / "fma_mpb_v41_20261013/fma_mpb_v41")
BUNDLE = (Path.home() / "FMA_Competition"
          / "Market_Refresh_Runs"
          / "manual_full_20261031T061137Z_432cf6e9"
          / "market_bundle")
AUDIT = ROOT / "audit"

def csv_rows(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))

def literal_class(filename, class_name):
    tree = ast.parse((FMA / filename).read_text())
    cls = next(
        x for x in tree.body
        if isinstance(x, ast.ClassDef) and x.name == class_name
    )
    values = {}
    for node in cls.body:
        if (isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.value is not None):
            try:
                values[node.target.id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    return SimpleNamespace(**values)

# Execute only two actual frozen function definitions.
# No import of execution.py, rules.py, or trading entry points.
source_path = FMA / "momentum_pullback_breakout.py"
tree = ast.parse(source_path.read_text())
wanted = {"bars", "signal_features"}
functions = [
    x for x in tree.body
    if isinstance(x, ast.FunctionDef) and x.name in wanted
]
assert {x.name for x in functions} == wanted

namespace = {
    "np": np,
    "pd": pd,
    "CFG": literal_class(
        "momentum_pullback_breakout.py", "PullbackConfig"
    ),
    "STRAT": literal_class("config.py", "StrategyConfig"),
    "CONTEST": literal_class("config.py", "ContestConfig"),
}

isolated_module = ast.Module(body=functions, type_ignores=[])
exec(compile(isolated_module, str(source_path), "exec"), namespace)

original_bars = namespace["bars"]
original_signal = namespace["signal_features"]

universe = csv_rows(BUNDLE / "universe.csv")
tickers = sorted({r["ticker"] for r in universe})
assert len(tickers) == len(universe) == 503

daily = csv_rows(AUDIT / "historical_signal_daily.csv")
candidates = csv_rows(AUDIT / "historical_signal_candidates.csv")
previous_summary = json.loads(
    (AUDIT / "historical_signal_summary.json").read_text()
)
expected = {(r["date"], r["ticker"]): r for r in candidates}
assert len(expected) == len(candidates)
assert len(candidates) == previous_summary[
    "total_confirmed_signal_events"
]

daily_lookup = {r["date"]: r for r in daily}
assert len(daily_lookup) == len(daily) == 282

# Check internal consistency of the earlier scan.
counts = Counter(r["date"] for r in candidates)
for row in daily:
    assert counts[row["date"]] == int(row["eligible_signals"]), (
        "Earlier scan CSV mismatch: " + row["date"]
    )

# Recreate the exact input fingerprint from the earlier scan.
digest = hashlib.sha256()

def fingerprint(relative):
    path = BUNDLE / relative
    raw = path.read_bytes()
    digest.update(str(relative).encode())
    digest.update(hashlib.sha256(raw).digest())

fingerprint(Path("adjusted/SPY.csv"))
for ticker in tickers:
    fingerprint(Path("adjusted") / f"{ticker}.csv")

actual_hash = digest.hexdigest()
expected_hash = previous_summary["input_panel_sha256_aggregate"]
assert actual_hash == expected_hash, (
    "Market data changed since historical signal scan. "
    "Do not compare nonidentical data snapshots."
)

print("Source panel fingerprint: PASS", flush=True)

def load_frame(ticker):
    path = BUNDLE / "adjusted" / f"{ticker}.csv"
    frame = pd.read_csv(path, parse_dates=["Date"])
    return frame.set_index("Date")[
        ["Open", "High", "Low", "Close", "Volume"]
    ]

spy = load_frame("SPY")
cache = {}

def get_stock(ticker):
    if ticker not in cache:
        cache[ticker] = load_frame(ticker)
    return cache[ticker]

# Select diverse historical days deterministically.
first = daily[0]
last = daily[-1]
max_day = max(daily, key=lambda r: int(r["eligible_signals"]))
median_day = min(
    daily,
    key=lambda r: abs(int(r["eligible_signals"]) - 3)
)

selected = [
    first["date"],
    last["date"],
    max_day["date"],
    median_day["date"],
]

for predicate in (
    lambda x: x == 0,
    lambda x: x == 1,
    lambda x: x == 2,
    lambda x: x >= 10,
):
    match = next(
        (r["date"] for r in daily
         if predicate(int(r["eligible_signals"]))
         and r["date"] not in selected),
        None
    )
    if match and len(selected) < 7:
        selected.append(match)

for r in daily:
    if len(selected) >= 7:
        break
    if r["date"] not in selected:
        selected.append(r["date"])

full_dates = set(selected)

# Every reported positive, plus every stock on selected days.
cases = set(expected)
for date in full_dates:
    cases.update((date, ticker) for ticker in tickers)

# Add random negatives from outside the selected full dates.
rng = random.Random(20261101)
negative_pairs = set()
dates = list(daily_lookup)

while len(negative_pairs) < 200:
    pair = (rng.choice(dates), rng.choice(tickers))
    if pair not in expected and pair[0] not in full_dates:
        negative_pairs.add(pair)

cases.update(negative_pairs)

print(
    f"Scheduled: {len(cases)} unique ticker-date checks "
    f"across {len(full_dates)} complete dates",
    flush=True,
)

mismatches = []
checked = 0
verified_positives = 0
verified_negatives = 0
reference_day_counts = Counter()
reference_day_valid = Counter()

for date, ticker in sorted(cases):
    stock = get_stock(ticker)
    ts = pd.Timestamp(date)

    # The original function, extracted from frozen source.
    result = original_signal(stock, spy, ts)
    confirmed = bool(result.get("entry_confirmed", False))

    expected_row = expected.get((date, ticker))
    expected_confirmed = expected_row is not None

    if date in full_dates:
        if confirmed:
            reference_day_counts[date] += 1

        stock_window = original_bars(stock, ts)
        spy_window = original_bars(spy, ts)

        if (stock_window is not None
            and spy_window is not None
            and stock_window.index.equals(spy_window.index)):
            reference_day_valid[date] += 1

    errors = []

    if confirmed != expected_confirmed:
        errors.append("ENTRY_CLASSIFICATION_MISMATCH")

    if confirmed and expected_confirmed:
        if result["setup"] != expected_row["setup"]:
            errors.append("SETUP_MISMATCH")

        fields = {
            "score": "score",
            "close": "close_adjusted",
            "planned_stop_adjusted": "planned_stop_adjusted",
            "stop_fraction": "stop_fraction",
            "volume_ratio": "volume_ratio",
            "avg_dollar_volume_20": "avg_dollar_volume_20",
        }

        for original_key, report_key in fields.items():
            a = float(result[original_key])
            b = float(expected_row[report_key])

            if not math.isclose(
                a, b, rel_tol=1e-9, abs_tol=1e-8
            ):
                errors.append(
                    f"{original_key}: original={a}, scan={b}"
                )

    if errors:
        mismatches.append({
            "date": date,
            "ticker": ticker,
            "original_confirmed": confirmed,
            "scan_confirmed": expected_confirmed,
            "errors": errors,
        })
    elif expected_confirmed:
        verified_positives += 1
    else:
        verified_negatives += 1

    checked += 1
    if checked % 500 == 0:
        print(
            f"Compared {checked}/{len(cases)} cases",
            flush=True,
        )

# Compare entire day's eligibility and data coverage.
day_checks = []
for date in selected:
    expected_count = int(
        daily_lookup[date]["eligible_signals"]
    )
    expected_valid = int(daily_lookup[date]["valid_tickers"])
    actual_count = reference_day_counts[date]
    actual_valid = reference_day_valid[date]

    passed = (
        actual_count == expected_count
        and actual_valid == expected_valid
    )

    day_checks.append({
        "date": date,
        "expected_signals": expected_count,
        "original_signals": actual_count,
        "expected_valid_tickers": expected_valid,
        "original_valid_tickers": actual_valid,
        "pass": passed,
    })

    if not passed:
        mismatches.append({
            "date": date,
            "ticker": "*ALL*",
            "errors": ["FULL_DAY_COUNT_MISMATCH"],
        })

status = "PASS" if not mismatches else "FAIL"

result = {
    "schema": "FMA_SIGNAL_DIFFERENTIAL_V1",
    "status": status,
    "tests_executed": checked,
    "verified_reported_positives": verified_positives,
    "verified_negative_cases": verified_negatives,
    "all_reported_positives_covered": (
        verified_positives == len(candidates)
    ),
    "complete_days": day_checks,
    "mismatch_count": len(mismatches),
    "first_mismatches": mismatches[:25],
    "market_panel_hash_match": True,
    "market_panel_hash": actual_hash,
    "frozen_signal_source_sha256": hashlib.sha256(
        source_path.read_bytes()
    ).hexdigest(),
    "limitations": [
        "All reported positive events are tested.",
        "Negative events are sampled, not exhaustively tested.",
        "Full universe checked on seven selected sessions.",
        "No actual order or portfolio execution validation.",
        "Fixed current-stock universe is not historical PIT.",
        "Historical period is exploratory, not new holdout.",
    ],
}

path = AUDIT / "signal_differential_summary.json"
path.write_text(json.dumps(result, indent=2) + "\n")

print("\n=== DIFFERENTIAL TEST RESULT ===")
print(json.dumps({
    "status": status,
    "tests_executed": checked,
    "verified_reported_positives": verified_positives,
    "verified_negative_cases": verified_negatives,
    "complete_days_passed": sum(
        x["pass"] for x in day_checks
    ),
    "mismatch_count": len(mismatches),
    "first_mismatches": mismatches[:5],
    "report": str(path),
}, indent=2))

if mismatches:
    raise SystemExit(1)
