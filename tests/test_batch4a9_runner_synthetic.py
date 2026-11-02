"""End-to-end synthetic tests of the isolated policy loop; no Norgate data."""

from datetime import date, timedelta
from decimal import Decimal as D
from pathlib import Path
from types import SimpleNamespace
import json
import importlib.util
import sqlite3
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/norgate"))
from diagnostic_feature_cache_v1 import DiagnosticFeatureCache
from portfolio.decision_execution_log_v1 import LocalJournal, reconcile_directory
from portfolio.exit_policy import ExitParameters
from portfolio.ng_sf_270_lw_actions_v1 import CashDividend, Split, TerminalCash
from portfolio.ng_sf_270_lw_runner_v1 import run_policy, ExperimentBlocked


def weekdays_ending(end, count):
    current, result = date.fromisoformat(end), []
    while len(result) < count:
        if current.weekday() < 5:
            result.append(current.isoformat())
        current -= timedelta(days=1)
    return result[::-1]


class SyntheticSource:
    spy_id = 99
    def __init__(self, *, days=("2025-12-02", "2025-12-03", "2025-12-04"),
                 members=True, prices=None, evidence=(), terminal_missing=False):
        self.calendar = list(days)
        self._members = members
        self.evidence = set(evidence)
        self.prices = prices or {}
        self.terminal_missing = terminal_missing
        self.history = weekdays_ending(self.calendar[-1], 310)
        self._views = {}
        for asset, base in ((1,20.), (99,100.)):
            raw = []
            for index,day in enumerate(self.history):
                price = self.prices.get((asset,day),
                                        base*(1+.0002*index+.001*(index%5)) if asset==99 else base)
                opening = self.prices.get((asset,day,"open"),price)
                closing = self.prices.get((asset,day,"close"),price)
                if asset == 1 and terminal_missing and day == self.calendar[-1]:
                    continue
                raw.append({"date":day,"open":opening,"high":max(opening,closing)*1.01,
                            "low":min(opening,closing)*.99,"close":closing,"volume":1_000_000.})
            self._views[asset] = {"NONE":raw,
                "CAPITAL":[{**r, **{k:r[k]*2 for k in ("open","high","low","close")},
                            "volume":r["volume"]/2} for r in raw],
                "TOTALRETURN":[{**r, **{k:r[k]*3 for k in ("open","high","low","close")},
                               "volume":r["volume"]/3} for r in raw]}
        self._raw = {(a,r["date"]):dict(r,mode="NONE")
                     for a,v in self._views.items() for r in v["NONE"]}

    def members(self, day):
        return {1} if self._members and day != self.calendar[-1] else set()
    def views(self, asset):
        return self._views[asset]
    def raw_row(self, asset, day):
        return self._raw.get((asset,day))
    def symbol(self, asset):
        return {1:"SYN",99:"SPY"}[asset]
    def action_evidence(self, asset, previous, day):
        return (asset,day) in self.evidence
    def event_candidates(self, previous, day):
        return {asset for asset,event_day in self.evidence if event_day==day}


def feature(pair, day):
    close = pair["stock"]["signal_bars"][-1]["close"]
    return {"close":close,"ema21":close*.9,"score":1.,"setup":"breakout",
            "uptrend":True,"momentum_63":.1,"momentum_126":.2,
            "rs_63":.1,"rs_126":.2,"stop_fraction":.05,
            "planned_stop_adjusted":close*.95}


def parameters():
    return SimpleNamespace(
        cfg=SimpleNamespace(gap_buffer=.01,risk_per_position=.005,max_participation=.01),
        strat=SimpleNamespace(min_avg_dollar_volume_20=15_000_000.,
                              target_positions=14,position_buffer_cap=.072,
                              order_entry_position_cap=.085,
                              cash_operating_target_dollars=50_000.,
                              min_rebalance_dollars=4_000.),
        contest=SimpleNamespace(min_buy_price=5.,max_position_weight=.10),
        fee=10.,slip=.0005,
        exit_policy=ExitParameters.from_json(
            Path(__file__).resolve().parents[1]/"configs/mpb_exit_reference.json"))


def run(source, *, policy="A", events=None, journal=None):
    return run_policy(source, feature, policy=policy, params=parameters(),
                      events=events or {}, run_id="synthetic", journal=journal,
                      strict_calendar=False)


def test_no_order_snapshots_and_policy_budgets(tmp_path):
    source = SyntheticSource(members=False)
    journal = LocalJournal(tmp_path,run_id="synthetic",policy_id="A",
                           config_hash="c",manifest_hash="m")
    result = run(source,journal=journal)
    assert result["status"] == "PASS" and len(result["daily"]) == 3
    assert result["trades"] == [] and len(result["pairs"]) == 2
    assert all(p["gap"] == 0 for p in result["pairs"])
    phases = [json.loads(x)["simulation_phase"] for x in
              (tmp_path/"snapshots.jsonl").read_text().splitlines()]
    assert phases == ["S0_PRE_DECISION","S1_AFTER_MPB_AND_OVERLAY","S2_FINAL_PLAN",
                      "S3_PRE_FILL","S4_POST_FILL","S5_CLOSE",
                      "S0_PRE_DECISION","S1_AFTER_MPB_AND_OVERLAY","S2_FINAL_PLAN",
                      "S3_PRE_FILL","S4_POST_FILL","S5_CLOSE"]
    assert reconcile_directory(tmp_path)["status"] == "PASS"


def test_buy_fill_cost_nav_and_logging_non_interference(tmp_path):
    source = SyntheticSource()
    baseline = run(source,policy="B")
    journal = LocalJournal(tmp_path,run_id="synthetic",policy_id="B",
                           config_hash="c",manifest_hash="m")
    logged = run(source,policy="B",journal=journal)
    assert baseline == logged
    assert logged["trades"][0]["action"] == "BUY"
    assert logged["daily"][1]["execution_cost"] > 10
    assert logged["daily"][1]["nav"] < 1_000_000
    assert logged["daily"][1]["cash"] > 0
    assert reconcile_directory(tmp_path)["status"] == "PASS"
    assert all(p["calculation_status"] == "VALID" for p in logged["pairs"])


def test_opening_cash_rejection_and_future_bar_isolation(tmp_path):
    days=("2025-12-02","2025-12-03")
    first = SyntheticSource(days=days,prices={(1,"2025-12-03"):1000.})
    journal = LocalJournal(tmp_path/"a",run_id="synthetic",policy_id="A",
                           config_hash="c",manifest_hash="m")
    result = run(first,journal=journal)
    assert not result["trades"]
    orders = [json.loads(x) for x in (journal.directory/"orders.jsonl").read_text().splitlines()]
    assert any(x["order_state"]=="REJECTED" and x["reason"]=="OPENING_CASH_BUDGET"
               for x in orders)
    assert reconcile_directory(journal.directory)["status"] == "PASS"
    other = SyntheticSource(days=days,prices={(1,"2025-12-03"):40.})
    j2 = LocalJournal(tmp_path/"b",run_id="synthetic",policy_id="A",
                      config_hash="c",manifest_hash="m")
    run(other,journal=j2)
    def first_plan(j):
        return next(json.loads(x) for x in (j.directory/"snapshots.jsonl").read_text().splitlines()
                    if '"S2_FINAL_PLAN"' in x)
    assert first_plan(journal) == first_plan(j2)
    class FutureMembershipChanged(SyntheticSource):
        def members(self, day):
            return set() if day==self.calendar[1] else super().members(day)
    j3=LocalJournal(tmp_path/"c",run_id="synthetic",policy_id="A",
                    config_hash="c",manifest_hash="m")
    run(FutureMembershipChanged(days=days),journal=j3)
    j4=LocalJournal(tmp_path/"d",run_id="synthetic",policy_id="A",
                    config_hash="c",manifest_hash="m")
    run(SyntheticSource(days=days),journal=j4)
    assert first_plan(j3)==first_plan(j4)


def test_dividend_receivable_payment_and_open_close_nav():
    days=("2025-12-02","2025-12-03","2025-12-04","2025-12-05")
    source=SyntheticSource(days=days,evidence={(1,days[2])},
                           prices={(1,days[2]):19.})
    event=CashDividend("d",1,"2025-11-01",days[1],days[2],days[3],
                       D("1"),"independent-notice",True)
    result=run(source,events={(days[2],1):[event]})
    assert result["daily"][2]["receivable"]>0
    assert result["daily"][3]["receivable"]==0
    assert result["daily"][3]["cash"]>result["daily"][2]["cash"]


def test_split_pending_order_and_terminal_cash(tmp_path):
    days=("2025-12-02","2025-12-03","2025-12-04","2025-12-05")
    # Day 2 fills the buy; a day-3 close prompts a sell pending across the split.
    source=SyntheticSource(days=days,evidence={(1,days[3])},
                           prices={(1,days[2],"close"):50.,(1,days[3]):25.})
    split=Split("s",1,days[3],2,1,"independent-notice",True)
    journal=LocalJournal(tmp_path/"split",run_id="synthetic",policy_id="A",
                         config_hash="c",manifest_hash="m")
    result=run(source,events={(days[3],1):[split]},journal=journal)
    rows=[json.loads(x) for x in (journal.directory/"orders.jsonl").read_text().splitlines()]
    assert any(r["order_state"]=="ADJUSTED_FOR_VERIFIED_SPLIT" for r in rows)
    assert reconcile_directory(journal.directory)["status"]=="PASS"
    assert any(t["action"]=="SELL" for t in result["trades"])
    terminal_days=days[:3]
    terminal_source=SyntheticSource(days=terminal_days,evidence={(1,terminal_days[2])},
                                    terminal_missing=True)
    terminal=TerminalCash("t",1,terminal_days[2],terminal_days[1],"2025-12-08",D("20"),
                          "independent-terms",True)
    terminal_result=run(terminal_source,events={(terminal_days[2],1):[terminal]})
    assert terminal_result["ending_positions"]=={}
    assert terminal_result["ending_receivable"]>0


def test_unresolved_held_event_and_missing_terminal_fail_closed():
    days=("2025-12-02","2025-12-03","2025-12-04")
    source=SyntheticSource(days=days,evidence={(1,days[2])})
    with pytest.raises(ExperimentBlocked,match="UNRESOLVED_REAL_ACTION"):
        run(source)
    no_price=SyntheticSource(days=days,terminal_missing=True)
    with pytest.raises(ExperimentBlocked,match="MISSING_HELD_RAW_OPEN"):
        run(no_price)


def test_terminal_event_cancels_pending_sell_in_journal(tmp_path):
    days=("2025-12-02","2025-12-03","2025-12-04","2025-12-05")
    source=SyntheticSource(days=days,evidence={(1,days[3])},terminal_missing=True,
                           prices={(1,days[2],"close"):50.})
    event=TerminalCash("terminal",1,days[3],days[2],"2025-12-08",
                       D("25"),"independent-terms",True)
    journal=LocalJournal(tmp_path,run_id="synthetic",policy_id="A",
                         config_hash="c",manifest_hash="m")
    result=run(source,events={(days[3],1):[event]},journal=journal)
    rows=[json.loads(x) for x in (tmp_path/"orders.jsonl").read_text().splitlines()]
    assert any(r["order_state"]=="CANCELLED" and
               r["reason"]=="VERIFIED_TERMINAL_EVENT" for r in rows)
    assert reconcile_directory(tmp_path)["status"]=="PASS"
    assert result["ending_receivable"]>0


def test_controlled_diagnostic_stops_at_first_affected_event():
    days=("2025-12-02","2025-12-03","2025-12-04")
    source=SyntheticSource(days=days,evidence={(2,days[1]),(1,days[2])})
    classifications=[]
    with pytest.raises(ExperimentBlocked,match="UNRESOLVED_REAL_ACTION"):
        run_policy(source,feature,policy="A",params=parameters(),events={},
                   run_id="synthetic",diagnostic=True,
                   diagnostic_events=classifications,strict_calendar=False)
    assert [r["classification"] for r in classifications]==[
        "NO_ACTUAL_PORTFOLIO_EXPOSURE","MATERIAL_UNRESOLVED_EVENT_BLOCKS_PATH"]
    assert classifications[1]["held_shares"]>0


def test_controlled_diagnostic_records_verified_exposure():
    days=("2025-12-02","2025-12-03","2025-12-04")
    source=SyntheticSource(days=days,evidence={(1,days[2])})
    dividend=CashDividend("verified-div",1,"2025-11-01",days[1],days[2],
                          "2025-12-08",D("1"),"independent-notice",True)
    classifications=[]
    result=run_policy(source,feature,policy="A",params=parameters(),
                      events={(days[2],1):[dividend]},run_id="synthetic",
                      diagnostic=True,diagnostic_events=classifications,
                      strict_calendar=False)
    assert result["status"]=="PASS"
    assert [r["classification"] for r in classifications]==[
        "EXPOSURE_WITH_VERIFIED_ACCOUNTING_TERMS"]
    assert classifications[0]["held_shares"]>0


def test_completed_diagnostic_private_arithmetic_audit(tmp_path):
    audit_path=Path(__file__).resolve().parents[1]/"scripts/norgate/reconcile_ng_sf_diagnostic_v1.py"
    spec=importlib.util.spec_from_file_location("private_diagnostic_audit",audit_path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT=tmp_path
    private=tmp_path/"restricted_norgate"
    private.mkdir()
    db=private/"synthetic.sqlite"
    db.write_bytes(b"synthetic")
    days=("2025-12-02","2025-12-03","2025-12-04","2025-12-05")
    source=SyntheticSource(days=days,evidence={(1,days[2])})
    event=CashDividend("verified-div",1,"2025-11-01",days[1],days[2],
                       days[3],D("1"),"independent-notice",True)
    event_path=private/"events.json"
    event_path.write_text(json.dumps([{"event_type":"CASH_DIVIDEND",
        "event_id":"verified-div","asset_id":1,"declared_on":"2025-11-01",
        "entitlement_date":days[1],"ex_date":days[2],"payment_date":days[3],
        "cash_per_raw_share":"1","source_id":"independent-notice",
        "independently_verified":True}]))
    import hashlib
    data_hash=hashlib.sha256((module._sha256(db)+module._sha256(event_path)).encode()).hexdigest()
    output=private/"synthetic_run"
    journal=LocalJournal(output,run_id="synthetic",policy_id="A",
                         config_hash="c",manifest_hash=data_hash)
    classifications=[]
    result=run_policy(source,feature,policy="A",params=parameters(),
                      events={(days[2],1):[event]},run_id="synthetic",
                      journal=journal,diagnostic=True,
                      diagnostic_events=classifications,strict_calendar=False)
    assert result["status"]=="PASS"
    (output/"diagnostic_private.json").write_text(json.dumps({
        "status":"NO_AFFECTED_EVENT_FOUND","performance_not_reported":True}))
    checked=module.audit(output,event_path,db,expected_pairs=3)
    assert checked["status"]=="PASS"
    assert checked["snapshots"]==18
    assert checked["accounting_events"]["cash_dividends"]==1
    assert checked["accounting_events"]["receivable_payments"]==1
    private_path=output/"diagnostic_private.json"
    private_path.write_text(json.dumps({"status":"BLOCKED_AT_FIRST_AFFECTED_EVENT",
                                        "performance_not_reported":True}))
    partial=module.audit(output,event_path,db,allow_blocked_prefix=True)
    assert partial["status"]=="PARTIAL" and partial["pairs"]==3
    private_path.write_text(json.dumps({"status":"NO_AFFECTED_EVENT_FOUND",
                                        "performance_not_reported":True}))
    pair_path=output/"pairs.jsonl"
    pair_rows=[json.loads(line) for line in pair_path.read_text().splitlines()]
    pair_rows[0]["gap"]+=.01
    pair_path.write_text("\n".join(json.dumps(row) for row in pair_rows)+"\n")
    with pytest.raises(module.AuditBlocked,match="IMPLEMENTATION_GAP_ARITHMETIC_MISMATCH"):
        module.audit(output,event_path,db,expected_pairs=3)


def test_same_day_composite_action_requires_explicit_policy():
    days=("2025-12-02","2025-12-03","2025-12-04")
    source=SyntheticSource(days=days,evidence={(1,days[2])})
    dividend=CashDividend("div",1,"2025-11-01",days[1],days[2],
                          "2025-12-08",D("1"),"notice",True)
    split=Split("split",1,days[2],2,1,"notice",True)
    with pytest.raises(ExperimentBlocked,match="COMPOSITE_EVENT_ORDER_UNVERIFIED"):
        run(source,events={(days[2],1):[dividend,split]})


def test_codated_cash_dividend_aggregate_equivalence():
    from portfolio.ng_sf_270_lw_actions_v1 import ActionAccount
    from copy import deepcopy

    day = "2026-03-10"
    account = ActionAccount(cash=D("1000"), positions={1: {
        "shares": 81, "initial_shares": 81, "stop": D("230"),
        "avg_cost": D("250")}}, pending_orders=[{
        "asset_id": 1, "action": "BUY", "shares": 5,
        "stop": D("230"), "state": "ACCEPTED"}])
    account.close_session("2026-03-09")
    separate = deepcopy(account)
    combined = deepcopy(account)
    base = (1, "2026-02-12", "2026-03-09", day, "2026-03-26")
    separate.process_open(day, [
        CashDividend("regular", *base, D("1.30"), "issuer", True),
        CashDividend("annual", *base, D("6.15"), "issuer", True)])
    combined.process_open(day, [CashDividend(
        "combined", *base, D("7.45"), "issuer", True)])
    assert separate.outstanding() == combined.outstanding() == D("603.45")
    assert separate.positions[1]["stop"] == combined.positions[1]["stop"]
    assert separate.pending_orders[0]["stop"] == combined.pending_orders[0]["stop"]
    assert sum(r["amount"] for r in separate.receivables) == combined.receivables[0]["amount"]


def test_dividend_with_only_post_window_payment_lower_bound_fails_closed():
    from portfolio.ng_sf_270_lw_actions_v1 import ActionAccount, ActionBlocked

    account = ActionAccount(cash=D("1000"), positions={1: {
        "shares": 10, "stop": D("90"), "avg_cost": D("100")}})
    account.close_session("2026-10-22")
    event = CashDividend("pg", 1, "2026-10-13", "2026-10-22",
                         "2026-10-23", None, D("1.0885"), "issuer", True,
                         payment_not_before_date="2026-11-16")
    account.process_open("2026-10-23", [event])
    assert account.cash == D("1000")
    assert account.outstanding() == D("10.8850")
    assert account.receivables[0]["payment_date"] is None
    account.close_session("2026-10-30")
    with pytest.raises(ActionBlocked, match="UNKNOWN_PAYMENT_DATE_REACHED"):
        account.process_open("2026-11-16", [])


def test_diagnostic_feature_cache_replay_preserves_policy_path(tmp_path):
    source = SyntheticSource()
    uncached = run(source)
    cache_path = tmp_path/"features.sqlite"
    cache = DiagnosticFeatureCache(cache_path, "synthetic-source-and-code-hash")
    first = run_policy(source, feature, policy="A", params=parameters(),
                       events={}, run_id="synthetic", strict_calendar=False,
                       diagnostic=True, feature_cache=cache)
    cache.close()
    with sqlite3.connect(cache_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM features").fetchone()[0] > 0
    cache = DiagnosticFeatureCache(cache_path, "synthetic-source-and-code-hash")
    second = run_policy(source, feature, policy="A", params=parameters(),
                        events={}, run_id="synthetic", strict_calendar=False,
                        diagnostic=True, feature_cache=cache)
    cache.close()
    assert first == second == uncached
    with pytest.raises(ValueError, match="CACHE_IDENTITY_MISMATCH"):
        DiagnosticFeatureCache(cache_path, "different-source-or-code-hash")


def test_policy_c_reference_is_pre_study_only():
    source=SyntheticSource(members=False)
    result=run(source,policy="C")
    assert result["sigma_reference"]>0
    assert all(.02<=d["risk_budget_fraction"]<=.05 for d in result["daily"])
    fixed=run(source,policy="F")
    assert .02<=fixed["fixed_comparator_budget"]<=.05
    assert all(d["risk_budget_fraction"]==fixed["fixed_comparator_budget"]
               for d in fixed["daily"])


def test_overlay_is_applied_after_mpb_and_only_to_overlay_policies(tmp_path):
    days=("2025-12-02","2025-12-03","2025-12-04","2025-12-05")
    source=SyntheticSource(days=days,prices={(1,days[2],"close"):50.,
                                               (1,days[3]):50.})
    a=run(source,policy="A")
    journal=LocalJournal(tmp_path,run_id="synthetic",policy_id="B",
                         config_hash="c",manifest_hash="m")
    b=run(source,policy="B",journal=journal)
    a_sells=sum(t["shares"] for t in a["trades"] if t["action"]=="SELL")
    b_sells=sum(t["shares"] for t in b["trades"] if t["action"]=="SELL")
    assert b_sells>a_sells
    orders=[json.loads(x) for x in (tmp_path/"orders.jsonl").read_text().splitlines()]
    combined=[x for x in orders if x["order_state"]=="PROPOSED" and
              x["action"]=="SELL" and x["decision_date"]==days[2]]
    assert len(combined)==1
    assert combined[0]["final_netted_quantity"] == (
        combined[0]["mpb_exit_quantity"]+combined[0]["overlay_reduction_quantity"])
    assert combined[0]["overlay_reduction_quantity"]>0


def test_private_source_bridge_uses_pit_membership_and_raw_rows(tmp_path):
    path=tmp_path/"synthetic.sqlite"
    conn=sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE metadata(key TEXT,value TEXT);
        CREATE TABLE securities(asset_id INTEGER,symbol TEXT);
        CREATE TABLE prices(asset_id INTEGER,mode TEXT,date TEXT,open REAL,high REAL,
            low REAL,close REAL,volume REAL,turnover REAL,dividend REAL);
        CREATE TABLE membership(asset_id INTEGER,date TEXT,eligible INTEGER);
        CREATE TABLE capital_events(asset_id INTEGER,date TEXT,flag INTEGER);
    """)
    conn.executemany("INSERT INTO metadata VALUES (?,?)",[("complete","true"),
        ("padding","NONE"),("sample","false"),
        ("modes","NONE,CAPITAL,CAPITALSPECIAL,TOTALRETURN")])
    conn.executemany("INSERT INTO securities VALUES (?,?)",[(1,"SYN"),(99,"SPY")])
    for asset in (1,99):
        for day in ("2025-12-02","2025-12-03"):
            for mode in ("NONE","CAPITAL","CAPITALSPECIAL","TOTALRETURN"):
                conn.execute("INSERT INTO prices VALUES (?,?,?,?,?,?,?,?,?,?)",
                             (asset,mode,day,20,21,19,20,1000000,20000000,
                              1 if asset==1 and day=="2025-12-02" else 0))
    conn.executemany("INSERT INTO membership VALUES (?,?,?)",[(1,"2025-12-02",1),
        (1,"2025-12-03",0)])
    conn.commit();conn.close()
    cli=Path(__file__).resolve().parents[1]/"scripts/run_ng_sf_270_lw_v1.py"
    spec=importlib.util.spec_from_file_location("synthetic_ng_cli",cli)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    source=module.PrivateNorgateSource(path)
    try:
        assert source.members("2025-12-02")=={1}
        assert source.members("2025-12-03")==set()
        assert source.raw_row(1,"2025-12-02")["mode"]=="NONE"
        assert source.action_evidence(1,"2025-12-02","2025-12-03")
        assert 1 in source.event_candidates("2025-12-02","2025-12-03")
    finally:
        source.close()
    register=tmp_path/"events.json"
    register.write_text("[]")
    assert module.load_verified_events(register)=={}
    protocol=tmp_path/"draft.md";protocol.write_text("draft")
    approval=tmp_path/"approval.json";approval.write_text('{"status":"DRAFT"}')
    with pytest.raises(ExperimentBlocked,match="PROTOCOL_APPROVAL"):
        module.approved(approval,protocol,path,register)
