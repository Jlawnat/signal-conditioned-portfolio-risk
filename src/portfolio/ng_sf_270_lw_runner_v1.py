"""Isolated NG-SF-270-LW policy engine. No data access or automatic run."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal as D
import math
import statistics

from portfolio.decision_execution_log_v1 import (
    exposure, implementation_gap, stable_id,
)
from portfolio.ng_sf_270_lw_actions_v1 import ActionAccount, ActionBlocked
from portfolio.ng_sf_270_lw_inputs_v1 import (
    InputBlocked, prepare_pair, economic_entry_gate, normalized_entry,
    decision_stop_raw, raw_execution_mark,
)
from portfolio.exit_policy import plan_mpb_exit
from portfolio.risk_budget import budget_fraction, additional_risk_trim

START, END = "2025-12-02", "2026-10-30"


class ExperimentBlocked(RuntimeError):
    pass


def _feature(source, feature_fn, asset, day, *, holding=False, params=None,
             feature_cache=None):
    if source.raw_row(asset, day) is None:
        raise ExperimentBlocked("MISSING_MEMBER_OR_HOLDING_T_BAR")
    if feature_cache is not None:
        cached, result = feature_cache.get(asset, day, holding)
        if cached:
            return result
    try:
        pair = prepare_pair(source.views(asset), source.views(source.spy_id), day)
    except InputBlocked as exc:
        if not holding and str(exc) == "INSUFFICIENT_OR_MISSING_T_HISTORY":
            if feature_cache is not None:
                feature_cache.put(asset, day, holding, None)
            return None
        raise ExperimentBlocked("INPUT:" + str(exc)) from exc
    result = feature_fn(pair, day)
    if not result:
        if holding:
            raise ExperimentBlocked("MISSING_HOLDING_FEATURES")
        if feature_cache is not None:
            feature_cache.put(asset, day, holding, None)
        return None
    if not holding:
        economic = economic_entry_gate(
            pair, min_buy_price=params.contest.min_buy_price,
            min_avg_dollar_volume_20=params.strat.min_avg_dollar_volume_20)
        if not normalized_entry(result, economic):
            if feature_cache is not None:
                feature_cache.put(asset, day, holding, None)
            return None
        result = dict(result, raw_stop=decision_stop_raw(result, pair),
                      raw_avg_volume20=sum(r["volume"] for r in pair["stock"]["raw_bars"][-21:-1])/20)
    if feature_cache is not None:
        feature_cache.put(asset, day, holding, result)
    return result


def _volatility(values):
    if len(values) != 21 or any(not math.isfinite(x) or x <= 0 for x in values):
        raise ExperimentBlocked("MISSING_SPY_VOLATILITY_HISTORY")
    returns = [values[i] / values[i-1] - 1 for i in range(1, 21)]
    return statistics.stdev(returns) * math.sqrt(252)


def _prestudy_volatilities(source):
    tr = {r["date"]: r["close"] for r in source.views(source.spy_id)["TOTALRETURN"]}
    ordered = sorted(tr)
    samples = []
    for i, day in enumerate(ordered):
        if "2025-01-02" <= day <= "2025-08-29" and i >= 20:
            samples.append(_volatility([tr[d] for d in ordered[i-20:i+1]]))
    if not samples:
        raise ExperimentBlocked("MISSING_PRE_STUDY_SIGMA_REFERENCE")
    return samples


def _sigma_reference(source):
    return statistics.median(_prestudy_volatilities(source))


def _fixed_comparator_budget(source, sigma_ref):
    return statistics.mean(budget_fraction("C", sigma_20=value,
                                           sigma_reference=sigma_ref)
                           for value in _prestudy_volatilities(source))


def _budget(source, day, policy, sigma_ref, fixed_budget=None):
    if policy == "F":
        return fixed_budget
    if policy != "C":
        return budget_fraction(policy)
    tr = {r["date"]: r["close"] for r in source.views(source.spy_id)["TOTALRETURN"]
          if r["date"] <= day}
    dates = sorted(tr)
    if len(dates) < 21 or dates[-1] != day:
        raise ExperimentBlocked("MISSING_DECISION_VOLATILITY")
    return budget_fraction("C", sigma_20=_volatility([tr[d] for d in dates[-21:]]),
                           sigma_reference=sigma_ref)


def _positions(account):
    return {str(a): {"shares": p["shares"], "initial_stop": float(p["stop"]),
                     "security_id": a} for a, p in account.positions.items()}


def _marks(source, account, day, field):
    result = {}
    for asset in account.positions:
        row = source.raw_row(asset, day)
        if row is None:
            raise ExperimentBlocked("MISSING_HELD_RAW_" + field.upper())
        result[asset] = raw_execution_mark(row, day, field)
    return result


def _project(account, orders):
    positions = {str(a): dict(p) for a, p in _positions(account).items()}
    for o in orders:
        key = str(o["asset_id"])
        qty = int(o["shares"])
        if o["action"] == "SELL":
            if key not in positions or qty > positions[key]["shares"]:
                raise ExperimentBlocked("INVALID_PLANNED_SELL")
            positions[key]["shares"] -= qty
            if positions[key]["shares"] == 0:
                del positions[key]
        else:
            if key in positions:
                raise ExperimentBlocked("PLANNED_TOPUP_NOT_SUPPORTED")
            positions[key] = {"shares": qty, "initial_stop": float(o["stop"]),
                              "security_id": o["asset_id"]}
    return positions


def _snapshot(journal, *, run_id, policy, phase, decision_day, execution_day,
              positions, raw_prices, nav, cash, receivable, budget, origin,
              order_ids=(), cost=None, **extra):
    value = exposure(positions, {str(k): float(v) for k, v in raw_prices.items()},
                     float(nav), cash=float(cash), receivable=float(receivable),
                     budget=budget, price_source="NONE_" +
                     ("CLOSE" if phase in ("S0_PRE_DECISION", "S1_AFTER_MPB_AND_OVERLAY",
                                           "S2_FINAL_PLAN", "S5_CLOSE") else "OPEN"),
                     price_time=decision_day if origin == "decision_time" else execution_day)
    if value["calculation_status"] != "VALID":
        raise ExperimentBlocked("MISSING_RISK:" + ",".join(value["missing_input_reasons"]))
    record = dict(value, order_ids=list(order_ids),
                  projected_execution_cost=cost if origin == "decision_time" else None,
                  realized_execution_cost=cost if origin == "execution_time" else None,
                  **extra)
    if journal:
        journal.emit("snapshots", decision_date=decision_day,
                     execution_date=execution_day, phase=phase,
                     cutoff=decision_day if origin == "decision_time" else execution_day,
                     origin=origin, decision_id=stable_id("decision", run_id, policy, decision_day),
                     **record)
    return record


def _lifecycle(journal, *, run_id, policy, decision_day, execution_day, order, state,
               reason=None, **details):
    if journal:
        journal.lifecycle(decision_date=decision_day, execution_date=execution_day,
                          decision_id=stable_id("decision", run_id, policy, decision_day),
                          order_id=order["order_id"], state=state, reason=reason,
                          ticker=order["symbol"], security_id=order["asset_id"],
                          action=order["action"], **details)


def run_policy(source, feature_fn, *, policy, params, events, run_id,
               journal=None, diagnostic=False, diagnostic_events=None,
               strict_calendar=True, feature_cache=None):
    """Run only when caller has separately authorized inputs and protocol.

    source: calendar, spy_id, members(day), views(asset), raw_row(asset,day),
    symbol(asset), action_evidence(asset,prior_day,day).
    events: mapping (day, asset_id) -> list of independently verified events.
    """
    calendar = list(source.calendar)
    if strict_calendar and (len(calendar) != 230 or calendar[0] != START or calendar[-1] != END):
        raise ExperimentBlocked("CALENDAR_NOT_APPROVED_230_SESSIONS")
    if len(calendar) < 2 or calendar != sorted(set(calendar)):
        raise ExperimentBlocked("INVALID_CALENDAR")
    if policy not in ("A", "B", "C", "F"):
        raise ExperimentBlocked("UNKNOWN_POLICY")
    if abs(params.cfg.gap_buffer-.01) > 1e-12:
        raise ExperimentBlocked("GAP_BUFFER_MISMATCH")
    sigma_ref = _sigma_reference(source) if policy in ("C", "F") else None
    fixed_budget = _fixed_comparator_budget(source, sigma_ref) if policy == "F" else None
    account = ActionAccount(cash=D("1000000"))
    daily, trades, pairs = [], [], []
    last_plan = None
    for index, day in enumerate(calendar):
        previous = calendar[index-1] if index else None
        if previous is not None:
            active = set(account.positions) | {o["asset_id"] for o in account.pending_orders}
            selected = []
            if diagnostic:
                observed_candidates = (source.event_candidates(previous, day)
                                       if hasattr(source, "event_candidates") else
                                       {asset for asset in active
                                        if source.action_evidence(asset, previous, day)})
                candidate_assets = set(observed_candidates) | {
                    asset for event_day,asset in events if event_day == day}
                for asset in sorted(candidate_assets - active):
                    if diagnostic_events is not None:
                        diagnostic_events.append({
                            "date":day, "asset_id":asset,
                            "classification":"NO_ACTUAL_PORTFOLIO_EXPOSURE",
                            "held_shares":0, "pending_order_shares":0})
            for asset in sorted(active):
                actual = list(events.get((day, asset), ()))
                observed = source.action_evidence(asset, previous, day)
                relevant = observed or bool(actual) or (
                    diagnostic and asset in candidate_assets)
                impact = None
                if diagnostic and relevant:
                    impact = {"date":day,"asset_id":asset,
                              "held_shares":account.positions.get(asset,{}).get("shares",0),
                              "pending_order_shares":sum(o["shares"] for o in account.pending_orders
                                                          if o["asset_id"]==asset and o.get("state")!="CANCELLED")}
                if len(actual) > 1:
                    if diagnostic_events is not None and impact is not None:
                        diagnostic_events.append(dict(impact,
                            classification="MATERIAL_UNRESOLVED_EVENT_BLOCKS_PATH",
                            reason="COMPOSITE_EVENT_ORDER_UNVERIFIED"))
                    raise ExperimentBlocked("COMPOSITE_EVENT_ORDER_UNVERIFIED")
                if relevant and not actual:
                    if diagnostic_events is not None and impact is not None:
                        diagnostic_events.append(dict(impact,
                            classification="MATERIAL_UNRESOLVED_EVENT_BLOCKS_PATH",
                            reason="UNVERIFIED_ACTION_TERMS"))
                    raise ExperimentBlocked("UNRESOLVED_REAL_ACTION:" + str(asset) + ":" + day)
                if diagnostic_events is not None and impact is not None and actual:
                    diagnostic_events.append(dict(impact,
                        classification="EXPOSURE_WITH_VERIFIED_ACCOUNTING_TERMS",
                        event_id=actual[0].event_id))
                selected.extend(actual)
            before_lifecycle = len(account.lifecycle)
            try:
                account.process_open(day, selected)
            except ActionBlocked as exc:
                if diagnostic_events is not None:
                    for record in reversed(diagnostic_events):
                        if record["date"] != day:
                            break
                        if record["classification"] == "EXPOSURE_WITH_VERIFIED_ACCOUNTING_TERMS":
                            record["classification"] = "MATERIAL_UNRESOLVED_EVENT_BLOCKS_PATH"
                            record["reason"] = "ACTION_ACCOUNTING_BLOCKED:" + str(exc)
                raise ExperimentBlocked("ACTION:" + str(exc)) from exc
            for change in account.lifecycle[before_lifecycle:]:
                order = next((o for o in account.pending_orders
                              if o.get("order_id") == change.get("order_id")), None)
                if order is None:
                    raise ExperimentBlocked("ACTION_ORDER_LINK_MISSING")
                _lifecycle(journal, run_id=run_id, policy=policy, decision_day=previous,
                           execution_day=day, order=order, state=change["state"],
                           reason=change.get("reason"),
                           adjusted_shares=change.get("shares"), event_id=change["event_id"])
            opening_marks = _marks(source, account, day, "open")
            open_before = account.nav(opening_marks)
            _snapshot(journal, run_id=run_id, policy=policy, phase="S3_PRE_FILL",
                      decision_day=previous, execution_day=day, positions=_positions(account),
                      raw_prices=opening_marks, nav=open_before, cash=account.cash,
                      receivable=account.outstanding(), budget=last_plan["budget_fraction"],
                      origin="execution_time")
            buy_budget = account.cash
            buy_spent = D(0)
            cost_today = 0.0
            orders = sorted(account.pending_orders, key=lambda o: o["action"] != "SELL")
            for order in orders:
                if order.get("state") == "CANCELLED":
                    continue
                asset, side, qty = order["asset_id"], order["action"], int(order["shares"])
                raw = source.raw_row(asset, day)
                if raw is None:
                    raise ExperimentBlocked("MISSING_ORDER_OPEN")
                opening = raw_execution_mark(raw, day, "open")
                execution = opening * (1 - params.slip if side == "SELL" else 1 + params.slip)
                cost = qty * opening * params.slip + params.fee
                if side == "SELL":
                    holding = account.positions.get(asset)
                    if holding is None or qty <= 0 or qty > holding["shares"]:
                        raise ExperimentBlocked("INVALID_EXECUTION_SELL")
                    account.cash += D(str(qty*execution-params.fee))
                    holding["shares"] -= qty
                    if holding["shares"] == 0:
                        del account.positions[asset]
                else:
                    if asset in account.positions or qty <= 0:
                        raise ExperimentBlocked("INVALID_EXECUTION_BUY")
                    debit = D(str(qty*execution+params.fee))
                    reason = None
                    if debit + buy_spent > buy_budget + D("0.0000001"):
                        reason = "OPENING_CASH_BUDGET"
                    elif qty*opening/float(open_before) > params.strat.order_entry_position_cap+1e-9:
                        reason = "OPENING_POSITION_CAP"
                    if reason:
                        order["state"] = "REJECTED"
                        _lifecycle(journal, run_id=run_id, policy=policy,
                                   decision_day=previous, execution_day=day,
                                   order=order, state="REJECTED", reason=reason,
                                   filled_shares=0, accepted_planned_shares=qty)
                        continue
                    buy_spent += debit
                    account.cash -= debit
                    account.positions[asset] = {"shares": qty, "initial_shares": qty,
                                                "avg_cost": D(str(execution)),
                                                "stop": D(str(order["stop"])),
                                                "entry_date": day}
                    if execution <= float(order["stop"]):
                        raise ExperimentBlocked("FILLED_BELOW_STOP_REQUIRES_POLICY")
                cost_today += cost
                trades.append({"decision_date": previous, "date": day,
                               "asset_id": asset, "action": side, "shares": qty,
                               "execution_price": execution, "execution_cost": cost,
                               "reason": order["reason"], "order_id": order["order_id"]})
                order["state"] = "FILLED"
                _lifecycle(journal, run_id=run_id, policy=policy, decision_day=previous,
                           execution_day=day, order=order, state="FILLED",
                           filled_shares=qty, accepted_planned_shares=qty,
                           execution_price=execution, realized_cost=cost)
            account.pending_orders = []
            open_after = account.nav(_marks(source, account, day, "open"))
            if not math.isclose(float(open_before-open_after), cost_today, abs_tol=.0001):
                raise ExperimentBlocked("OPEN_EXECUTION_NAV_IDENTITY_FAILED")
            post = _snapshot(journal, run_id=run_id, policy=policy, phase="S4_POST_FILL",
                             decision_day=previous, execution_day=day,
                             positions=_positions(account), raw_prices=_marks(source, account, day, "open"),
                             nav=open_after, cash=account.cash, receivable=account.outstanding(),
                             budget=last_plan["budget_fraction"], origin="execution_time", cost=cost_today)
            gap = implementation_gap(last_plan, post)
            pair = dict(decision_date=previous, execution_date=day, had_orders=bool(orders),
                        had_overlay_intervention=any("risk_budget_overlay" in o["reason"] for o in orders),
                        own_overlay_requirement=policy in ("B", "C", "F"),
                        policy_a_reference_only=policy == "A", **gap)
            pairs.append(pair)
            if journal:
                journal.emit("pairs", decision_date=previous, execution_date=day,
                             phase="IMPLEMENTATION_GAP", cutoff=day,
                             origin="execution_time",
                             decision_id=stable_id("decision", run_id, policy, previous),
                             **{k:v for k,v in pair.items() if k not in ("decision_date","execution_date")})
        close_marks = _marks(source, account, day, "close")
        nav = account.nav(close_marks)
        if nav <= 0:
            raise ExperimentBlocked("NONPOSITIVE_NAV")
        current_budget = _budget(source, day, policy, sigma_ref, fixed_budget)
        close_risk = exposure(_positions(account), {str(k):v for k,v in close_marks.items()},
                              float(nav), cash=float(account.cash),
                              receivable=float(account.outstanding()), budget=current_budget,
                              price_source="NONE_CLOSE", price_time=day)
        if close_risk["calculation_status"] != "VALID":
            raise ExperimentBlocked("MISSING_CLOSE_RISK")
        if previous is not None:
            _snapshot(journal, run_id=run_id, policy=policy, phase="S5_CLOSE",
                      decision_day=previous, execution_day=day, positions=_positions(account),
                      raw_prices=close_marks, nav=nav, cash=account.cash,
                      receivable=account.outstanding(), budget=current_budget,
                      origin="execution_time")
        daily.append({"date": day, "nav": float(nav), "cash": float(account.cash),
                      "receivable": float(account.outstanding()),
                      "holdings": len(account.positions), "risk_budget_fraction": current_budget,
                      "marked_stop_gap_exposure": close_risk["marked_stop_gap_exposure"],
                      "execution_cost": cost_today if previous else 0.0})
        account.close_session(day)
        if index == len(calendar)-1:
            break
        next_day = calendar[index+1]
        _snapshot(journal, run_id=run_id, policy=policy, phase="S0_PRE_DECISION",
                  decision_day=day, execution_day=next_day, positions=_positions(account),
                  raw_prices=close_marks, nav=nav, cash=account.cash,
                  receivable=account.outstanding(), budget=current_budget,
                  origin="decision_time")
        pending = []
        mpb = {}
        for asset, p in sorted(account.positions.items()):
            f = _feature(source, feature_fn, asset, day, holding=True,
                         params=params, feature_cache=feature_cache)
            close = close_marks[asset]
            result = plan_mpb_exit(
                shares=p["shares"], original_shares=p["initial_shares"],
                entry_cost=float(p["avg_cost"]), initial_stop=float(p["stop"]),
                close_raw=close, ema21_adjusted=float(f["ema21"]),
                close_adjusted=float(f["close"]), nav=float(nav),
                same_day=p["entry_date"] == day, policy=params.exit_policy)
            if result.sell_shares > 0:
                mpb[asset] = result.sell_shares
                pending.append({"asset_id": asset, "symbol": source.symbol(asset),
                                "action": "SELL", "shares": result.sell_shares,
                                "reason": result.reason})
        if policy in ("B", "C", "F"):
            overlay = additional_risk_trim(
                {a: {"shares": p["shares"], "stop": float(p["stop"])}
                 for a, p in account.positions.items()}, mpb,
                prices=close_marks, nav=float(nav), risk_fraction=current_budget,
                gap_buffer=params.cfg.gap_buffer)
            if not overlay["projected_within_budget"]:
                raise ExperimentBlocked("OVERLAY_TRIM_CANNOT_REACH_TARGET")
            for asset, extra in sorted(overlay["extra_sells"].items()):
                if extra <= 0:
                    continue
                existing = next((o for o in pending if o["asset_id"] == asset), None)
                if existing:
                    existing["shares"] += extra
                    existing["reason"] += "|risk_budget_overlay"
                else:
                    pending.append({"asset_id": asset, "symbol": source.symbol(asset),
                                    "action": "SELL", "shares": extra,
                                    "reason": "risk_budget_overlay"})
                if next(o for o in pending if o["asset_id"] == asset)["shares"] > account.positions[asset]["shares"]:
                    raise ExperimentBlocked("OVERLAY_OVERSELL")
        s1 = _project(account, pending)
        _snapshot(journal, run_id=run_id, policy=policy, phase="S1_AFTER_MPB_AND_OVERLAY",
                  decision_day=day, execution_day=next_day, positions=s1,
                  raw_prices={a:close_marks[int(a)] for a in s1}, nav=nav,
                  cash=account.cash, receivable=account.outstanding(),
                  budget=current_budget, origin="decision_time")
        used_risk = sum(p["shares"]*(max(0.0, close_marks[a]-float(p["stop"]))
                        + params.cfg.gap_buffer*close_marks[a]) for a,p in account.positions.items())
        projected_risk, projected_cash, planned_buys = used_risk, float(account.cash), 0
        proposed_buys = {}
        candidates = []
        for asset in source.members(day):
            if asset in account.terminal_assets:
                raise ExperimentBlocked("TERMINAL_ASSET_REENTERED_MEMBERSHIP")
            result = _feature(source, feature_fn, asset, day, params=params,
                              feature_cache=feature_cache)
            if result:
                candidates.append((asset, result))
        candidates.sort(key=lambda item: (-item[1]["score"], source.symbol(item[0])))
        for asset, f in candidates:
            if asset in account.positions:
                continue
            if len(account.positions) + planned_buys >= params.strat.target_positions:
                break
            close = close_marks.get(asset)
            if close is None:
                raw = source.raw_row(asset, day)
                close = raw_execution_mark(raw, day, "close")
            stop = f["raw_stop"]
            per_share = close-stop+close*(params.cfg.gap_buffer+params.slip)
            budget = min(params.cfg.risk_per_position*float(nav),
                         max(0, current_budget*float(nav)-projected_risk))
            limits = [math.floor(max(0,budget-2*params.fee)/per_share),
                      math.floor(min(params.strat.position_buffer_cap,
                                     params.strat.order_entry_position_cap,
                                     params.contest.max_position_weight)*float(nav)/
                                 (close*(1+params.cfg.gap_buffer))),
                      math.floor(f["raw_avg_volume20"]*params.cfg.max_participation),
                      math.floor(max(0,projected_cash-params.strat.cash_operating_target_dollars-
                                     params.fee)/(close*(1+params.cfg.gap_buffer)))]
            qty = max(0,min(limits))
            requested = max(0,min(limits[:-1]))
            proposed_buys[asset] = (requested, qty)
            if journal:
                proposal = {"asset_id":asset,"symbol":source.symbol(asset),"action":"BUY",
                            "order_id":stable_id("order",run_id,policy,day,asset,"BUY")}
                _lifecycle(journal,run_id=run_id,policy=policy,decision_day=day,
                           execution_day=next_day,order=proposal,state="PROPOSED",
                           requested_shares=requested,
                           decision_reference_price=close,decision_stop=stop,
                           cash_available=projected_cash,risk_limit_shares=limits[0],
                           position_limit_shares=limits[1],volume_limit_shares=limits[2],
                           cash_limit_shares=limits[3],strategy_component=f["setup"])
            if qty*close < params.strat.min_rebalance_dollars:
                if journal:
                    _lifecycle(journal,run_id=run_id,policy=policy,decision_day=day,
                               execution_day=next_day,order=proposal,state="REJECTED",
                               reason="MIN_REBALANCE_OR_LIMIT",filled_shares=0,
                               rejected_planned_shares=requested)
                continue
            if journal and requested > qty:
                journal.emit("orders", decision_date=day, execution_date=next_day,
                             phase="ORDER_PARTIAL_PLAN_REJECTION", cutoff=day,
                             origin="decision_time",
                             decision_id=stable_id("decision",run_id,policy,day),
                             order_id=proposal["order_id"],
                             order_state="PARTIAL_PLAN_REJECTION",
                             reason="PLANNER_CASH_LIMIT",requested_shares=requested,
                             accepted_planned_shares=qty,
                             rejected_planned_shares=requested-qty)
            pending.append({"asset_id":asset,"symbol":source.symbol(asset),"action":"BUY",
                            "shares":qty,"stop":D(str(stop)),"reason":f["setup"]})
            projected_cash -= qty*close*(1+params.cfg.gap_buffer)+params.fee
            projected_risk += qty*per_share+2*params.fee
            planned_buys += 1
        estimated_cost = 0.0
        for order in pending:
            asset, side, qty = order["asset_id"], order["action"], int(order["shares"])
            order["order_id"] = stable_id("order",run_id,policy,day,asset,side)
            order["state"] = "QUEUED"
            close = close_marks.get(asset)
            if close is None:
                close = raw_execution_mark(source.raw_row(asset,day),day,"close")
            estimated = qty*close*params.slip+params.fee
            estimated_cost += estimated
            if journal and side == "SELL":
                _lifecycle(journal,run_id=run_id,policy=policy,decision_day=day,
                           execution_day=next_day,order=order,state="PROPOSED",
                           requested_shares=qty,mpb_exit_quantity=mpb.get(asset,0),
                           overlay_reduction_quantity=qty-mpb.get(asset,0),
                           final_netted_quantity=qty,decision_reference_price=close,
                           decision_stop=float(account.positions[asset]["stop"]),
                           strategy_component=order["reason"])
            _lifecycle(journal,run_id=run_id,policy=policy,decision_day=day,
                       execution_day=next_day,order=order,state="ACCEPTED",
                       accepted_planned_shares=qty,
                       rejected_planned_shares=0 if side=="SELL" else max(0,proposed_buys[asset][0]-qty),
                       estimated_cost=estimated)
            _lifecycle(journal,run_id=run_id,policy=policy,decision_day=day,
                       execution_day=next_day,order=order,state="QUEUED",queued_shares=qty)
        account.pending_orders = pending
        s2 = _project(account, pending)
        s2_prices = {a:close_marks.get(int(a)) or raw_execution_mark(source.raw_row(int(a),day),day,"close")
                     for a in s2}
        last_plan = _snapshot(journal, run_id=run_id, policy=policy, phase="S2_FINAL_PLAN",
                              decision_day=day, execution_day=next_day, positions=s2,
                              raw_prices=s2_prices, nav=nav, cash=account.cash,
                              receivable=account.outstanding(), budget=current_budget,
                              origin="decision_time", order_ids=[o["order_id"] for o in pending],
                              cost=estimated_cost, planner_projected_cash=projected_cash,
                              nav_convention="ACTUAL_T_CLOSE")
    return {"status":"PASS","policy":policy,"daily":daily,"trades":trades,
            "pairs":pairs,"ending_cash":float(account.cash),
            "ending_receivable":float(account.outstanding()),
            "ending_positions":_positions(account),"sigma_reference":sigma_ref,
            "fixed_comparator_budget":fixed_budget}
