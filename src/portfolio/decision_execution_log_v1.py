"""Local, versioned decision-to-execution evidence; no strategy decisions here."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

SCHEMA = "BATCH4A6_DECISION_EXECUTION_V1"
TERMINAL = {"REJECTED", "FILLED", "CANCELLED", "EXPIRED"}
EPSILON = 1e-9


def stable_id(kind, *parts):
    raw = json.dumps([kind, *parts], sort_keys=True, separators=(",", ":"))
    return kind.lower() + "_" + hashlib.sha256(raw.encode()).hexdigest()[:24]


def projected_positions(positions, orders):
    result = {t: dict(p) for t, p in positions.items()}
    for order in orders:
        ticker, qty = order["ticker"], int(order["shares"])
        if order["action"] == "SELL":
            if ticker not in result or qty > result[ticker]["shares"]:
                raise ValueError("INVALID_PLANNED_SELL")
            result[ticker]["shares"] -= qty
            if result[ticker]["shares"] == 0:
                del result[ticker]
        else:
            if ticker in result:
                raise ValueError("UNSUPPORTED_PLANNED_TOPUP")
            result[ticker] = {"shares": qty, "initial_stop": order["stop"]}
    return result


def exposure(positions, prices, nav, *, cash, receivable, budget,
             price_source, price_time, reference_budget=0.04):
    """Approved stop-gap numerator / actual or T-close NAV; missing is explicit."""
    reasons = []
    if not isinstance(nav, (int, float)) or not math.isfinite(nav) or nav <= 0:
        reasons.append("INVALID_NAV")
    for value, name in ((cash, "CASH"), (receivable, "RECEIVABLE"),
                        (budget, "BUDGET")):
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            reasons.append("INVALID_" + name)
    if isinstance(budget, (int, float)) and math.isfinite(budget) and budget <= 0:
        reasons.append("INVALID_BUDGET")
    rows, numerator = [], 0.0
    for ticker, p in sorted(positions.items()):
        qty = p.get("shares")
        stop = p.get("initial_stop")
        price = prices.get(ticker)
        if not isinstance(qty, int) or qty < 0:
            reasons.append("INVALID_SHARES:" + ticker)
        if not isinstance(stop, (int, float)) or not math.isfinite(stop) or stop <= 0:
            reasons.append("INVALID_STOP:" + ticker)
        if not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
            reasons.append("MISSING_OR_INVALID_PRICE:" + ticker)
        rows.append({"ticker": ticker, "security_id": p.get("security_id"),
                     "shares": qty if isinstance(qty, int) else None,
                     "adjusted_stop": stop if isinstance(stop, (int, float)) and math.isfinite(stop) else None,
                     "marked_price": price if isinstance(price, (int, float)) and math.isfinite(price) else None})
        if not reasons:
            numerator += qty * (max(0.0, price - stop) + 0.01 * price)
    valid = not reasons
    risk = numerator / nav if valid else None
    safe = lambda x: x if isinstance(x, (int, float)) and math.isfinite(x) else None
    return {"nav": safe(nav), "cash": safe(cash), "dividend_receivable": safe(receivable),
            "holdings_count": len(positions), "positions": rows,
            "valuation_price_source": price_source, "valuation_price_time": price_time,
            "risk_numerator": numerator if valid else None,
            "risk_denominator": nav if valid else None,
            "marked_stop_gap_exposure": risk, "budget_fraction": safe(budget),
            "reference_budget_fraction": safe(reference_budget),
            "budget_excess_fraction": risk - budget if valid else None,
            "calculation_status": "VALID" if valid else "MISSING",
            "missing_input_reasons": reasons}


def implementation_gap(plan, post_fill, *, epsilon=EPSILON):
    a, b = plan["marked_stop_gap_exposure"], post_fill["marked_stop_gap_exposure"]
    if a is None or b is None:
        return {"calculation_status": "MISSING", "missing_input_reasons":
                plan["missing_input_reasons"] + post_fill["missing_input_reasons"],
                "gap": None, "positive_gap": None, "compliant_to_exceedance": None}
    budget = plan["budget_fraction"]
    gap = b - a
    return {"calculation_status": "VALID", "missing_input_reasons": [],
            "gap": gap, "positive_gap": max(0.0, gap),
            "compliant_to_exceedance": int(a <= budget + epsilon and b > budget + epsilon),
            "decision_budget_fraction": budget, "epsilon": epsilon}


class LocalJournal:
    def __init__(self, directory, *, run_id, policy_id, config_hash, manifest_hash,
                 timezone="America/New_York"):
        self.directory = Path(directory)
        if self.directory.exists() and any(self.directory.iterdir()):
            raise FileExistsError("EVENT_DIRECTORY_NOT_EMPTY:" + str(self.directory))
        self.directory.mkdir(parents=True, exist_ok=True)
        self.common = {"schema": SCHEMA, "run_id": run_id, "policy_id": policy_id,
                       "strategy_config_hash": config_hash,
                       "data_manifest_hash": manifest_hash,
                       "simulation_timezone": timezone}
        self.sequence = 0
        self.states = {}
        self.order_context = {}

    def emit(self, stream, *, decision_date, execution_date, phase, cutoff,
             origin, decision_id, order_id=None, **payload):
        self.sequence += 1
        record = dict(self.common, decision_id=decision_id, order_id=order_id,
                      decision_date=decision_date, execution_date=execution_date,
                      event_sequence=self.sequence, simulation_phase=phase,
                      information_cutoff=cutoff, record_origin=origin, **payload)
        path = self.directory / (stream + ".jsonl")
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return record

    def lifecycle(self, *, decision_date, execution_date, decision_id, order_id,
                  state, reason=None, **details):
        prior = self.states.get(order_id)
        if prior in TERMINAL:
            raise ValueError("ORDER_ALREADY_TERMINAL")
        if state in {"REJECTED", "CANCELLED", "EXPIRED"} and not reason:
            raise ValueError("MISSING_TERMINAL_REASON")
        self.states[order_id] = state
        self.order_context[order_id] = (decision_date, execution_date, decision_id)
        return self.emit("orders", decision_date=decision_date,
                         execution_date=execution_date, phase="ORDER_" + state,
                         cutoff=decision_date if state in {"PROPOSED", "ACCEPTED", "QUEUED"}
                         else execution_date, origin="decision_time" if state in
                         {"PROPOSED", "ACCEPTED", "QUEUED"} else "execution_time",
                         decision_id=decision_id, order_id=order_id,
                         order_state=state, reason=reason, **details)


def reconcile_directory(directory):
    """Check archived order IDs and quantities against snapshots and fills."""
    root = Path(directory)
    def rows(stream):
        path = root / (stream + ".jsonl")
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    order_rows = rows("orders")
    snapshots = rows("snapshots")
    accepted, terminal, proposed = {}, {}, set()
    issues = []
    for row in order_rows:
        oid, state = row["order_id"], row["order_state"]
        if state == "PROPOSED":
            proposed.add(oid)
        elif state == "ACCEPTED":
            if oid in accepted:
                issues.append("DUPLICATE_ACCEPTED:" + oid)
            accepted[oid] = row
        elif state in TERMINAL:
            if oid in terminal:
                issues.append("DUPLICATE_TERMINAL:" + oid)
            terminal[oid] = row
    for oid in proposed:
        if oid not in terminal:
            issues.append("NO_TERMINAL:" + oid)
    for oid, row in accepted.items():
        if oid not in proposed:
            issues.append("NO_PROPOSAL:" + oid)
        end = terminal.get(oid)
        if end is None:
            continue
        if end["order_state"] == "FILLED" and (
            end.get("filled_shares") != row["accepted_planned_shares"]
        ):
            issues.append("FILL_QUANTITY_MISMATCH:" + oid)
        if end["order_state"] == "REJECTED" and end.get("filled_shares", 0) != 0:
            issues.append("REJECTED_WITH_FILL:" + oid)
    planned_ids = set()
    for row in snapshots:
        if row["simulation_phase"] == "S2_FINAL_PLAN":
            planned_ids.update(row["order_ids"])
    for oid in planned_ids - accepted.keys():
        issues.append("S2_WITHOUT_ACCEPTED:" + oid)
    for oid in accepted.keys() - planned_ids:
        issues.append("ACCEPTED_WITHOUT_S2:" + oid)
    return {"status": "PASS" if not issues else "FAIL",
            "issues": sorted(issues), "proposed_orders": len(proposed),
            "accepted_orders": len(accepted), "terminal_orders": len(terminal),
            "filled_orders": sum(r["order_state"] == "FILLED" for r in terminal.values()),
            "s2_order_ids": len(planned_ids)}
