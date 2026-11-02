"""Synthetic validation only: no provider data or historical simulation."""

import json
import math
import sys
import ast
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from portfolio.decision_execution_log_v1 import (
    LocalJournal, exposure, implementation_gap, projected_positions, stable_id,
    reconcile_directory,
)


def snapshot(positions, prices, *, nav=1000, cash=100, receivable=0, budget=.04):
    return exposure(positions, prices, nav, cash=cash, receivable=receivable,
                    budget=budget, price_source="synthetic", price_time="T")


def test_no_order_and_planned_sells_buys_mixed():
    before = {"AAA": {"shares": 10, "initial_stop": 90}}
    assert projected_positions(before, []) == before
    assert snapshot(before, {"AAA": 100})["marked_stop_gap_exposure"] == .11
    sell = {"ticker": "AAA", "action": "SELL", "shares": 4}
    buy = {"ticker": "BBB", "action": "BUY", "shares": 2, "stop": 40}
    assert projected_positions(before, [sell]) == {"AAA": {"shares": 6, "initial_stop": 90}}
    assert projected_positions({}, [buy])["BBB"]["shares"] == 2
    final = projected_positions(before, [sell, buy])
    assert final["AAA"]["shares"] == 6 and final["BBB"]["shares"] == 2
    assert before["AAA"]["shares"] == 10
    assert math.isclose(snapshot(final, {"AAA": 100, "BBB": 50})["risk_numerator"], 66 + 2*(10+.5))


def test_combined_mpb_overlay_netting_and_rejection(tmp_path):
    journal = LocalJournal(tmp_path, run_id="synthetic", policy_id="B",
                           config_hash="c", manifest_hash="m")
    did = stable_id("decision", "synthetic", "B", "T")
    oid = stable_id("order", "synthetic", "B", "T", "AAA", "SELL")
    details = dict(ticker="AAA", action="SELL", requested_shares=7,
                   mpb_exit_quantity=3, overlay_reduction_quantity=4,
                   final_netted_quantity=7)
    journal.lifecycle(decision_date="T", execution_date="T+1", decision_id=did,
                      order_id=oid, state="PROPOSED", **details)
    journal.lifecycle(decision_date="T", execution_date="T+1", decision_id=did,
                      order_id=oid, state="ACCEPTED", accepted_planned_shares=7)
    journal.lifecycle(decision_date="T", execution_date="T+1", decision_id=did,
                      order_id=oid, state="QUEUED")
    journal.lifecycle(decision_date="T", execution_date="T+1", decision_id=did,
                      order_id=oid, state="FILLED", filled_shares=7)
    assert sum(details[k] for k in ("mpb_exit_quantity", "overlay_reduction_quantity")) == 7
    buy_id = stable_id("order", "synthetic", "B", "T", "BBB", "BUY")
    journal.lifecycle(decision_date="T", execution_date="T+1", decision_id=did,
                      order_id=buy_id, state="PROPOSED", requested_shares=5)
    journal.lifecycle(decision_date="T", execution_date="T+1", decision_id=did,
                      order_id=buy_id, state="REJECTED", reason="CASH_LIMIT",
                      accepted_planned_shares=0, rejected_planned_shares=5)
    records = [json.loads(x) for x in (tmp_path / "orders.jsonl").read_text().splitlines()]
    assert [r["event_sequence"] for r in records] == list(range(1, len(records)+1))
    assert records[0]["order_id"] == records[3]["order_id"] == oid
    assert journal.states[oid] == "FILLED" and journal.states[buy_id] == "REJECTED"
    assert reconcile_directory(tmp_path)["status"] == "FAIL"  # no S2 in this isolated lifecycle fixture
    with pytest.raises(ValueError, match="ORDER_ALREADY_TERMINAL"):
        journal.lifecycle(decision_date="T", execution_date="T+1", decision_id=did,
                          order_id=oid, state="FILLED")


def test_overnight_gap_costs_and_dynamic_budget():
    positions = {"AAA": {"shares": 10, "initial_stop": 99}}
    plan = snapshot(positions, {"AAA": 100}, nav=1000, budget=.04)
    up = snapshot(positions, {"AAA": 105}, nav=1049, budget=.05)
    down = snapshot(positions, {"AAA": 95}, nav=949, budget=.05)
    assert implementation_gap(plan, up)["gap"] > 0
    assert implementation_gap(plan, down)["gap"] < 0
    assert implementation_gap(plan, up)["decision_budget_fraction"] == .04
    # Realized cost changes the S4 denominator; S2 keeps the T-close NAV.
    costly = snapshot(positions, {"AAA": 105}, nav=1040, budget=.04)
    assert costly["marked_stop_gap_exposure"] > up["marked_stop_gap_exposure"]
    assert plan["risk_denominator"] == 1000


def test_dividend_adjustment_split_and_missing_inputs():
    held = {"AAA": {"shares": 10, "initial_stop": 90}}
    ex_dividend = {"AAA": {"shares": 10, "initial_stop": 89}}
    assert snapshot(ex_dividend, {"AAA": 99}, receivable=10)["dividend_receivable"] == 10
    split_adjusted = {"AAA": {"shares": 20, "initial_stop": 45}}
    assert snapshot(split_adjusted, {"AAA": 50})["calculation_status"] == "VALID"
    assert snapshot(held, {})["marked_stop_gap_exposure"] is None
    assert "MISSING_OR_INVALID_PRICE:AAA" in snapshot(held, {})["missing_input_reasons"]
    assert snapshot(held, {"AAA": 100}, nav=0)["calculation_status"] == "MISSING"
    assert implementation_gap(snapshot(held, {}), snapshot(held, {"AAA": 100}))["gap"] is None


def test_determinism_forward_isolation_and_local_non_interference(tmp_path):
    past = {"AAA": {"shares": 10, "initial_stop": 95}}
    order = {"ticker": "AAA", "action": "SELL", "shares": 3}

    def run(future_price, logging):
        positions = projected_positions(past, [order])
        plan = snapshot(positions, {"AAA": 100})
        if logging:
            j = LocalJournal(tmp_path / str(future_price), run_id="same", policy_id="B",
                             config_hash="c", manifest_hash="m")
            j.emit("snapshots", decision_date="T", execution_date="T+1",
                   phase="S2_FINAL_PLAN", cutoff="T", origin="decision_time",
                   decision_id=stable_id("decision", "same", "B", "T"), **plan)
        # Synthetic full fill: 3 shares at the open, fixed adverse cost.
        cost = 3 * future_price * .0005 + 10
        cash = 100 + 3 * future_price * (1-.0005) - 10
        nav = cash + 7 * future_price
        return {"decision": order, "plan": plan, "fill": 3,
                "cash": cash, "nav": nav, "holdings": positions,
                "cost": cost, "risk": snapshot(positions, {"AAA": future_price}, nav=nav,
                                             cash=cash)}

    a = run(102, False)
    b = run(102, True)
    assert a == b
    c = run(120, True)
    assert a["decision"] == c["decision"] and a["plan"] == c["plan"]
    assert (tmp_path / "102" / "snapshots.jsonl").read_text() == (
        tmp_path / "120" / "snapshots.jsonl").read_text()
    assert stable_id("order", "same", "B", "T", "AAA") == stable_id(
        "order", "same", "B", "T", "AAA")


def test_versioned_runner_stage_order_and_no_frozen_edits():
    source = (Path(__file__).resolve().parents[1] /
              "scripts/run_mpb_lifecycle_v5u_logged_v1.py").read_text()
    markers = ["S3_PRE_FILL", "S4_POST_FILL", "S5_CLOSE",
               "S0_PRE_DECISION", "S1_AFTER_MPB_AND_OVERLAY", "S2_FINAL_PLAN"]
    for marker in markers:
        assert marker in source
    assert source.index('"S1_AFTER_MPB_AND_OVERLAY"') < source.index('"S2_FINAL_PLAN"')
    assert 'OUT = RUN_PATH' in source


def test_actual_runner_loop_non_interference_and_forward_isolation(tmp_path):
    root = Path(__file__).resolve().parents[1]
    dates = ["2020-02-03", "2020-02-04"]

    class Ledger:
        def __init__(self):
            self.amount = Decimal(0)
        def settle(self, day):
            return Decimal(0)
        def outstanding(self):
            return self.amount
        def accrue(self, event, day, shares):
            self.amount += event.amount * shares

    def execute(filename, *, future_open=102, logging=False, expect_blocker=False,
                dividend=False, split=False, future_buy_open=10.2,
                no_orders=False, sell_only=False, buy_only=False):
        source = ast.parse((root / "scripts" / filename).read_text())
        loop = next(n for n in source.body if isinstance(n, ast.For)
                    and isinstance(n.target, ast.Name) and n.target.id == "day")
        class Volume:
            def mean(self):
                return 100000.

        class Frame:
            def __len__(self):
                return 25
            @property
            def loc(self):
                return self
            @property
            def iloc(self):
                return self
            def __getitem__(self, key):
                return Volume() if key == "Volume" else self
            def tail(self, n):
                return self

        frame = Frame()
        prices = {
            ("AAA", dates[0], "Open"): 100, ("AAA", dates[0], "Close"): 100,
            ("AAA", dates[1], "Open"): future_open,
            ("AAA", dates[1], "Close"): future_open,
            ("BBB", dates[0], "Open"): 10, ("BBB", dates[0], "Close"): 10,
            ("BBB", dates[1], "Open"): future_buy_open,
            ("BBB", dates[1], "Close"): future_buy_open,
        }
        if future_open is None:
            prices.pop(("AAA", dates[1], "Open"))
        journal = LocalJournal(tmp_path / f"{filename}_{future_open}_{future_buy_open}_{dividend}_{split}_{logging}_{no_orders}_{sell_only}_{buy_only}",
                               run_id="synthetic", policy_id="B",
                               config_hash="c", manifest_hash="m") if logging else None
        event = SimpleNamespace(amount=Decimal("1"), declared_on=dates[0])
        action = {"dividends": [event] if dividend else [],
                  "splits": ["synthetic"] if split else [], "other": []}
        env = {"__builtins__": __builtins__, "math": math,
               "pd": SimpleNamespace(Timestamp=lambda day: day),
               "defaultdict": defaultdict, "Decimal": Decimal,
               "days": dates, "cash": 1000.,
               "positions": {"AAA": {"shares": 10, "initial_shares": 10,
                                      "avg_cost": 100., "initial_stop": 99.,
                                      "entry_date": "2020-01-01", "sector": "Tech"}},
               "pending": [], "trades": [], "daily": [], "ledger": Ledger(),
               "provisional_claims": {}, "provisional_events_used": set(),
               "previous_nav": 2000., "previous_day": None, "blocker": None,
               "rejections": [], "plans_count": 0,
               "overlay_trim_events": 0, "overlay_trim_shares": 0,
               "last_plan": None, "last_budget": None, "JOURNAL": journal,
               "RECORDED_PHASES": set(),
               "RUN_ID": "synthetic", "POLICY_NAME": "B", "ACTION_MODE": "STRICT",
               "ACTION_INDEX": {("AAA", dates[1]): action} if dividend or split else {},
               "EVENTS": {("AAA", dates[1]): event} if dividend else {},
               "SLIP": .0005, "FEE": 10.,
               "STRAT": SimpleNamespace(target_positions=3,
                                         order_entry_position_cap=.5,
                                         position_buffer_cap=.5,
                                         max_sector_weight=.8,
                                         min_rebalance_dollars=1,
                                         cash_operating_target_dollars=0),
               "CONTEST": SimpleNamespace(max_position_weight=.5),
               "CFG": SimpleNamespace(gap_buffer=.01, risk_per_position=.04,
                                      max_participation=.1),
               "POLICY": object(), "VOL20": None, "SIGMA_REFERENCE": None,
               "by_day": {} if no_orders or sell_only else {
                   dates[0]: [{"ticker": "BBB", "sector": "Other",
                               "planned_stop_adjusted": "9", "setup": "entry"}]},
               "budget_fraction": lambda *a, **kw: .04,
               "plan_mpb_exit": lambda **kw: SimpleNamespace(sell_shares=0 if no_orders or buy_only else 3,
                                                             reason="mpb_exit"),
               "additional_risk_trim": lambda *a, **kw: {
                   "projected_within_budget": True,
                   "extra_sells": {} if no_orders or buy_only else {"AAA": 2}},
               "stable_id": stable_id, "exposure": exposure,
               "projected_positions": projected_positions,
               "implementation_gap": implementation_gap,
               "factor_reconciles": lambda *a: True,
               "checked_dividend_amount": lambda *a: 0,
               "math": math}
        env["provisional_total"] = lambda: Decimal(0)
        env["price"] = lambda ticker, day, field="Close", kind="raw": prices[(ticker, day, field)]
        env["factor"] = lambda ticker, day: .99 if dividend and ticker == "AAA" and day == dates[1] else 1.
        env["features"] = lambda ticker, day: {"ema21": 90, "close": 100}
        env["panel"] = lambda ticker, kind: frame
        env["mark"] = lambda day, field: (env["cash"] + sum(
            p["shares"] * env["price"](ticker, day, field)
            for ticker, p in env["positions"].items()))
        if filename.endswith("logged_v1.py"):
            snap_node = next(n for n in source.body if isinstance(n, ast.FunctionDef)
                             and n.name == "snap")
            exec(compile(ast.Module(body=[snap_node], type_ignores=[]), filename, "exec"), env)
        exec(compile(ast.Module(body=[loop], type_ignores=[]), filename, "exec"), env)
        assert (env["blocker"] is not None) == expect_blocker, env["blocker"]
        economic = {key: env[key] for key in (
            "cash", "positions", "pending", "trades", "daily", "plans_count",
            "rejections", "overlay_trim_events", "overlay_trim_shares")}
        return economic, journal

    baseline, _ = execute("run_mpb_lifecycle_v5u.py")
    disabled, _ = execute("run_mpb_lifecycle_v5u_logged_v1.py")
    enabled, journal = execute("run_mpb_lifecycle_v5u_logged_v1.py", logging=True)
    assert baseline == disabled == enabled
    assert {t["action"] for t in enabled["trades"]} == {"SELL", "BUY"}
    assert journal.states and set(journal.states.values()) == {"FILLED"}
    order_rows = [json.loads(line) for line in
                  (journal.directory / "orders.jsonl").read_text().splitlines()]
    accepted = {r["order_id"]: r["accepted_planned_shares"] for r in order_rows
                if r["order_state"] == "ACCEPTED"}
    filled = {r["order_id"]: r["filled_shares"] for r in order_rows
              if r["order_state"] == "FILLED"}
    assert accepted == filled
    assert sorted(accepted.values()) == sorted(t["shares"] for t in enabled["trades"])
    assert reconcile_directory(journal.directory)["status"] == "PASS"
    future, future_journal = execute("run_mpb_lifecycle_v5u_logged_v1.py",
                                     future_open=120, logging=True)
    assert future["trades"] != enabled["trades"]
    plans = [json.loads(line) for line in
             (journal.directory / "snapshots.jsonl").read_text().splitlines()
             if '"S2_FINAL_PLAN"' in line]
    future_plans = [json.loads(line) for line in
                    (future_journal.directory / "snapshots.jsonl").read_text().splitlines()
                    if '"S2_FINAL_PLAN"' in line]
    assert plans == future_plans and len(plans) == 1
    _, missing_journal = execute("run_mpb_lifecycle_v5u_logged_v1.py",
                                 future_open=None, logging=True, expect_blocker=True)
    pairs = [json.loads(line) for line in
             (missing_journal.directory / "pairs.jsonl").read_text().splitlines()]
    assert pairs[0]["calculation_status"] == "MISSING"
    assert pairs[0]["gap"] is None
    base_div, _ = execute("run_mpb_lifecycle_v5u.py", dividend=True)
    logged_div, div_journal = execute("run_mpb_lifecycle_v5u_logged_v1.py",
                                      dividend=True, logging=True)
    assert base_div == logged_div
    s3 = [json.loads(line) for line in
          (div_journal.directory / "snapshots.jsonl").read_text().splitlines()
          if '"S3_PRE_FILL"' in line]
    assert s3[0]["dividend_receivable"] == 10
    assert s3[0]["positions"][0]["adjusted_stop"] == 98
    _, split_journal = execute("run_mpb_lifecycle_v5u_logged_v1.py",
                               split=True, logging=True, expect_blocker=True)
    assert split_journal.states and set(split_journal.states.values()) == {"CANCELLED"}
    for options in ({"no_orders": True}, {"sell_only": True}, {"buy_only": True}):
        reference, _ = execute("run_mpb_lifecycle_v5u.py", **options)
        instrumented, scenario_journal = execute("run_mpb_lifecycle_v5u_logged_v1.py",
                                                  logging=True, **options)
        assert reference == instrumented
        assert reconcile_directory(scenario_journal.directory)["status"] == "PASS"
    cash_reference, _ = execute("run_mpb_lifecycle_v5u.py", future_buy_open=1000)
    cash_logged, cash_journal = execute("run_mpb_lifecycle_v5u_logged_v1.py",
                                        future_buy_open=1000, logging=True)
    assert cash_reference == cash_logged
    assert cash_logged["rejections"][0]["reason"] == "OPENING_CASH_BUDGET"
    assert reconcile_directory(cash_journal.directory)["status"] == "PASS"
