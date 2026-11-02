"""Versioned private NG-SF-270-LW runner; official mode requires approval file.

No command is run on import. All outputs stay under ignored restricted_norgate/.
"""

import argparse
import ast
from decimal import Decimal as D
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "norgate"))

from portfolio.decision_execution_log_v1 import LocalJournal, reconcile_directory, stable_id
from portfolio.exit_policy import ExitParameters
from portfolio.ng_sf_270_lw_actions_v1 import CashDividend, Split, TerminalCash, ActionBlocked
from portfolio.ng_sf_270_lw_inputs_v1 import InputBlocked
from portfolio.ng_sf_270_lw_runner_v1 import run_policy, ExperimentBlocked, START, END
from batch4a8_readiness import frozen_features, frame
from diagnostic_feature_cache_v1 import DiagnosticFeatureCache


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def code_manifest_hash(protocol=None):
    files = [
        ROOT/"scripts/run_ng_sf_270_lw_v1.py",
        ROOT/"src/portfolio/ng_sf_270_lw_runner_v1.py",
        ROOT/"src/portfolio/ng_sf_270_lw_inputs_v1.py",
        ROOT/"src/portfolio/ng_sf_270_lw_actions_v1.py",
        ROOT/"src/portfolio/decision_execution_log_v1.py",
        ROOT/"src/portfolio/exit_policy.py",
        ROOT/"src/portfolio/risk_budget.py",
        ROOT/"scripts/norgate/batch4a8_readiness.py",
        ROOT/"scripts/norgate/diagnostic_feature_cache_v1.py",
        ROOT/"configs/mpb_exit_reference.json",
        Path.home()/"FMA_Competition/fma_mpb_v41_20261013/fma_mpb_v41/momentum_pullback_breakout.py",
        Path.home()/"FMA_Competition/fma_mpb_v41_20261013/fma_mpb_v41/config.py",
    ]
    if protocol:
        files.append(Path(protocol))
    return hashlib.sha256("".join(sha256(p) for p in files).encode()).hexdigest()


class PrivateNorgateSource:
    def __init__(self, path):
        self.connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        self.connection.row_factory = sqlite3.Row
        meta = dict(self.connection.execute("SELECT key,value FROM metadata"))
        if (meta.get("complete") != "true" or meta.get("padding") != "NONE"
                or meta.get("sample") != "false" or
                set(meta.get("modes", "").split(",")) !=
                {"NONE","CAPITAL","CAPITALSPECIAL","TOTALRETURN"}):
            raise ExperimentBlocked("INCOMPLETE_OR_PADDED_EXTRACT")
        sec = {r["asset_id"]: dict(r) for r in self.connection.execute("SELECT * FROM securities")}
        self.symbols = {a: r["symbol"] for a, r in sec.items()}
        self.spy_id = next(a for a, s in self.symbols.items() if s == "SPY")
        self._views = {}
        self.calendar = [r[0] for r in self.connection.execute(
            "SELECT date FROM prices WHERE asset_id=? AND mode='NONE' AND date BETWEEN ? AND ? ORDER BY date",
            (self.spy_id, START, END))]

    def close(self):
        self.connection.close()

    def symbol(self, asset):
        return self.symbols[asset]

    def members(self, day):
        return {r[0] for r in self.connection.execute(
            "SELECT asset_id FROM membership WHERE date=? AND eligible=1", (day,))}

    def views(self, asset):
        if asset not in self._views:
            self._views[asset] = {mode: [dict(r) for r in self.connection.execute(
                "SELECT date,open,high,low,close,volume,turnover FROM prices WHERE asset_id=? AND mode=? ORDER BY date",
                (asset, mode))] for mode in ("NONE", "CAPITAL", "TOTALRETURN")}
        return self._views[asset]

    def raw_row(self, asset, day):
        row = self.connection.execute(
            "SELECT date,open,high,low,close,volume,turnover FROM prices WHERE asset_id=? AND mode='NONE' AND date=?",
            (asset, day)).fetchone()
        return dict(row, mode="NONE") if row else None

    def action_evidence(self, asset, previous, day):
        flag = self.connection.execute(
            "SELECT flag FROM capital_events WHERE asset_id=? AND date=?", (asset, day)).fetchone()
        if flag and flag[0] == 1:
            return True
        prev = self.connection.execute(
            "SELECT MAX(dividend) FROM prices WHERE asset_id=? AND date=? AND mode IN ('NONE','CAPITAL','CAPITALSPECIAL','TOTALRETURN')",
            (asset, previous)).fetchone()[0]
        if prev is not None and prev > 0:
            return True
        factors = []
        for date in (previous, day):
            rows = {r[0]:r[1] for r in self.connection.execute(
                "SELECT mode,close FROM prices WHERE asset_id=? AND date=? AND mode IN ('NONE','CAPITAL')",
                (asset, date))}
            if rows.get("NONE") and rows.get("CAPITAL"):
                factors.append(rows["CAPITAL"]/rows["NONE"])
        return len(factors) == 2 and not math.isclose(factors[0], factors[1], rel_tol=1e-6)

    def event_candidates(self, previous, day):
        """Provider flags, prior-date distributions, factor moves and terminal gaps."""
        result = {r[0] for r in self.connection.execute(
            "SELECT asset_id FROM capital_events WHERE date=? AND flag=1", (day,))}
        result.update(r[0] for r in self.connection.execute(
            "SELECT DISTINCT asset_id FROM prices WHERE date=? AND dividend>0", (previous,)))
        factor_assets = [r[0] for r in self.connection.execute("""
            SELECT p.asset_id FROM prices p
            JOIN prices c ON c.asset_id=p.asset_id AND c.date=p.date AND c.mode='CAPITAL'
            JOIN prices pn ON pn.asset_id=p.asset_id AND pn.date=? AND pn.mode='NONE'
            JOIN prices cn ON cn.asset_id=p.asset_id AND cn.date=? AND cn.mode='CAPITAL'
            WHERE p.mode='NONE' AND p.date=? AND p.close>0 AND pn.close>0
              AND c.close>0 AND cn.close>0
              AND ABS((cn.close/pn.close)/(c.close/p.close)-1)>0.000001
        """, (day,day,previous))]
        result.update(factor_assets)
        result.update(r[0] for r in self.connection.execute("""
            SELECT m.asset_id FROM membership m
            JOIN prices p ON p.asset_id=m.asset_id AND p.date=m.date AND p.mode='NONE'
            WHERE m.date=? AND m.eligible=1 AND NOT EXISTS(
                SELECT 1 FROM prices q WHERE q.asset_id=m.asset_id
                AND q.date=? AND q.mode='NONE')
        """, (previous,day)))
        return result


def load_verified_events(path):
    """A private event register must supply source-backed raw-share terms."""
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ExperimentBlocked("EVENT_REGISTER_NOT_LIST")
    result = {}
    types = {"CASH_DIVIDEND": CashDividend, "SPLIT": Split,
             "TERMINAL_CASH": TerminalCash}
    for row in rows:
        kind = row.get("event_type")
        if kind not in types:
            raise ExperimentBlocked("UNSUPPORTED_EVENT_REGISTER_TYPE")
        fields = {k:v for k,v in row.items() if k != "event_type"}
        if kind in ("CASH_DIVIDEND", "TERMINAL_CASH") and "cash_per_raw_share" in fields:
            fields["cash_per_raw_share"] = D(str(fields["cash_per_raw_share"]))
        event = types[kind](**fields)
        if not event.independently_verified or not event.source_id:
            raise ExperimentBlocked("UNVERIFIED_EVENT_IN_REGISTER")
        day = event.ex_date if kind == "CASH_DIVIDEND" else event.effective_date
        result.setdefault((day, event.asset_id), []).append(event)
    return result


def approved(path, protocol, db, event_path):
    record = json.loads(Path(path).read_text())
    expected_data = hashlib.sha256((sha256(db)+sha256(event_path)).encode()).hexdigest()
    codated_rule = ROOT/"docs/NG_SF_270_LW_CME_CODATED_CASH_RULE_APPROVAL_DRAFT.md"
    event_evidence = ROOT/"restricted_norgate/ng_sf_270_lw_event_evidence_v1.json"
    adapter = ROOT/"src/portfolio/ng_sf_270_lw_inputs_v1.py"
    actions = ROOT/"src/portfolio/ng_sf_270_lw_actions_v1.py"
    engine = ROOT/"src/portfolio/ng_sf_270_lw_runner_v1.py"
    frozen = Path.home()/"FMA_Competition/fma_mpb_v41_20261013/fma_mpb_v41/momentum_pullback_breakout.py"
    if (record.get("status") != "APPROVED" or not record.get("approved_on")
            or record.get("protocol_sha256") != sha256(protocol)
            or record.get("data_manifest_hash") != expected_data
            or record.get("runner_sha256") != sha256(__file__)
            or record.get("adapter_sha256") != sha256(adapter)
            or record.get("actions_sha256") != sha256(actions)
            or record.get("engine_sha256") != sha256(engine)
            or record.get("frozen_feature_sha256") != sha256(frozen)
            or record.get("code_manifest_hash") != code_manifest_hash(protocol)
            or record.get("codated_cash_rule_sha256") != sha256(codated_rule)
            or record.get("event_evidence_sha256") != sha256(event_evidence)):
        raise ExperimentBlocked("PROTOCOL_APPROVAL_MISSING_OR_MISMATCHED")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--events", required=True)
    parser.add_argument("--policy", required=True, choices=("A", "B", "C", "F"))
    parser.add_argument("--mode", choices=("diagnostic", "official"), required=True)
    parser.add_argument("--protocol")
    parser.add_argument("--approval-file")
    args = parser.parse_args()
    private = (ROOT / "restricted_norgate").resolve()
    db, event_path = Path(args.db).resolve(), Path(args.events).resolve()
    if private not in db.parents or private not in event_path.parents:
        parser.error("db and event register must stay in restricted_norgate")
    if args.mode == "official":
        if not args.protocol or not args.approval_file:
            parser.error("official mode requires protocol and approval file")
        approved(args.approval_file, args.protocol, db, event_path)
    feature, strat, contest, pd = frozen_features()
    fma_source = Path.home()/"FMA_Competition/fma_mpb_v41_20261013/fma_mpb_v41/momentum_pullback_breakout.py"
    cls = next(n for n in ast.parse(fma_source.read_text()).body
               if isinstance(n, ast.ClassDef) and n.name == "PullbackConfig")
    cfg = SimpleNamespace(**{n.target.id:ast.literal_eval(n.value) for n in cls.body
                             if isinstance(n, ast.AnnAssign) and n.value is not None})
    params = SimpleNamespace(cfg=cfg, strat=strat, contest=contest,
                             fee=float(contest.commission_per_trade),
                             slip=strat.assumed_slippage_bps/10000,
                             exit_policy=ExitParameters.from_json(ROOT/"configs/mpb_exit_reference.json"))
    data_hash = hashlib.sha256((sha256(db)+sha256(event_path)).encode()).hexdigest()
    config_hash = code_manifest_hash(args.protocol)
    run_id = stable_id("run", "NG_SF_270_LW_V1", args.policy, args.mode, data_hash, config_hash)
    output = private/"ng_sf_270_lw_v1"/run_id
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("VERSIONED_OUTPUT_EXISTS")
    source = PrivateNorgateSource(db)
    events = load_verified_events(event_path)
    feature_cache = None
    if args.mode == "diagnostic":
        # The cache stores only decision-date feature outputs. Accounting rules,
        # event evidence and the approval protocol cannot change those outputs.
        feature_sources = [
            db,
            ROOT/"src/portfolio/ng_sf_270_lw_runner_v1.py",
            ROOT/"src/portfolio/ng_sf_270_lw_inputs_v1.py",
            ROOT/"scripts/norgate/batch4a8_readiness.py",
            ROOT/"scripts/norgate/diagnostic_feature_cache_v1.py",
            fma_source,
            fma_source.with_name("config.py"),
        ]
        identity = hashlib.sha256("".join(sha256(p) for p in feature_sources).encode()).hexdigest()
        feature_cache = DiagnosticFeatureCache(
            private/("ng_sf_270_lw_feature_cache_"+args.policy+"_"+identity[:20]+".sqlite"),
            identity)
    def feature_fn(pair, day):
        return feature(frame(pair["stock"]["signal_bars"], pd),
                       frame(pair["spy"]["signal_bars"], pd), pd.Timestamp(day))
    # Controlled diagnostics retain the same private S0–S5 and order journal so a
    # completed path can be reconciled without publishing a performance result.
    journal = LocalJournal(output, run_id=run_id, policy_id=args.policy,
                           config_hash=config_hash, manifest_hash=data_hash)
    diagnostic_events = [] if args.mode == "diagnostic" else None
    if args.mode == "diagnostic":
        output.mkdir(parents=True, exist_ok=True)
    try:
        result = run_policy(source, feature_fn, policy=args.policy, params=params,
                            events=events, run_id=run_id, journal=journal,
                            diagnostic=args.mode == "diagnostic",
                            diagnostic_events=diagnostic_events,
                            feature_cache=feature_cache)
        if args.mode == "official":
            result["reconciliation"] = reconcile_directory(output)
            if result["reconciliation"]["status"] != "PASS":
                raise ExperimentBlocked("ORDER_RECONCILIATION_FAILED")
            (output/"result_private.json").write_text(json.dumps(result,indent=2)+"\n")
            print(json.dumps({"status":"PASS","policy":args.policy,"run_id":run_id,
                              "sessions":len(result["daily"]),"reconciliation":"PASS"}))
        else:
            reconciliation = reconcile_directory(output)
            if reconciliation["status"] != "PASS":
                raise ExperimentBlocked("DIAGNOSTIC_ORDER_RECONCILIATION_FAILED")
            (output/"diagnostic_private.json").write_text(json.dumps({
                "status":"NO_AFFECTED_EVENT_FOUND","policy":args.policy,
                "event_classifications":diagnostic_events,
                "reconciliation":reconciliation,
                "sessions_checked":len(result["daily"]),
                "decision_open_pairs_checked":len(result["pairs"]),
                "performance_not_reported":True},indent=2)+"\n")
            print(json.dumps({"status":"DIAGNOSTIC_COMPLETE_NO_AFFECTED_EVENT",
                              "policy":args.policy,"reconciliation":"PASS",
                              "performance_not_reported":True}))
    except (ExperimentBlocked, InputBlocked, ActionBlocked, ValueError, KeyError) as exc:
        if journal:
            for oid,state in list(journal.states.items()):
                if state not in ("FILLED","REJECTED","CANCELLED","EXPIRED"):
                    ddate,edate,did=journal.order_context[oid]
                    journal.lifecycle(decision_date=ddate,execution_date=edate,
                                      decision_id=did,order_id=oid,state="CANCELLED",
                                      reason="SIMULATION_ABORT")
        if args.mode == "official":
            (output/"blocked_private.json").write_text(json.dumps({"status":"BLOCKED",
                "reason":str(exc),"policy":args.policy},indent=2)+"\n")
        else:
            (output/"diagnostic_private.json").write_text(json.dumps({
                "status":"BLOCKED_AT_FIRST_AFFECTED_EVENT","policy":args.policy,
                "private_reason":str(exc),"event_classifications":diagnostic_events,
                "later_events_not_evaluable":True,
                "performance_not_reported":True},indent=2)+"\n")
        safe_reason=str(exc).split(":")[0]
        print(json.dumps({"status":"BLOCKED","reason":safe_reason,
                          "performance_not_reported":True}))
        raise SystemExit(2)
    finally:
        if feature_cache is not None:
            feature_cache.close()
        source.close()


if __name__ == "__main__":
    main()
