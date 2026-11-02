"""Read-only arithmetic audit of a completed private NG-SF diagnostic journal.

Prints status and counts only. It never reports portfolio performance or asset IDs.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from portfolio.decision_execution_log_v1 import reconcile_directory


class AuditBlocked(ValueError):
    pass


def _close(a, b, *, atol=0.0001):
    return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=atol)


def _check(ok, reason):
    if not ok:
        raise AuditBlocked(reason)


def _rows(directory, name):
    path = directory / (name + ".jsonl")
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def _positions(row):
    return {p["security_id"]: p for p in row["positions"]}


def audit(directory, event_register, db, *, expected_pairs=229,
          allow_blocked_prefix=False):
    directory = Path(directory).resolve()
    private = (ROOT / "restricted_norgate").resolve()
    _check(private in directory.parents, "OUTPUT_OUTSIDE_RESTRICTED_STORAGE")
    status = json.loads((directory / "diagnostic_private.json").read_text())
    complete = status.get("status") == "NO_AFFECTED_EVENT_FOUND"
    _check(complete or (allow_blocked_prefix and
           status.get("status") == "BLOCKED_AT_FIRST_AFFECTED_EVENT"),
           "DIAGNOSTIC_PATH_INCOMPLETE")
    _check(status.get("performance_not_reported") is True, "UNEXPECTED_DIAGNOSTIC_OUTPUT")
    events = json.loads(Path(event_register).read_text())
    _check(isinstance(events, list), "INVALID_EVENT_REGISTER")
    event_map = {}
    for event in events:
        day = event.get("ex_date", event.get("effective_date"))
        key = (day, event["asset_id"])
        _check(key not in event_map, "COMPOSITE_EVENT_REQUIRES_REVIEW")
        event_map[key] = event
    snapshots, orders, pairs = (_rows(directory, name) for name in
                                ("snapshots", "orders", "pairs"))
    if not complete:
        # The blocked opening can leave S0–S2 of the next pair in the journal.
        # Audit only fully closed pairs; preserve the original files unchanged.
        expected_pairs = len(pairs)
        closed_keys = {(r["decision_date"], r["execution_date"]) for r in pairs}
        snapshots = [r for r in snapshots if
                     (r["decision_date"],r["execution_date"]) in closed_keys]
    data_hash = hashlib.sha256((_sha256(db)+_sha256(event_register)).encode()).hexdigest()
    _check(all(row["data_manifest_hash"]==data_hash for row in snapshots),
           "DATA_OR_REGISTER_HASH_MISMATCH")
    _check(len(pairs) == expected_pairs and
           len(snapshots) == expected_pairs * 6, "INCOMPLETE_STAGE_POPULATION")
    lifecycle = reconcile_directory(directory)
    _check(lifecycle["status"] == "PASS", "ORDER_LIFECYCLE_RECONCILIATION_FAILED")
    by_pair = {}
    for row in snapshots:
        key = (row["decision_date"], row["execution_date"])
        by_pair.setdefault(key, {})[row["simulation_phase"]] = row
        _check(row["calculation_status"] == "VALID", "INVALID_RISK_SNAPSHOT")
        numerator = sum(p["shares"] *
                        (max(0, p["marked_price"] - p["adjusted_stop"]) +
                         .01 * p["marked_price"]) for p in row["positions"])
        _check(_close(numerator, row["risk_numerator"]) and
               _close(numerator / row["nav"], row["marked_stop_gap_exposure"],
                      atol=1e-10), "RISK_ARITHMETIC_MISMATCH")
        if row["simulation_phase"] in ("S0_PRE_DECISION", "S3_PRE_FILL",
                                        "S4_POST_FILL", "S5_CLOSE"):
            marked_nav = row["cash"] + row["dividend_receivable"] + sum(
                p["shares"] * p["marked_price"] for p in row["positions"])
            _check(_close(marked_nav, row["nav"]), "VALUATION_IDENTITY_MISMATCH")
        if row["simulation_phase"] in ("S0_PRE_DECISION", "S1_AFTER_MPB_AND_OVERLAY",
                                        "S2_FINAL_PLAN"):
            _check(row["record_origin"] == "decision_time" and
                   row["information_cutoff"] == row["decision_date"],
                   "DECISION_FORWARD_INFORMATION")
        else:
            _check(row["record_origin"] == "execution_time" and
                   row["information_cutoff"] == row["execution_date"],
                   "EXECUTION_CUTOFF_MISMATCH")
    _check(len(by_pair) == expected_pairs, "PAIR_COUNT_MISMATCH")
    first = by_pair[min(by_pair)]["S0_PRE_DECISION"]
    _check(_close(first["nav"], 1000000) and
           _close(first["cash"], 1000000) and
           _close(first["dividend_receivable"], 0) and
           first["positions"] == [], "OPENING_ACCOUNT_MISMATCH")
    with Path(db).open("rb") as stream:
        sqlite_input = stream.read(16) == b"SQLite format 3\x00"
    if sqlite_input:
        with sqlite3.connect(f"file:{Path(db).resolve()}?mode=ro", uri=True) as connection:
            spy = connection.execute("SELECT asset_id FROM securities WHERE symbol='SPY'").fetchone()[0]
            calendar = [r[0] for r in connection.execute(
                "SELECT date FROM prices WHERE asset_id=? AND mode='NONE' AND date BETWEEN '2025-12-02' AND '2026-10-30' ORDER BY date", (spy,))]
        _check(len(calendar)==230 and
               sorted(by_pair)==list(zip(calendar,calendar[1:]))[:expected_pairs],
               "CALENDAR_COVERAGE_MISMATCH")
    gap_rows = {(r["decision_date"],r["execution_date"]):r for r in pairs}
    _check(len(gap_rows)==expected_pairs and set(gap_rows)==set(by_pair),
           "IMPLEMENTATION_GAP_POPULATION_MISMATCH")
    claims = {}
    prior_close = None
    action_counts = {"cash_dividends": 0, "splits": 0, "terminals": 0,
                     "pending_dividend_adjustments": 0, "receivable_payments": 0}
    phase_names = ("S0_PRE_DECISION", "S1_AFTER_MPB_AND_OVERLAY", "S2_FINAL_PLAN",
                   "S3_PRE_FILL", "S4_POST_FILL", "S5_CLOSE")
    for (decision, execution), phases in sorted(by_pair.items()):
        _check(set(phases) == set(phase_names), "MISSING_OR_DUPLICATE_STAGE")
        s0,s1,s2,s3,s4,s5 = (phases[name] for name in phase_names)
        _check([s0["event_sequence"],s1["event_sequence"],s2["event_sequence"],
                s3["event_sequence"],s4["event_sequence"],s5["event_sequence"]] ==
               sorted([s0["event_sequence"],s1["event_sequence"],s2["event_sequence"],
                       s3["event_sequence"],s4["event_sequence"],s5["event_sequence"]]),
               "STAGE_SEQUENCE_MISMATCH")
        _check(_close(s0["nav"],s1["nav"]) and _close(s0["nav"],s2["nav"]),
               "PLANNING_NAV_CHANGED")
        gap = gap_rows[(decision,execution)]
        expected_gap = s4["marked_stop_gap_exposure"]-s2["marked_stop_gap_exposure"]
        crossing = int(s2["marked_stop_gap_exposure"] <=
                       s2["budget_fraction"]+1e-9 and
                       s4["marked_stop_gap_exposure"] >
                       s2["budget_fraction"]+1e-9)
        _check(_close(gap["gap"],expected_gap,atol=1e-10) and
               _close(gap["positive_gap"],max(0,expected_gap),atol=1e-10) and
               gap["compliant_to_exceedance"]==crossing and
               _close(gap["decision_budget_fraction"],s2["budget_fraction"],atol=1e-10) and
               gap["had_orders"]==bool(s2["order_ids"]),
               "IMPLEMENTATION_GAP_ARITHMETIC_MISMATCH")
        if prior_close is not None:
            _check(_close(prior_close["nav"], s0["nav"]) and
                   _close(prior_close["cash"], s0["cash"]) and
                   _close(prior_close["dividend_receivable"],
                          s0["dividend_receivable"]) and
                   _positions(prior_close) == _positions(s0),
                   "CLOSE_TO_NEXT_DECISION_MISMATCH")
        _check(_close(s0["dividend_receivable"],
                      sum(amount for _,amount in claims.values())),
               "OPENING_RECEIVABLE_LEDGER_MISMATCH")
        payments = 0.0
        for key,(pay_day,amount) in list(claims.items()):
            if pay_day <= execution:
                payments += amount
                del claims[key]
                action_counts["receivable_payments"] += 1
        held = _positions(s0)
        expected = {asset: dict(p) for asset,p in held.items()}
        current_orders = [r for r in orders if r["decision_date"]==decision and
                          r["execution_date"]==execution]
        accepted = {r["order_id"]:r for r in current_orders if r["order_state"]=="ACCEPTED"}
        proposed = {r["order_id"]:r for r in current_orders if r["order_state"]=="PROPOSED"}
        pending = {r["security_id"] for r in accepted.values()}
        pending_stop_adjustments = {}
        for (event_day, asset), event in event_map.items():
            if event_day != execution or (asset not in held and asset not in pending):
                continue
            kind = event["event_type"]
            if kind == "CASH_DIVIDEND":
                _check(event["entitlement_date"] == decision,
                       "DIVIDEND_ENTITLEMENT_DATE_MISMATCH")
                if event.get("payment_date") is None:
                    _check(event.get("payment_not_before_date", "") > "2026-10-30",
                           "UNKNOWN_PAYMENT_CAN_AFFECT_STUDY")
                amount = float(event["cash_per_raw_share"])
                if asset in held:
                    shares = held[asset]["shares"]
                    _check(event["event_id"] not in claims, "DUPLICATE_DIVIDEND_ACCRUAL")
                    claims[event["event_id"]] = (
                        event.get("payment_date") or event["payment_not_before_date"],
                        shares*amount)
                    expected[asset]["adjusted_stop"] = max(.01,
                        expected[asset]["adjusted_stop"]-amount)
                else:
                    action_counts["pending_dividend_adjustments"] += 1
                for oid,order in accepted.items():
                    if order["security_id"]==asset and order["action"]=="BUY":
                        pending_stop_adjustments[oid] = max(.01,
                            float(proposed[oid]["decision_stop"])-amount)
                action_counts["cash_dividends"] += 1
            elif kind == "SPLIT":
                ratio = event["numerator"] / event["denominator"]
                if asset in held:
                    expected[asset]["shares"] *= ratio
                    expected[asset]["adjusted_stop"] /= ratio
                action_counts["splits"] += 1
            elif kind == "TERMINAL_CASH":
                _check(event["entitlement_date"] == decision,
                       "TERMINAL_ENTITLEMENT_DATE_MISMATCH")
                if asset in held:
                    claims[event["event_id"]] = (event["payment_date"],
                        held[asset]["shares"]*float(event["cash_per_raw_share"]))
                    expected.pop(asset)
                action_counts["terminals"] += 1
            else:
                raise AuditBlocked("UNSUPPORTED_EVENT_TYPE")
        if any(pay_day <= execution for pay_day,_ in claims.values()):
            for key,(pay_day,amount) in list(claims.items()):
                if pay_day <= execution:
                    payments += amount
                    del claims[key]
                    action_counts["receivable_payments"] += 1
        _check(_close(s3["cash"],s0["cash"]+payments) and
               _close(s3["dividend_receivable"],sum(v for _,v in claims.values())),
               "ACTION_CASH_OR_RECEIVABLE_MISMATCH")
        actual = _positions(s3)
        _check(set(actual)==set(expected), "ACTION_POSITION_SET_MISMATCH")
        for asset,p in expected.items():
            _check(_close(p["shares"],actual[asset]["shares"]) and
                   _close(p["adjusted_stop"],actual[asset]["adjusted_stop"]),
                   "ACTION_SHARES_OR_STOP_MISMATCH")
        fills = [r for r in orders if r["order_state"]=="FILLED" and
                 r["decision_date"]==decision and r["execution_date"]==execution]
        for fill in fills:
            oid = fill["order_id"]
            if oid in pending_stop_adjustments:
                actual_stop = _positions(s4)[fill["security_id"]]["adjusted_stop"]
                _check(_close(actual_stop,pending_stop_adjustments[oid]),
                       "PENDING_DIVIDEND_STOP_MISMATCH")
        fill_cost = 0.0
        cash_delta = 0.0
        for fill in fills:
            asset = fill["security_id"]
            marked = (_positions(s3) if fill["action"]=="SELL" else _positions(s4))[asset]["marked_price"]
            qty = fill["filled_shares"]
            cost = qty * marked * .0005 + 10
            _check(_close(cost,fill["realized_cost"]), "FILL_COST_MISMATCH")
            fill_cost += cost
            cash_delta += (1 if fill["action"]=="SELL" else -1) * qty*fill["execution_price"] - 10
        _check(_close(s3["nav"]-s4["nav"],fill_cost) and
               _close(s4["realized_execution_cost"],fill_cost) and
               _close(s4["cash"]-s3["cash"],cash_delta),
               "OPENING_FILL_NAV_OR_CASH_MISMATCH")
        _check(_close(s5["cash"],s4["cash"]) and
               _close(s5["dividend_receivable"],s4["dividend_receivable"]),
               "INTRADAY_CASH_OR_RECEIVABLE_MISMATCH")
        prior_close = s5
    return {"status":"PASS" if complete else "PARTIAL", "pairs":expected_pairs,
            "snapshots":len(snapshots),"order_reconciliation":lifecycle,
            "accounting_events":action_counts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory",required=True)
    parser.add_argument("--events",required=True)
    parser.add_argument("--db",required=True)
    parser.add_argument("--allow-blocked-prefix",action="store_true")
    args = parser.parse_args()
    try:
        result = audit(args.directory,args.events,args.db,
                       allow_blocked_prefix=args.allow_blocked_prefix)
    except (AuditBlocked, OSError, ValueError, KeyError, IndexError) as exc:
        print(json.dumps({"status":"BLOCKED","reason":str(exc).split(":")[0]}))
        raise SystemExit(2)
    print(json.dumps(result,sort_keys=True))


if __name__ == "__main__":
    main()
