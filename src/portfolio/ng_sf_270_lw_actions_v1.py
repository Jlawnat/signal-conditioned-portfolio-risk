"""Fail-closed, verified-event accounting for the draft NG-SF-270-LW model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal as D
from copy import deepcopy


class ActionBlocked(ValueError):
    pass


def _day(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ActionBlocked("MISSING_OR_INVALID_EVENT_DATE") from None


def _money(value, *, positive=True):
    if value is None:
        raise ActionBlocked("MISSING_EVENT_TERMS")
    try:
        number = D(str(value))
    except Exception:
        raise ActionBlocked("INVALID_EVENT_AMOUNT") from None
    if not number.is_finite() or (number <= 0 if positive else number < 0):
        raise ActionBlocked("INVALID_EVENT_AMOUNT")
    return number


@dataclass(frozen=True)
class CashDividend:
    event_id: str
    asset_id: int
    declared_on: str
    entitlement_date: str
    ex_date: str
    payment_date: str | None
    cash_per_raw_share: D
    source_id: str
    independently_verified: bool
    payment_not_before_date: str | None = None


@dataclass(frozen=True)
class Split:
    event_id: str
    asset_id: int
    effective_date: str
    numerator: int
    denominator: int
    source_id: str
    independently_verified: bool


@dataclass(frozen=True)
class TerminalCash:
    event_id: str
    asset_id: int
    effective_date: str
    entitlement_date: str
    payment_date: str
    cash_per_raw_share: D
    source_id: str
    independently_verified: bool
    successor_asset_id: int | None = None
    fractional_treatment: str | None = None


@dataclass
class ActionAccount:
    cash: D
    positions: dict = field(default_factory=dict)
    pending_orders: list = field(default_factory=list)
    receivables: list = field(default_factory=list)
    last_close_date: str | None = None
    last_open_date: str | None = None
    applied_event_ids: set = field(default_factory=set)
    terminal_assets: set = field(default_factory=set)
    lifecycle: list = field(default_factory=list)

    def close_session(self, day):
        _day(day)
        if self.last_open_date and day < self.last_open_date:
            raise ActionBlocked("CLOSE_BEFORE_OPEN")
        if self.last_close_date and day <= self.last_close_date:
            raise ActionBlocked("NONMONOTONE_CLOSE")
        self.last_close_date = day

    def outstanding(self):
        return sum((r["amount"] for r in self.receivables if not r["paid"]), D(0))

    def nav(self, raw_marks):
        value = self.cash + self.outstanding()
        for asset, p in self.positions.items():
            if asset not in raw_marks:
                raise ActionBlocked("MISSING_RAW_MARK")
            value += D(p["shares"]) * _money(raw_marks[asset])
        return value

    def process_open(self, day, events):
        """Settle documented claims, then apply verified ex/effective events atomically."""
        today = _day(day)
        if self.last_close_date is None or _day(self.last_close_date) >= today:
            raise ActionBlocked("MISSING_PRIOR_CLOSE")
        if self.last_open_date and _day(self.last_open_date) >= today:
            raise ActionBlocked("NONMONOTONE_OPEN")
        work = deepcopy(self)
        for claim in work.receivables:
            if claim["paid"]:
                continue
            if claim["payment_date"] is None:
                if today >= _day(claim.get("payment_not_before_date")):
                    raise ActionBlocked("UNKNOWN_PAYMENT_DATE_REACHED")
                continue
            if _day(claim["payment_date"]) <= today:
                work.cash += claim["amount"]
                claim["paid"] = True
        for event in events:
            if not getattr(event, "event_id", None) or event.event_id in work.applied_event_ids:
                raise ActionBlocked("MISSING_OR_DUPLICATE_EVENT_ID")
            if not getattr(event, "independently_verified", False) or not getattr(event, "source_id", None):
                raise ActionBlocked("UNVERIFIED_EVENT_TERMS")
            if isinstance(event, CashDividend):
                payment_limit = event.payment_date or event.payment_not_before_date
                if ((event.payment_date is None) == (event.payment_not_before_date is None)) or (
                    _day(event.declared_on) > _day(event.entitlement_date)
                    or not (_day(event.entitlement_date) < _day(event.ex_date) < _day(payment_limit))
                    or event.ex_date != day or event.entitlement_date != self.last_close_date
                ):
                    raise ActionBlocked("INVALID_DIVIDEND_TIMELINE")
                amount = _money(event.cash_per_raw_share)
                shares = work.positions.get(event.asset_id, {}).get("shares", 0)
                if shares:
                    work.receivables.append({"event_id": event.event_id, "asset_id": event.asset_id,
                                             "amount": amount * shares,
                                             "payment_date": event.payment_date,
                                             "payment_not_before_date": event.payment_not_before_date,
                                             "entitled_shares": shares, "paid": False})
                    p = work.positions[event.asset_id]
                    p["stop"] = max(D("0.01"), D(str(p["stop"])) - amount)
                for order in work.pending_orders:
                    if order["asset_id"] == event.asset_id and order["action"] == "BUY":
                        order["stop"] = max(D("0.01"), D(str(order["stop"])) - amount)
            elif isinstance(event, Split):
                if event.effective_date != day or type(event.numerator) is not int or type(event.denominator) is not int or min(event.numerator, event.denominator) <= 0:
                    raise ActionBlocked("INVALID_SPLIT_TERMS")
                ratio = D(event.numerator) / D(event.denominator)
                p = work.positions.get(event.asset_id)
                if p:
                    for field_name in ("shares", "initial_shares"):
                        if field_name in p:
                            changed = D(p[field_name]) * ratio
                            if changed != changed.to_integral_value():
                                raise ActionBlocked("FRACTIONAL_SPLIT_SHARES_UNRESOLVED")
                            p[field_name] = int(changed)
                    p["stop"] = D(str(p["stop"])) / ratio
                    if "avg_cost" in p:
                        p["avg_cost"] = D(str(p["avg_cost"])) / ratio
                for order in work.pending_orders:
                    if order["asset_id"] != event.asset_id or order.get("state") in ("CANCELLED", "FILLED"):
                        continue
                    for field_name in ("shares", "requested_shares", "accepted_planned_shares"):
                        if field_name in order:
                            changed = D(order[field_name]) * ratio
                            if changed != changed.to_integral_value():
                                raise ActionBlocked("FRACTIONAL_PENDING_ORDER_UNRESOLVED")
                            order[field_name] = int(changed)
                    if "stop" in order:
                        order["stop"] = D(str(order["stop"])) / ratio
                    work.lifecycle.append({"order_id": order.get("order_id"),
                                           "state": "ADJUSTED_FOR_VERIFIED_SPLIT",
                                           "event_id": event.event_id, "shares": order["shares"]})
            elif isinstance(event, TerminalCash):
                if event.successor_asset_id is not None or event.fractional_treatment is not None:
                    raise ActionBlocked("UNSUPPORTED_SUCCESSOR_OR_FRACTIONAL_TERMS")
                if event.effective_date != day or event.entitlement_date != self.last_close_date or _day(event.payment_date) < today:
                    raise ActionBlocked("INVALID_TERMINAL_TIMELINE")
                amount = _money(event.cash_per_raw_share, positive=False)
                p = work.positions.pop(event.asset_id, None)
                if p:
                    work.receivables.append({"event_id": event.event_id, "asset_id": event.asset_id,
                                             "amount": amount * p["shares"],
                                             "payment_date": event.payment_date,
                                             "entitled_shares": p["shares"], "paid": False})
                work.terminal_assets.add(event.asset_id)
                for order in work.pending_orders:
                    if order["asset_id"] == event.asset_id and order.get("state") not in ("CANCELLED", "FILLED"):
                        order["state"] = "CANCELLED"
                        work.lifecycle.append({"order_id": order.get("order_id"), "state": "CANCELLED",
                                               "reason": "VERIFIED_TERMINAL_EVENT", "event_id": event.event_id})
            else:
                raise ActionBlocked("UNSUPPORTED_EVENT_TYPE")
            work.applied_event_ids.add(event.event_id)
        # Same-day documented settlement, if terms explicitly permit it.
        for claim in work.receivables:
            if claim["paid"] or claim["payment_date"] is None:
                continue
            if _day(claim["payment_date"]) <= today:
                work.cash += claim["amount"]
                claim["paid"] = True
        work.last_open_date = day
        self.__dict__.update(work.__dict__)
