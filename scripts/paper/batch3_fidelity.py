"""Read-only, bounded candidate and flat-account decision differential."""

import csv
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FMA = Path.home() / "FMA_Competition/fma_mpb_v41_20261013/fma_mpb_v41"
BUNDLE = (Path.home() / "FMA_Competition/Market_Refresh_Runs"
          / "manual_full_20261031T061137Z_432cf6e9/market_bundle")
SIGNALS = Path.home() / "FMA_Independent_Research/audit/historical_signal_candidates.csv"
OUT = ROOT / "paper/tables/v2/fidelity_differential.json"
DATES = ("2025-09-18", "2026-01-05", "2026-10-30")

snapshot = json.loads((ROOT / "configs/mpb_exit_reference.json").read_text())
for filename, expected in snapshot["source_sha256"].items():
    assert hashlib.sha256((FMA / filename).read_bytes()).hexdigest() == expected
sys.path.insert(0, str(FMA))
import momentum_pullback_breakout as reference  # noqa: E402

with SIGNALS.open(newline="") as fh:
    stored = list(csv.DictReader(fh))
by_date = {date: [r for r in stored if r["date"] == date] for date in DATES}
with (Path.home() / "FMA_Independent_Research/audit/universe_lineage.csv").open(newline="") as fh:
    tickers = sorted(r["ticker"] for r in csv.DictReader(fh))
hist = {}
for ticker in ["SPY", *tickers]:
    frame = pd.read_csv(BUNDLE / "adjusted" / f"{ticker}.csv", parse_dates=["Date"])
    hist[ticker] = frame.set_index("Date").sort_index()
universe = pd.DataFrame({"ticker": tickers, "sector": "Unknown"})
results = []
for date in DATES:
    ranked = reference.rankings(hist, universe, pd.Timestamp(date))
    actual = ranked.to_dict("records")
    expected = sorted(by_date[date], key=lambda r: (-float(r["score"]), r["ticker"]))
    observed_tickers = [r["ticker"] for r in actual]
    stored_tickers = [r["ticker"] for r in expected]
    common = set(observed_tickers) & set(stored_tickers)
    score_max_abs = max((abs(float(next(r["score"] for r in actual if r["ticker"] == t))
                          - float(next(r["score"] for r in expected if r["ticker"] == t)))
                         for t in common), default=0.0)
    stop_max_abs = max((abs(float(next(r["planned_stop_adjusted"] for r in actual if r["ticker"] == t))
                         - float(next(r["planned_stop_adjusted"] for r in expected if r["ticker"] == t)))
                        for t in common), default=0.0)
    setup_mismatch = [t for t in common if next(r["setup"] for r in actual if r["ticker"] == t)
                      != next(r["setup"] for r in expected if r["ticker"] == t)]
    results.append({"date": date, "universe_tickers": len(tickers),
                    "reference_count": len(actual), "stored_count": len(expected),
                    "reference_only": sorted(set(observed_tickers) - set(stored_tickers)),
                    "stored_only": sorted(set(stored_tickers) - set(observed_tickers)),
                    "rank_order_equal": observed_tickers == stored_tickers,
                    "maximum_common_score_abs_difference": score_max_abs,
                    "maximum_common_stop_abs_difference": stop_max_abs,
                    "setup_mismatch": sorted(setup_mismatch)})

# The first session has a flat $1m account. Compare target order planning at
# that one comparable state; reference sector labels are unavailable for the
# full historical universe, so assign stored candidate sectors where present.
first = DATES[0]
sectors = {r["ticker"]: r["sector"] for r in by_date[first]}
flat_universe = pd.DataFrame({"ticker": tickers,
                              "sector": [sectors.get(t, "Unknown") for t in tickers]})
prices = {}
for ticker in tickers:
    frame = pd.read_csv(BUNDLE / "raw" / f"{ticker}.csv")
    match = frame.loc[frame["Date"] == first, "Close"]
    if len(match) == 1:
        prices[ticker] = float(match.iloc[0])
decision = reference.decision(hist, flat_universe, pd.Timestamp(first), 1_000_000.0,
                              pd.DataFrame(), pd.DataFrame(), 0, prices)
reference_targets = {r["ticker"]: int(r["target_shares"])
                     for r in decision["targets"].to_dict("records") if int(r["target_shares"]) > 0}
trade_path = ROOT / "audit/p3_lifecycle_v5u_A_trades.csv"
with trade_path.open(newline="") as fh:
    first_fills = [r for r in csv.DictReader(fh)
                   if r["signal_date"] == first and r["action"] == "BUY"]
result = {"dates": results, "flat_first_day": {
    "reference_target_shares": reference_targets,
    "reference_order_tickers": decision["orders"]["ticker"].tolist() if not decision["orders"].empty else [],
    "v5u_next_open_filled_shares": {r["ticker"]: int(r["shares"]) for r in first_fills},
    "reference_strategy_issues": decision["strategy_issues"],
    "comparison_note": "Reference close targets versus V5-U next-open fills; quantity difference may include execution guards."}}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
