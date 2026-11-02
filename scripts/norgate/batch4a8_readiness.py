"""Read-only private NG-SF-270-LW readiness audit; no portfolio path or returns."""

import argparse
import ast
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from portfolio.ng_sf_270_lw_inputs_v1 import (
    InputBlocked, prepare_pair, economic_entry_gate, normalized_entry,
)

START, END = "2025-09-18", "2026-10-30"


def frozen_features():
    import numpy as np
    import pandas as pd
    fma = Path.home() / "FMA_Competition/fma_mpb_v41_20261013/fma_mpb_v41"
    snapshot = json.loads((ROOT / "configs/mpb_exit_reference.json").read_text())
    for name, expected in snapshot["source_sha256"].items():
        if hashlib.sha256((fma / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError("FROZEN_SOURCE_HASH_MISMATCH")
    source = fma / "momentum_pullback_breakout.py"
    tree = ast.parse(source.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "PullbackConfig")
    defaults = {n.target.id: ast.literal_eval(n.value) for n in cls.body
                if isinstance(n, ast.AnnAssign) and n.value is not None}
    if defaults["min_history"] != 270 or defaults["gap_buffer"] != .01:
        raise RuntimeError("FROZEN_CONFIG_DRIFT")
    spec = importlib.util.spec_from_file_location("batch4a8_readonly_config", fma / "config.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name in ("bars", "signal_features")]
    if len(functions) != 2:
        raise RuntimeError("FROZEN_FEATURES_NOT_FOUND")
    ns = {"pd": pd, "np": np, "CFG": SimpleNamespace(**defaults),
          "STRAT": module.STRAT, "CONTEST": module.CONTEST}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), "exec"), ns)
    return ns["signal_features"], module.STRAT, module.CONTEST, pd


def frame(rows, pd):
    result = pd.DataFrame(rows).set_index("date")
    result.index = pd.to_datetime(result.index)
    return result.rename(columns={k: k.title() for k in ("open", "high", "low", "close", "volume")})


def scan(db, clearance, output):
    if output.exists():
        raise FileExistsError("PRIVATE_REPORT_EXISTS")
    signal_features, strat, contest, pd = frozen_features()
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        meta = dict(conn.execute("SELECT key,value FROM metadata"))
        if meta.get("complete") != "true" or meta.get("padding") != "NONE":
            raise RuntimeError("EXTRACT_NOT_COMPLETE_NO_PADDING")
        spy = conn.execute("SELECT asset_id FROM securities WHERE symbol='SPY'").fetchone()[0]
        spy_dates = [r[0] for r in conn.execute(
            "SELECT date FROM prices WHERE asset_id=? AND mode='NONE' ORDER BY date", (spy,))]
        calendar = [d for d in spy_dates if START <= d <= END]
        if len(calendar) != 282 or calendar[0] != START or calendar[-1] != END:
            raise RuntimeError("BASE_CALENDAR_MISMATCH")
        first = next((d for i, d in enumerate(spy_dates, 1) if i >= 270 and START <= d <= END), None)
        if first is None:
            raise RuntimeError("NO_270_BAR_STUDY_DATE")
        later = [d for d in calendar if d >= first]
        # Raw stock dates are a qualification input, not a signal or trade.
        stock_dates = {}
        for asset, day in conn.execute("SELECT asset_id,date FROM prices WHERE mode='NONE' ORDER BY asset_id,date"):
            stock_dates.setdefault(asset, []).append(day)
        spy_tail = [d for d in spy_dates if d <= first][-270:]
        stock_ready_first = 0
        member_first = {a for a, eligible in conn.execute(
            "SELECT asset_id,eligible FROM membership WHERE date=?", (first,)) if eligible == 1}
        member_aligned_first = set()
        for (asset,) in conn.execute("SELECT asset_id FROM securities WHERE is_candidate=1"):
            ds = [d for d in stock_dates.get(asset, []) if d <= first]
            if len(ds) >= 270 and ds[-270:] == spy_tail:
                stock_ready_first += 1
                if asset in member_first:
                    member_aligned_first.add(asset)
        source = json.loads(clearance.read_text())
        terminal_items = source["terminal_review"]
        exception_items = source["dividend_review"]
        targets = {x["asset_id"] for x in terminal_items} | {x["asset_id"] for x in exception_items}
        targets.add(spy)
        views = {}
        for asset in targets:
            views[asset] = {}
            for mode in ("NONE", "CAPITAL", "TOTALRETURN"):
                views[asset][mode] = [dict(r) for r in conn.execute(
                    "SELECT date,open,high,low,close,volume,turnover FROM prices WHERE asset_id=? AND mode=? ORDER BY date",
                    (asset, mode))]
        adapter_ready_first = 0
        adapter_blockers_first = Counter()
        for asset in member_aligned_first:
            local = views.get(asset)
            if local is None:
                local = {mode: [dict(r) for r in conn.execute(
                    "SELECT date,open,high,low,close,volume,turnover FROM prices WHERE asset_id=? AND mode=? AND date<=? ORDER BY date DESC LIMIT 270",
                    (asset, mode, first))][::-1] for mode in ("NONE", "CAPITAL", "TOTALRETURN")}
            try:
                prepare_pair(local, views[spy], first)
                adapter_ready_first += 1
            except InputBlocked as exc:
                adapter_blockers_first[str(exc)] += 1
        member_days = {}
        for asset in targets - {spy}:
            member_days[asset] = {d for d, eligible in conn.execute(
                "SELECT date,eligible FROM membership WHERE asset_id=?", (asset,)) if eligible == 1}
        terminal_results = []
        for item in terminal_items:
            asset, last = item["asset_id"], item["last_price_date"]
            possible, blocked = [], Counter()
            if last is not None:
                for day in later:
                    if day >= last:
                        break
                    if day not in member_days[asset]:
                        continue
                    try:
                        pair = prepare_pair(views[asset], views[spy], day)
                        features = signal_features(frame(pair["stock"]["signal_bars"], pd),
                                                   frame(pair["spy"]["signal_bars"], pd), pd.Timestamp(day))
                        economic = economic_entry_gate(pair, min_buy_price=contest.min_buy_price,
                                                       min_avg_dollar_volume_20=strat.min_avg_dollar_volume_20)
                        if normalized_entry(features, economic):
                            possible.append(day)
                    except InputBlocked as exc:
                        blocked[str(exc)] += 1
            terminal_results.append({"asset_id": asset, "symbol": item["symbol"],
                                     "last_price_date": last,
                                     "normalized_possible_entry_days": possible,
                                     "input_blocked_days": dict(blocked),
                                     "actual_holdings": "UNKNOWN_NO_PORTFOLIO_PATH",
                                     "settlement": "UNVERIFIED"})
        priorities = []
        for item in exception_items:
            day = item["ex_date"]
            asset = item["asset_id"]
            possible_entries, blocked_inputs = [], Counter()
            if day >= first:
                for decision in later:
                    if decision >= day:
                        break
                    if decision not in member_days[asset]:
                        continue
                    try:
                        pair = prepare_pair(views[asset], views[spy], decision)
                        features = signal_features(frame(pair["stock"]["signal_bars"], pd),
                                                   frame(pair["spy"]["signal_bars"], pd), pd.Timestamp(decision))
                        economic = economic_entry_gate(pair, min_buy_price=contest.min_buy_price,
                                                       min_avg_dollar_volume_20=strat.min_avg_dollar_volume_20)
                        if normalized_entry(features, economic):
                            possible_entries.append(decision)
                    except InputBlocked as exc:
                        blocked_inputs[str(exc)] += 1
            raw = item.get("mode_entitlement_rows", {}).get("NONE")
            price = raw.get("close") if raw else None
            possible = [x for x in (item.get("legacy_amount"),
                        *(r.get("dividend") for r in item.get("mode_entitlement_rows", {}).values() if r))
                        if isinstance(x, (int, float)) and x >= 0]
            span = max(possible) - min(possible) if possible else None
            # $72k is the frozen 7.2% entry buffer of a $1m empty-start NAV.
            # This is a screening scale, not a bound on future held exposure.
            proxy = 72000 * span / price if price and span is not None else None
            priorities.append({"asset_id": item["asset_id"], "symbol": item["symbol"],
                               "ex_date": day, "in_later_window": day >= first,
                               "normalized_possible_entry_before_event": possible_entries,
                               "input_blocked_days": dict(blocked_inputs),
                               "indicative_entry_scale_difference_usd": proxy,
                               "independent_terms_verified": False,
                               "needs_raw_share_units": True,
                               "record_and_payment_dates_verified": False})
        priorities.sort(key=lambda x: (not bool(x["normalized_possible_entry_before_event"]),
                                       not bool(x["input_blocked_days"]),
                                       not x["in_later_window"],
                                       -(x["indicative_entry_scale_difference_usd"] or -1),
                                       x["asset_id"]))
        for rank, row in enumerate(priorities, 1):
            row["priority_rank"] = rank
            row["priority_tier"] = (
                "P1_POSSIBLE_HELD_EVENT" if row["normalized_possible_entry_before_event"]
                else "P2_INPUT_UNCERTAIN" if row["input_blocked_days"]
                else "P3_NO_PRE_EVENT_ENTRY_UNDER_DRAFT" if row["in_later_window"]
                else "P4_PRE_EMPTY_START")
        summary = {"first_eligible_decision_date": first,
                   "first_eligible_spy_bars": 270,
                   "excluded_initial_sessions": len(calendar)-len(later),
                   "later_window_sessions": len(later),
                   "first_possible_next_open_fill": later[1],
                   "last_session": later[-1],
                   "adjacent_pairs_max": len(later)-1,
                   "stock_ids_with_270_aligned_raw_bars_on_first_date": stock_ready_first,
                   "observed_members_on_first_date": len(member_first),
                   "members_with_270_aligned_raw_bars_on_first_date": len(member_aligned_first),
                   "members_passing_full_adapter_on_first_date": adapter_ready_first,
                   "member_adapter_blockers_on_first_date": dict(adapter_blockers_first),
                   "terminal_candidates": len(terminal_results),
                   "terminal_possible_entry_candidates": sum(bool(x["normalized_possible_entry_days"]) for x in terminal_results),
                   "terminal_input_blocked_candidates": sum(bool(x["input_blocked_days"]) for x in terminal_results),
                   "dividend_exceptions": len(priorities),
                   "dividend_exceptions_in_later_window": sum(x["in_later_window"] for x in priorities),
                   "dividend_exceptions_with_possible_pre_event_entry": sum(
                       bool(x["normalized_possible_entry_before_event"]) for x in priorities),
                   "dividend_exceptions_with_input_uncertainty": sum(
                       bool(x["input_blocked_days"]) for x in priorities),
                   "independently_verified_exception_dividends": 0,
                   "portfolio_simulation_run": False,
                   "ready_for_historical_experiment": False}
        report = {"schema": "BATCH4A8_READINESS_PRIVATE_V1", "summary": summary,
                  "input_db_sha256": hashlib.sha256(db.read_bytes()).hexdigest(),
                  "clearance_sha256": hashlib.sha256(clearance.read_bytes()).hexdigest(),
                  "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  "later_window_calendar": later,
                  "terminal_reachability": terminal_results,
                  "dividend_verification_priority": priorities}
        with output.open("x") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
        return summary
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="batch4a7_warmup_v1.sqlite")
    parser.add_argument("--clearance", default="batch4a7_clearance_v2.json")
    parser.add_argument("--output", default="batch4a8_readiness_v1.json")
    args = parser.parse_args()
    if any(Path(x).name != x for x in (args.db, args.clearance, args.output)):
        parser.error("Use only private basenames under restricted_norgate")
    private = ROOT / "restricted_norgate"
    result = scan(private / args.db, private / args.clearance, private / args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
