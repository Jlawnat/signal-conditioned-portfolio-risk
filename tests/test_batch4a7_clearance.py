"""Synthetic eligibility tests; no licensed data."""
import importlib.util
from datetime import date, timedelta
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('clearance',Path(__file__).resolve().parents[1]/'scripts/norgate/batch4a7_clearance.py')
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)

class ClearanceTests(unittest.TestCase):
    def setUp(self):
        self.dates=[(date(2020,1,1)+timedelta(days=i)).isoformat() for i in range(300)]
    def test_269_270_boundary(self):
        self.assertEqual(module.history_state(self.dates,self.dates,self.dates[268]),'PIT_ELIGIBLE_NO_SIGNAL_WARMUP')
        self.assertEqual(module.history_state(self.dates,self.dates,self.dates[269]),'HISTORY_READY_NOT_SIGNAL_PROVEN')
    def test_future_bars_do_not_cure_short_history(self):
        d=self.dates[125]
        self.assertEqual(module.history_state(self.dates,self.dates,d),module.history_state(self.dates[:126],self.dates[:126],d))
    def test_equal_counts_do_not_prove_alignment(self):
        shifted=self.dates[:100]+self.dates[101:]
        self.assertEqual(module.history_state(shifted,self.dates,self.dates[270]),'BLOCKED_CALENDAR_ALIGNMENT')
    def test_different_mode_match_is_only_numeric(self):
        self.assertFalse(module.hypothesis(None,1))
        self.assertFalse(module.hypothesis(2,1))
        self.assertTrue(module.hypothesis(1.005,1))
if __name__=='__main__': unittest.main()
