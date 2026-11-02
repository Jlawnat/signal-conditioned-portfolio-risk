"""Aggregate private Norgate corporate-action checks; never print source events."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--legacy-manifest", required=True)
    parser.add_argument("--curated", required=True)
    parser.add_argument("--output", required=True, help="Private aggregate JSON")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if "restricted_norgate" not in output.parts or output.exists():
        parser.error("output must be a new file in restricted_norgate/")
    conn = sqlite3.connect(f"file:{Path(args.db)}?mode=ro", uri=True)
    try:
        symbols = {symbol: asset for asset, symbol in conn.execute("SELECT asset_id,symbol FROM securities")}
        dates = defaultdict(list)
        dividend = {}
        capital = defaultdict(dict)
        raw = defaultdict(dict)
        for asset, mode, date, close, amount in conn.execute(
            "SELECT asset_id,mode,date,close,dividend FROM prices WHERE mode IN ('NONE','CAPITALSPECIAL','CAPITAL') ORDER BY asset_id,date"):
            if mode == "NONE":
                dates[asset].append(date)
                raw[asset][date] = close
            elif mode == "CAPITAL":
                capital[asset][date] = close
            else:
                dividend[asset, date] = amount or 0.0
        def prior_date(asset, exdate):
            return next((d for d in reversed(dates[asset]) if d < exdate), None)
        legacy = json.loads(Path(args.legacy_manifest).read_text(encoding="utf-8"))
        comparison = Counter()
        private_exceptions = []
        for filename, panel in legacy.get("panels", {}).items():
            if not filename.startswith("adjusted/"):
                continue
            symbol = panel.get("ticker") or Path(filename).stem
            events = panel.get("attributes", {}).get("corporate_action_events", {}).get("dividends", {})
            for event in events.values():
                comparison["legacy_events"] += 1
                asset = symbols.get(symbol)
                if asset is None:
                    comparison["symbol_not_in_norgate_candidate"] += 1
                    continue
                exdate = event.get("date")
                if isinstance(exdate, (int, float)):
                    exdate = datetime.fromtimestamp(exdate, timezone.utc).date().isoformat()
                elif isinstance(exdate, str) and exdate.isdigit():
                    exdate = datetime.fromtimestamp(int(exdate), timezone.utc).date().isoformat()
                else:
                    exdate = str(exdate)[:10]
                if not "2025-09-18" <= exdate <= "2026-10-30":
                    comparison["outside_study"] += 1
                    continue
                entitlement = prior_date(asset, exdate)
                observed = dividend.get((asset, entitlement)) if entitlement else None
                if observed is None:
                    comparison["no_norgate_entitlement_row"] += 1
                else:
                    try:
                        expected = float(event.get("amount", 0))
                        if abs(observed - expected) <= 0.01:
                            comparison["amount_match"] += 1
                        else:
                            comparison["amount_mismatch"] += 1
                            private_exceptions.append({"symbol": symbol, "ex_date": exdate,
                                "legacy_amount": expected, "norgate_ordinary_amount": observed})
                    except (ValueError, TypeError):
                        comparison["legacy_amount_unreadable"] += 1
        curated = json.loads(Path(args.curated).read_text(encoding="utf-8"))
        curated_count = Counter()
        for event in curated:
            asset = symbols.get(event["ticker"])
            if asset is None:
                curated_count["symbol_missing"] += 1
                continue
            entitlement = prior_date(asset, event["ex_date"])
            observed = dividend.get((asset, entitlement)) if entitlement else None
            if observed is None:
                curated_count["entitlement_missing"] += 1
            else:
                expected = float(event["amount_per_share"])
                curated_count["amount_match" if abs(observed - expected) <= 0.01 else "amount_mismatch"] += 1
        flags = {(a, d) for a, d in conn.execute("SELECT asset_id,date FROM capital_events WHERE flag=1 AND date BETWEEN '2025-09-18' AND '2026-10-30'")}
        factor_jump_count = factor_jump_flagged = factor_jump_prior_flagged = 0
        for asset, daymap in raw.items():
            previous = previous_date = None
            for date, close in daymap.items():
                adjusted = capital[asset].get(date)
                factor = adjusted / close if close and adjusted else None
                if previous and factor and abs(factor / previous - 1) > 0.01 and "2025-09-18" <= date <= "2026-10-30":
                    factor_jump_count += 1
                    if (asset, date) in flags:
                        factor_jump_flagged += 1
                    if (asset, previous_date) in flags:
                        factor_jump_prior_flagged += 1
                previous = factor
                previous_date = date
        delisted = [(a, s) for a, s in conn.execute("SELECT asset_id,symbol FROM securities WHERE status='DELISTED_DATABASE' AND is_candidate=1")]
        delisted_with_prices = sum(bool(dates[a]) for a, _ in delisted)
        last_price_member_one = 0
        for asset, _ in delisted:
            if dates[asset] and conn.execute("SELECT eligible FROM membership WHERE asset_id=? AND date=?", (asset, dates[asset][-1])).fetchone() == (1,):
                last_price_member_one += 1
        report = {
            "audit_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "legacy_dividend_comparison": dict(comparison),
            "curated_dividend_comparison": dict(curated_count),
            "capital_event_flags_in_window": len(flags),
            "capital_factor_jumps_over_1pct": factor_jump_count,
            "capital_factor_jumps_same_day_flagged": factor_jump_flagged,
            "capital_factor_jumps_prior_trading_day_flagged": factor_jump_prior_flagged,
            "delisted_candidate_count": len(delisted),
            "delisted_candidates_with_prices": delisted_with_prices,
            "delisted_last_price_member_one": last_price_member_one,
        }
        output.write_text(json.dumps({**report, "private_dividend_exceptions": private_exceptions}, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
