import sys
import unittest
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from portfolio.corporate_actions import (
    DividendLedger, load_events, factor_reconciles
)


class TestCashDividend(unittest.TestCase):
    def setUp(self):
        self.event = load_events(
            ROOT / "configs/verified_cash_dividends.json"
        )[("USB", "2025-09-30")]
        self.ledger = DividendLedger()

    def test_event_metadata(self):
        self.assertEqual(self.event.amount, D("0.52"))
        self.assertEqual(self.event.pay_date, "2025-10-15")

    def test_factor_reconciliation(self):
        self.assertTrue(factor_reconciles(
            self.event,
            0.9527356766843671,
            0.9629568677966316,
            48.9900016784668,
        ))

    def test_receivable_before_payment(self):
        amount = self.ledger.accrue(
            self.event, "2025-09-30", 300
        )
        self.assertEqual(amount, D("156.00"))
        self.assertEqual(
            self.ledger.outstanding(), D("156.00")
        )
        self.assertEqual(
            self.ledger.settle("2025-10-14"), D("0")
        )

    def test_payment_on_correct_date(self):
        self.ledger.accrue(
            self.event, "2025-09-30", 300
        )
        self.assertEqual(
            self.ledger.settle("2025-10-15"), D("156.00")
        )
        self.assertEqual(
            self.ledger.outstanding(), D("0")
        )
        self.assertEqual(
            self.ledger.settle("2025-10-16"), D("0")
        )

    def test_ex_date_new_buyer_not_entitled(self):
        # The caller provides prior-close shares, not
        # shares purchased at the ex-date opening.
        self.assertEqual(
            self.ledger.accrue(
                self.event, "2025-09-30", 0
            ),
            D("0"),
        )
        self.assertEqual(
            self.ledger.outstanding(), D("0")
        )

    def test_duplicate_claim_rejected(self):
        self.ledger.accrue(
            self.event, "2025-09-30", 100
        )
        with self.assertRaises(ValueError):
            self.ledger.accrue(
                self.event, "2025-09-30", 100
            )

    def test_wrong_ex_date_rejected(self):
        with self.assertRaises(ValueError):
            self.ledger.accrue(
                self.event, "2025-09-29", 100
            )


if __name__ == "__main__":
    unittest.main()
