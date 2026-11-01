"""Audited cash-dividend accounting for research simulations."""

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal as D


@dataclass(frozen=True)
class CashDividend:
    ticker: str
    declared_on: str
    ex_date: str
    pay_date: str
    amount: D

    def __post_init__(self):
        declared = date.fromisoformat(self.declared_on)
        ex = date.fromisoformat(self.ex_date)
        pay = date.fromisoformat(self.pay_date)

        if not declared <= ex < pay:
            raise ValueError("INVALID_EVENT_TIMELINE")
        if not self.amount.is_finite() or self.amount <= 0:
            raise ValueError("INVALID_DIVIDEND_AMOUNT")


def load_events(path):
    rows = json.loads(path.read_text(encoding="utf-8"))
    events = {}

    for row in rows:
        if (
            row["event_type"] != "CASH_DIVIDEND"
            or row["currency"] != "USD"
            or not row.get("source")
        ):
            raise ValueError("UNVERIFIED_EVENT_METADATA")

        e = CashDividend(
            ticker=row["ticker"],
            declared_on=row["declared_on"],
            ex_date=row["ex_date"],
            pay_date=row["pay_date"],
            amount=D(row["amount_per_share"]),
        )
        key = (e.ticker, e.ex_date)

        if key in events:
            raise ValueError("DUPLICATE_CORPORATE_ACTION")
        events[key] = e

    return events


def factor_reconciles(event, old_factor, new_factor,
                      previous_raw_close, tolerance_bps=D("5")):
    """Verify dividend-adjustment arithmetic against raw prices."""
    f0 = D(str(old_factor))
    f1 = D(str(new_factor))
    close = D(str(previous_raw_close))

    if min(f0, f1, close) <= 0 or close <= event.amount:
        return False

    observed = f1 / f0 - 1
    expected = 1 / (1 - event.amount / close) - 1
    return abs(observed - expected) * 10000 <= tolerance_bps


class DividendLedger:
    def __init__(self):
        self.claims = {}

    def accrue(self, event, day, eligible_shares):
        """Recognize receivable for shares held BEFORE ex-date."""
        if day != event.ex_date:
            raise ValueError("NOT_EX_DATE")
        if type(eligible_shares) is not int or eligible_shares < 0:
            raise ValueError("INVALID_ELIGIBLE_SHARES")

        key = (event.ticker, event.ex_date)
        if key in self.claims:
            raise ValueError("DUPLICATE_DIVIDEND_ACCRUAL")

        if eligible_shares == 0:
            return D("0")

        amount = event.amount * eligible_shares

        self.claims[key] = {
            "pay_date": event.pay_date,
            "receivable": amount,
            "paid": False,
            "eligible_shares": eligible_shares,
        }
        return amount

    def settle(self, day):
        """Convert receivable to cash, never before payment date."""
        received = D("0")

        for claim in self.claims.values():
            if not claim["paid"] and day >= claim["pay_date"]:
                received += claim["receivable"]
                claim["paid"] = True

        return received

    def outstanding(self):
        return sum(
            (
                c["receivable"]
                for c in self.claims.values()
                if not c["paid"]
            ),
            D("0"),
        )

    def total_accrued(self):
        return sum(
            (c["receivable"] for c in self.claims.values()),
            D("0"),
        )
