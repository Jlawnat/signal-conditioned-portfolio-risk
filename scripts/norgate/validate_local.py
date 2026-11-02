"""Validate a private Batch 4A Norgate SQLite extract; print aggregates only."""

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import sqlite3

START = "2025-09-18"
END = "2026-10-30"
MODES = {"NONE", "CAPITAL", "CAPITALSPECIAL", "TOTALRETURN"}


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def study_calendar(path):
    with open(path, newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        dates = [row["Date"][:10] for row in reader]
    return [date for date in dates if START <= date <= END]


def validate(db_path, calendar_path):
    db_path, calendar_path = Path(db_path), Path(calendar_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        meta = dict(conn.execute("SELECT key,value FROM metadata"))
        calendar = study_calendar(calendar_path)
        issues = []
        if len(calendar) != 282 or len(set(calendar)) != 282 or calendar != sorted(calendar):
            issues.append("study_calendar_not_282_unique_ordered_sessions")
        if not calendar or calendar[0] != START or calendar[-1] != END:
            issues.append("study_calendar_endpoint_mismatch")
        if meta.get("complete") != "true":
            issues.append("extract_incomplete")
        if meta.get("sample") != "false":
            issues.append("sample_extract")
        if meta.get("padding") != "NONE" or set(meta.get("modes", "").split(",")) != MODES:
            issues.append("adjustment_or_padding_metadata_mismatch")
        securities = {row["asset_id"]: dict(row) for row in conn.execute("SELECT * FROM securities")}
        candidates = {asset for asset, row in securities.items() if row["is_candidate"]}
        if len(candidates) != 544:
            issues.append("candidate_count_not_544")
        if len(candidates) != len({securities[asset]["symbol"] for asset in candidates}):
            issues.append("duplicate_candidate_symbol")
        if int(meta.get("candidate_count", -1)) != len(candidates):
            issues.append("candidate_metadata_mismatch")
        counts = Counter()
        for row in conn.execute("SELECT mode,COUNT(*) AS n FROM prices GROUP BY mode"):
            counts[row["mode"]] = row["n"]
        all_records = sum(counts.values())
        bad_ohlc = conn.execute("""SELECT COUNT(*) FROM prices WHERE open IS NULL OR high IS NULL
            OR low IS NULL OR close IS NULL OR open <= 0 OR high <= 0 OR low <= 0 OR close <= 0
            OR high < low OR high < open OR high < close OR low > open OR low > close
            OR volume IS NULL OR volume < 0""").fetchone()[0]
        if bad_ohlc:
            issues.append("invalid_ohlcv_rows")
        if counts.get("NONE", 0) != counts.get("CAPITAL", 0) or counts.get("NONE", 0) != counts.get("CAPITALSPECIAL", 0) or counts.get("NONE", 0) != counts.get("TOTALRETURN", 0):
            issues.append("adjustment_view_row_count_mismatch")
        cross_view_mismatch = conn.execute("""SELECT COUNT(*) FROM prices p LEFT JOIN prices r
            ON r.asset_id=p.asset_id AND r.date=p.date AND r.mode='NONE'
            WHERE p.mode<>'NONE' AND r.date IS NULL""").fetchone()[0]
        if cross_view_mismatch:
            issues.append("cross_view_date_mismatch")
        duplicate_rows = conn.execute("""SELECT SUM(n-1) FROM (
            SELECT COUNT(*) n FROM prices GROUP BY asset_id,mode,date HAVING n>1)""").fetchone()[0] or 0
        if duplicate_rows:
            issues.append("duplicate_price_rows")
        price_dates = defaultdict(set)
        asset_dates = defaultdict(list)
        for asset, date in conn.execute("SELECT asset_id,date FROM prices WHERE mode='NONE' ORDER BY asset_id,date"):
            price_dates[date].add(asset)
            asset_dates[asset].append(date)
        membership = defaultdict(dict)
        invalid_membership = 0
        for asset, date, eligible in conn.execute("SELECT asset_id,date,eligible FROM membership ORDER BY asset_id,date"):
            if eligible not in (0, 1) or asset not in candidates:
                invalid_membership += 1
            membership[asset][date] = eligible
        if invalid_membership:
            issues.append("invalid_membership_rows")
        member_counts, member_with_price, missing_member_price, unknown_membership = [], [], [], []
        insufficient_lookback, membership_transitions = 0, Counter()
        missing_lookback_assets = set()
        private_short_history = defaultdict(list)
        private_count_dates = []
        private_transitions = []
        price_span = {asset: (dates[0], dates[-1]) for asset, dates in asset_dates.items() if dates}
        for date in calendar:
            members = {asset for asset in candidates if membership[asset].get(date) == 1}
            member_counts.append(len(members))
            if len(members) != 503:
                private_count_dates.append({"date": date, "observed_members": len(members)})
            with_price = members & price_dates[date]
            member_with_price.append(len(with_price))
            missing_member_price.append(len(members - with_price))
            unknown_membership.append(sum(date not in membership[asset] and
                asset in price_span and price_span[asset][0] <= date <= price_span[asset][1]
                for asset in candidates))
            for asset in with_price:
                prior = sum(d < date for d in asset_dates[asset])
                if prior < 126:
                    insufficient_lookback += 1
                    missing_lookback_assets.add(asset)
                    private_short_history[asset].append(date)
        for asset in candidates:
            prev = None
            for date in calendar:
                value = membership[asset].get(date)
                if value is None:
                    prev = None
                    continue
                if prev is not None and prev != value:
                    membership_transitions["additions" if value else "removals"] += 1
                    private_transitions.append({"asset_id": asset, "symbol": securities[asset]["symbol"],
                                                "date": date, "kind": "addition" if value else "removal"})
                prev = value
        if max(unknown_membership, default=0):
            issues.append("membership_missing_on_study_dates")
        if max(missing_member_price, default=0):
            issues.append("member_without_price")
        if insufficient_lookback:
            issues.append("insufficient_126_prior_prices")
        spy = next((asset for asset, row in securities.items() if row["symbol"] == "SPY"), None)
        spy_dates = {d for d in asset_dates.get(spy, []) if START <= d <= END}
        if spy_dates != set(calendar):
            issues.append("norgate_spy_calendar_mismatch")
        listed_without_membership = sum(len(price_dates[d] & candidates - {a for a in candidates if membership[a].get(d) == 1}) for d in calendar)
        price_gaps = 0
        internal_price_gaps = 0
        assets_with_internal_price_gaps = 0
        member_after_last_price = 0
        for asset in candidates:
            observed = set(asset_dates[asset])
            if asset in price_span:
                lo, hi = price_span[asset]
                gap_count = sum(lo <= d <= hi and d not in observed for d in calendar)
                internal_price_gaps += gap_count
                assets_with_internal_price_gaps += int(gap_count > 0)
            active = [d for d in calendar if membership[asset].get(d) == 1]
            if active:
                price_gaps += sum(d not in observed for d in active)
                last = asset_dates[asset][-1] if asset_dates[asset] else ""
                if any(d > last for d in active):
                    member_after_last_price += 1
        if member_after_last_price:
            issues.append("membership_after_last_price")
        if internal_price_gaps:
            issues.append("internal_price_calendar_gaps")
        suspicious_raw_moves = 0
        factor_jumps = 0
        private_price_anomalies = []
        raw_close = defaultdict(dict)
        capital_close = defaultdict(dict)
        for asset, mode, date, close in conn.execute("SELECT asset_id,mode,date,close FROM prices WHERE mode IN ('NONE','CAPITAL') ORDER BY asset_id,date"):
            if mode == "NONE":
                raw_close[asset][date] = close
            else:
                capital_close[asset][date] = close
        for asset, date_map in raw_close.items():
            previous_close = previous_factor = None
            for date, close in date_map.items():
                if previous_close and close and abs(close / previous_close - 1) > 0.5:
                    suspicious_raw_moves += 1
                    private_price_anomalies.append({"asset_id": asset, "date": date, "kind": "raw_move_over_50pct"})
                adjusted = capital_close[asset].get(date)
                factor = adjusted / close if close and adjusted else None
                if previous_factor and factor and abs(factor / previous_factor - 1) > 0.01:
                    factor_jumps += 1
                    private_price_anomalies.append({"asset_id": asset, "date": date, "kind": "capital_factor_jump_over_1pct"})
                previous_close, previous_factor = close, factor
        event_flags = conn.execute("SELECT COUNT(*) FROM capital_events WHERE flag=1 AND date BETWEEN ? AND ?", (START, END)).fetchone()[0]
        dividend_rows = conn.execute("SELECT COUNT(*) FROM prices WHERE mode='CAPITAL' AND dividend > 0 AND date BETWEEN ? AND ?", (START, END)).fetchone()[0]
        errors = Counter(stage for (stage,) in conn.execute("SELECT stage FROM errors"))
        last_price_before_end = sum(bool(asset_dates[a]) and asset_dates[a][-1] < END for a in candidates)
        delisted_statuses = Counter(str(securities[a]["status"]) for a in candidates)
        result = {
            "status": "FAIL" if issues else "PASS", "issues": issues,
            "study_sessions": len(calendar), "study_start": calendar[0] if calendar else None,
            "study_end": calendar[-1] if calendar else None,
            "candidate_securities": len(candidates), "identified_securities": len(securities),
            "price_records_by_mode": dict(counts), "price_records_all": all_records,
            "invalid_ohlcv_rows": bad_ohlc, "duplicate_price_rows": duplicate_rows,
            "cross_view_date_mismatch": cross_view_mismatch,
            "member_count_range": [min(member_counts, default=0), max(member_counts, default=0)],
            "member_with_price_range": [min(member_with_price, default=0), max(member_with_price, default=0)],
            "member_without_price_total": sum(missing_member_price),
            "member_without_price_max_daily": max(missing_member_price, default=0),
            "membership_unknown_max_daily": max(unknown_membership, default=0),
            "price_bars_without_membership_total": listed_without_membership,
            "member_price_gap_total": price_gaps,
            "internal_price_calendar_gaps": internal_price_gaps,
            "assets_with_internal_price_calendar_gaps": assets_with_internal_price_gaps,
            "member_after_last_price_securities": member_after_last_price,
            "suspicious_raw_close_moves_over_50pct": suspicious_raw_moves,
            "capital_adjustment_factor_jumps_over_1pct": factor_jumps,
            "insufficient_126_lookback_member_dates": insufficient_lookback,
            "insufficient_126_lookback_securities": len(missing_lookback_assets),
            "membership_transitions": dict(membership_transitions),
            "securities_last_price_before_end": last_price_before_end,
            "status_counts": dict(delisted_statuses),
            "capital_event_flags_in_window": event_flags,
            "capital_dividend_rows_in_window": dividend_rows,
            "error_stages": dict(errors), "error_total": sum(errors.values()),
            "acquisition": {k: meta.get(k) for k in ("source", "acquired_utc", "start", "end", "norgatedata", "python", "ndu_version", "extractor_sha256", "padding", "modes")},
            "restricted_db_sha256": sha256(db_path),
            "validator_sha256": sha256(__file__),
            "calendar_sha256": sha256(calendar_path),
            "private_details": {
                "non_503_dates": private_count_dates,
                "short_history": [{"asset_id": a, "symbol": securities[a]["symbol"],
                    "first_insufficient_date": dates[0], "last_insufficient_date": dates[-1], "member_dates": len(dates)}
                    for a, dates in private_short_history.items()],
                "explicit_membership_transitions": private_transitions,
                "terminal_series": [{"asset_id": a, "symbol": securities[a]["symbol"],
                    "last_price_date": asset_dates[a][-1],
                    "membership_on_last_price": membership[a].get(asset_dates[a][-1])}
                    for a in candidates if asset_dates[a] and asset_dates[a][-1] < END],
                "price_anomalies": private_price_anomalies,
            },
        }
        if errors:
            result["issues"].append("extraction_errors")
            result["status"] = "FAIL"
        return result
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--calendar-csv", required=True, help="Existing study SPY raw CSV")
    parser.add_argument("--output", help="Private aggregate report JSON under restricted_norgate/")
    args = parser.parse_args()
    report = validate(args.db, args.calendar_csv)
    if args.output:
        destination = Path(args.output).resolve()
        if "restricted_norgate" not in destination.parts or destination.exists():
            parser.error("output must be a new path inside restricted_norgate/")
        destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("acquisition", "restricted_db_sha256", "validator_sha256", "calendar_sha256", "private_details")}, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
