"""Synthetic-only NG-SF-270-LW adapter and action accounting checks."""

import sys
from decimal import Decimal as D
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from portfolio.ng_sf_270_lw_inputs_v1 import (
    InputBlocked, prepare_pair, economic_entry_gate, normalized_entry,
    decision_stop_raw, raw_execution_mark,
)
from portfolio.ng_sf_270_lw_actions_v1 import (
    ActionAccount, ActionBlocked, CashDividend, Split, TerminalCash,
)


def views(n=271, *, raw_price=20, raw_volume=1000000, cap_factor=2, tr_factor=3):
    days = [f"2020-{1+i//28:02d}-{1+i%28:02d}" for i in range(n)]
    raw = [{"date": d, "open": raw_price, "high": raw_price+1,
            "low": raw_price-1, "close": raw_price, "volume": raw_volume}
           for d in days]
    def scaled(price_factor, volume_factor):
        return [{**r, **{k: r[k]*price_factor for k in ("open", "high", "low", "close")},
                 "volume": r["volume"]*volume_factor} for r in raw]
    return {"NONE": raw, "CAPITAL": scaled(cap_factor, 1/cap_factor),
            "TOTALRETURN": scaled(tr_factor, 1/tr_factor)}, days


def test_270_boundary_and_forward_isolation():
    stock, days = views()
    spy, _ = views(raw_price=100)
    with pytest.raises(InputBlocked, match="INSUFFICIENT"):
        prepare_pair(stock, spy, days[268])
    pair = prepare_pair(stock, spy, days[269])
    assert len(pair["stock"]["signal_bars"]) == 270
    assert pair["stock"]["signal_bars"][-1]["close"] == 20
    mutated, _ = views()
    mutated["TOTALRETURN"][-1]["close"] = 999
    mutated["NONE"][-1]["close"] = 999
    assert prepare_pair(mutated, spy, days[269]) == pair


def test_factor_invariance_stop_units_and_raw_economic_gate():
    stock, days = views()
    spy, _ = views(raw_price=100)
    first = prepare_pair(stock, spy, days[-1])
    revised, _ = views(cap_factor=10, tr_factor=7)
    second = prepare_pair(revised, spy, days[-1])
    assert first["stock"]["signal_bars"] == second["stock"]["signal_bars"]
    assert first["stock"]["signal_bars"][-1]["volume"] == 1000000
    assert economic_entry_gate(first, min_buy_price=5,
                               min_avg_dollar_volume_20=15_000_000)["liquidity_pass"]
    assert not economic_entry_gate(first, min_buy_price=25,
                                   min_avg_dollar_volume_20=15_000_000)["min_price_pass"]
    # A stop computed from normalized signal bars already has raw T price units.
    assert first["stock"]["signal_bars"][-1]["low"] == 19
    assert decision_stop_raw({"close": 20, "planned_stop_adjusted": 19}, first) == 19
    assert raw_execution_mark({**stock["NONE"][-1], "mode": "NONE"}, days[-1]) == 20
    with pytest.raises(InputBlocked, match="EXECUTION_REQUIRES_NONE"):
        raw_execution_mark({**stock["TOTALRETURN"][-1], "mode": "TOTALRETURN"}, days[-1])


def test_alignment_and_volume_convention_fail_closed():
    stock, days = views()
    spy, _ = views()
    spy["NONE"].pop(100)
    with pytest.raises(InputBlocked, match="MISALIGNMENT"):
        prepare_pair(stock, spy, days[-1])
    stock, days = views()
    stock["CAPITAL"][5]["volume"] *= 2
    with pytest.raises(InputBlocked, match="VOLUME_CONVENTION"):
        prepare_pair(stock, views()[0], days[-1])


def test_normalized_entry_uses_separate_economic_gates():
    features = {"uptrend": True, "momentum_63": .1, "momentum_126": .2,
                "rs_63": .01, "rs_126": .02, "setup": "breakout",
                "stop_fraction": .05, "entry_confirmed": False}
    assert normalized_entry(features, {"min_price_pass": True, "liquidity_pass": True})
    assert not normalized_entry(features, {"min_price_pass": False, "liquidity_pass": True})


def account():
    a = ActionAccount(cash=D("100"),
                      positions={1: {"shares": 10, "initial_shares": 10,
                                     "stop": D("9"), "avg_cost": D("10")}},
                      pending_orders=[{"order_id": "b", "asset_id": 1,
                                       "action": "BUY", "shares": 4,
                                       "accepted_planned_shares": 4,
                                       "stop": D("8"), "state": "QUEUED"}])
    a.close_session("2020-01-01")
    return a


def test_verified_dividend_receivable_pending_stop_and_payment():
    a = account()
    ev = CashDividend("div1", 1, "2019-12-01", "2020-01-01",
                      "2020-01-02", "2020-01-04", D("1"), "issuer-notice", True)
    a.process_open("2020-01-02", [ev])
    assert a.cash == 100 and a.outstanding() == 10
    assert a.positions[1]["stop"] == 8
    assert a.pending_orders[0]["stop"] == 7
    assert a.nav({1: D("9")}) == 200
    a.close_session("2020-01-02")
    a.process_open("2020-01-04", [])
    assert a.cash == 110 and a.outstanding() == 0


def test_verified_split_rebases_position_order_and_preserves_nav():
    a = account()
    before = a.nav({1: D("10")})
    a.process_open("2020-01-02", [Split("split1", 1, "2020-01-02", 2, 1,
                                        "issuer-notice", True)])
    assert a.positions[1] == {"shares": 20, "initial_shares": 20,
                              "stop": D("4.5"), "avg_cost": D("5")}
    assert a.pending_orders[0]["shares"] == 8
    assert a.pending_orders[0]["stop"] == 4
    assert a.nav({1: D("5")}) == before
    assert len(a.lifecycle) == 1


def test_fractional_split_and_unverified_terms_are_atomic_blockers():
    a = account()
    a.pending_orders[0]["shares"] = 3
    a.pending_orders[0]["accepted_planned_shares"] = 3
    original = a.nav({1: D("10")})
    with pytest.raises(ActionBlocked, match="FRACTIONAL_PENDING"):
        a.process_open("2020-01-02", [Split("split1", 1, "2020-01-02", 1, 2,
                                            "issuer-notice", True)])
    assert a.nav({1: D("10")}) == original and not a.applied_event_ids
    with pytest.raises(ActionBlocked, match="UNVERIFIED"):
        a.process_open("2020-01-02", [Split("split2", 1, "2020-01-02", 2, 1,
                                            "provider-factor", False)])


def test_verified_cash_terminal_cancels_pending_and_settles_only_on_payment():
    a = account()
    ev = TerminalCash("term1", 1, "2020-01-02", "2020-01-01",
                      "2020-01-04", D("11"), "merger-terms", True)
    a.process_open("2020-01-02", [ev])
    assert not a.positions and a.cash == 100 and a.outstanding() == 110
    assert a.pending_orders[0]["state"] == "CANCELLED"
    assert a.lifecycle[-1]["reason"] == "VERIFIED_TERMINAL_EVENT"
    a.close_session("2020-01-02")
    a.process_open("2020-01-04", [])
    assert a.cash == 210 and a.outstanding() == 0


def test_unknown_terminal_terms_and_duplicate_event_block():
    a = account()
    with pytest.raises(ActionBlocked, match="MISSING_EVENT_TERMS"):
        a.process_open("2020-01-02", [TerminalCash("term", 1, "2020-01-02",
            "2020-01-01", "2020-01-04", None, "notice", True)])
    assert a.positions[1]["shares"] == 10
    event = Split("split", 1, "2020-01-02", 2, 1, "notice", True)
    with pytest.raises(ActionBlocked, match="DUPLICATE_EVENT_ID"):
        a.process_open("2020-01-02", [event, event])
    assert a.positions[1]["shares"] == 10
