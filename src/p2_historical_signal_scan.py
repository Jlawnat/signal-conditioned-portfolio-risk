import csv
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path.home() / "FMA_Independent_Research"
BUNDLE = (
    Path.home()
    / "FMA_Competition/Market_Refresh_Runs"
    / "manual_full_20261031T061137Z_432cf6e9"
    / "market_bundle"
)
OUT = ROOT / "audit"
OUT.mkdir(exist_ok=True)

WINDOW = 270
MOMENTUM = (21, 63, 126)
WEIGHTS = (0.25, 0.35, 0.40)
input_digest = hashlib.sha256()

def load_csv(path):
    if not path.exists():
        return None

    raw = path.read_bytes()
    input_digest.update(str(path.relative_to(BUNDLE)).encode())
    input_digest.update(hashlib.sha256(raw).digest())

    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        dates, rows, invalid = [], [], [0]

        for r in reader:
            date = r["Date"]
            try:
                values = tuple(float(r[k]) for k in
                               ("Open", "High", "Low", "Close", "Volume"))
            except (ValueError, TypeError):
                values = (float("nan"),) * 5

            o, h, l, c, v = values
            valid = (
                all(math.isfinite(x) and x > 0 for x in values)
                and h >= max(o, l, c)
                and l <= min(o, h, c)
            )

            dates.append(date)
            rows.append(values)
            invalid.append(invalid[-1] + int(not valid))

    if dates != sorted(set(dates)):
        raise ValueError(f"Duplicate or unsorted dates: {path}")

    return {
        "dates": dates,
        "rows": rows,
        "index": {d: i for i, d in enumerate(dates)},
        "invalid_prefix": invalid,
    }

def valid_window(data, end):
    begin = end - WINDOW + 1
    return (
        begin >= 0
        and data["invalid_prefix"][end + 1]
            == data["invalid_prefix"][begin]
    )

def ema_pair(closes, span):
    """Pandas ewm(span=span, adjust=False), seeded at window start."""
    alpha = 2.0 / (span + 1.0)
    value = closes[0]
    five_ago = None

    for i in range(1, len(closes)):
        value = alpha * closes[i] + (1.0 - alpha) * value
        if i == len(closes) - 6:
            five_ago = value

    return value, five_ago

def calculate_signal(stock, spy):
    c = [r[3] for r in stock]
    bc = [r[3] for r in spy]
    o = [r[0] for r in stock]
    h = [r[1] for r in stock]
    l = [r[2] for r in stock]
    v = [r[4] for r in stock]

    px = c[-1]
    emas = {n: ema_pair(c, n) for n in (9, 21, 50)}

    ret = [px / c[-1-n] - 1 for n in MOMENTUM]
    rs = [
        r - (bc[-1] / bc[-1-n] - 1)
        for r, n in zip(ret, MOMENTUM)
    ]

    trend = (
        px > emas[9][0] > emas[21][0] > emas[50][0]
        and all(emas[n][0] > emas[n][1]
                for n in (9, 21, 50))
    )

    previous = stock[-11:-1]
    resistance = max(x[1] for x in previous)
    floor = min(x[2] for x in previous)
    range_fraction = resistance / floor - 1

    last_five_low = min(x[2] for x in previous[-5:])
    higher_low = last_five_low > min(l[-21:-11])

    avg_volume = sum(v[-21:-1]) / 20
    rvol = v[-1] / avg_volume
    adv = sum(cj * vj for cj, vj in
              zip(c[-21:-1], v[-21:-1])) / 20

    breakout = (
        range_fraction <= 0.12
        and higher_low
        and px > resistance * 1.001
        and rvol >= 1.20
    )

    support = min(emas[9][0], emas[21][0])
    recent_peak = max(h[-21:-1])
    pullback = (
        higher_low
        and floor >= emas[50][0]
        and last_five_low <= support * 1.02
        and 0 <= 1 - last_five_low / recent_peak <= 0.12
        and px > h[-2]
        and px > o[-1]
        and rvol >= 1.0
    )

    true_ranges = [
        max(h[j] - l[j],
            abs(h[j] - c[j-1]),
            abs(l[j] - c[j-1]))
        for j in range(WINDOW - 14, WINDOW)
    ]
    atr = sum(true_ranges) / 14
    stop = min(floor, l[-1]) - 0.25 * atr
    stop_fraction = (px - stop) / px

    eligible = (
        trend
        and ret[1] > 0 and ret[2] > 0
        and rs[1] > 0 and rs[2] > 0
        and adv >= 15_000_000
        and px >= 5.0
        and 0.015 <= stop_fraction <= 0.10
        and (breakout or pullback)
    )

    if not eligible:
        return None

    return {
        "score": sum(w * (r + s)
                     for w, r, s in zip(WEIGHTS, ret, rs)),
        "setup": "breakout" if breakout else "pullback_reclaim",
        "close_adjusted": px,
        "planned_stop_adjusted": stop,
        "stop_fraction": stop_fraction,
        "volume_ratio": rvol,
        "avg_dollar_volume_20": adv,
    }

with (BUNDLE / "universe.csv").open(newline="") as f:
    universe_rows = list(csv.DictReader(f))

tickers = {
    row["ticker"]: row["sector"]
    for row in universe_rows
}
if len(tickers) != 503 or len(universe_rows) != 503:
    raise ValueError("Research universe differs from audited 503 tickers")

spy = load_csv(BUNDLE / "adjusted/SPY.csv")
if spy is None or len(spy["rows"]) < WINDOW:
    raise ValueError("Missing SPY warmup data")

sessions = spy["dates"][WINDOW-1:]
daily = {
    d: {
        "date": d,
        "valid_tickers": 0,
        "eligible_signals": 0,
        "breakouts": 0,
        "pullbacks": 0,
        "sectors": set(),
    }
    for d in sessions
}

signals = []
missing_panels = []
ticker_signal_counts = Counter()
invalid_spy_sessions = []

for d in sessions:
    j = spy["index"][d]
    if not valid_window(spy, j):
        invalid_spy_sessions.append(d)

if invalid_spy_sessions:
    raise ValueError(
        f"SPY has {len(invalid_spy_sessions)} invalid research windows"
    )

for number, (ticker, sector) in enumerate(sorted(tickers.items()), 1):
    data = load_csv(BUNDLE / "adjusted" / f"{ticker}.csv")

    if data is None:
        missing_panels.append(ticker)
        continue

    for d in sessions:
        j = spy["index"][d]
        i = data["index"].get(d)

        if i is None or not valid_window(data, i):
            continue

        if data["dates"][i-WINDOW+1:i+1] != \
                spy["dates"][j-WINDOW+1:j+1]:
            continue

        daily[d]["valid_tickers"] += 1

        stock_window = data["rows"][i-WINDOW+1:i+1]
        spy_window = spy["rows"][j-WINDOW+1:j+1]
        result = calculate_signal(stock_window, spy_window)

        if result is None:
            continue

        daily[d]["eligible_signals"] += 1
        daily[d]["sectors"].add(sector)
        daily[d]["breakouts" if result["setup"] == "breakout"
                 else "pullbacks"] += 1
        ticker_signal_counts[ticker] += 1

        signals.append({
            "date": d,
            "ticker": ticker,
            "sector": sector,
            **result,
        })

    if number % 100 == 0:
        print(f"Scanned {number}/503 tickers", flush=True)

daily_rows = []
for d in sessions:
    item = daily[d]
    valid = item["valid_tickers"]
    daily_rows.append({
        "date": d,
        "valid_tickers": valid,
        "eligible_signals": item["eligible_signals"],
        "signal_rate_valid": (
            item["eligible_signals"] / valid if valid else 0
        ),
        "signal_rate_fixed_503": item["eligible_signals"] / 503,
        "eligible_sector_count": len(item["sectors"]),
        "breakouts": item["breakouts"],
        "pullbacks": item["pullbacks"],
    })

def write_csv(path, rows, columns):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

write_csv(
    OUT / "historical_signal_daily.csv",
    daily_rows,
    list(daily_rows[0]),
)

signals.sort(key=lambda x: (x["date"], -x["score"], x["ticker"]))

write_csv(
    OUT / "historical_signal_candidates.csv",
    signals,
    ["date", "ticker", "sector", "score", "setup",
     "close_adjusted", "planned_stop_adjusted",
     "stop_fraction", "volume_ratio", "avg_dollar_volume_20"],
)

counts = [r["eligible_signals"] for r in daily_rows]

summary = {
    "schema": "FMA_HISTORICAL_SIGNAL_SCAN_V1",
    "status": "EXPLORATORY_DESCRIPTIVE",
    "data_source": str(BUNDLE),
    "study_universe_tickers": len(tickers),
    "first_date": sessions[0],
    "last_date": sessions[-1],
    "sessions_checked": len(sessions),
    "total_confirmed_signal_events": len(signals),
    "mean_signals_per_session": statistics.mean(counts),
    "median_signals_per_session": statistics.median(counts),
    "min_signals_per_session": min(counts),
    "max_signals_per_session": max(counts),
    "zero_signal_sessions": sum(x == 0 for x in counts),
    "sessions_with_at_most_two": sum(x <= 2 for x in counts),
    "sessions_with_at_most_five": sum(x <= 5 for x in counts),
    "min_valid_tickers": min(r["valid_tickers"] for r in daily_rows),
    "max_valid_tickers": max(r["valid_tickers"] for r in daily_rows),
    "breakout_signal_events": sum(r["breakouts"] for r in daily_rows),
    "pullback_signal_events": sum(r["pullbacks"] for r in daily_rows),
    "missing_adjusted_panels": missing_panels,
    "unique_tickers_with_signals": len(ticker_signal_counts),
    "input_panel_sha256_aggregate": input_digest.hexdigest(),
    "important_limitations": [
        "Fixed current 503-stock universe; not historical PIT constituents.",
        "Adjusted OHLC with vendor-compatible unadjusted volume.",
        "Replicated signal formulas require differential testing "
        "against the original pandas implementation.",
        "Signal events are not actual trades or portfolio holdings.",
        "No transaction costs, capital deployment, or return estimates.",
        "Previously inspected historical period; not a fresh holdout.",
    ],
}

(OUT / "historical_signal_summary.json").write_text(
    json.dumps(summary, indent=2) + "\n"
)

print("\n=== HISTORICAL SIGNAL SUMMARY ===")
print(json.dumps(summary, indent=2))
print("\nReports:")
print(OUT / "historical_signal_daily.csv")
print(OUT / "historical_signal_candidates.csv")
print(OUT / "historical_signal_summary.json")
