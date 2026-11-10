import unittest
from market_audit import audit_sample


def candle(i, vol="10", high="101", low="99"):
    return [str(900000 * (i+1)),"100",high,low,"100",vol,"1","100","1"]


class AuditTests(unittest.TestCase):
    def test_clean_sample(self):
        report = audit_sample([candle(i) for i in range(100)])
        self.assertEqual(report["status"],"sample_pass")
        self.assertEqual(report["missing_intervals"],0)

    def test_zero_volume(self):
        report = audit_sample([candle(i,vol="0") for i in range(100)])
        self.assertIn("zero_volume",report["reasons"])

    def test_missing_candles(self):
        report = audit_sample([candle(i) for i in range(100) if i not in (20,21,22)])
        self.assertIn("missing_candles",report["reasons"])

    def test_price_spikes(self):
        report = audit_sample([candle(i,high="130" if i < 5 else "101") for i in range(100)])
        self.assertIn("extreme_intrabar_ranges",report["reasons"])

    def test_small_sample(self):
        report = audit_sample([candle(i) for i in range(20)])
        self.assertIn("insufficient_sample",report["reasons"])


if __name__ == "__main__":
    unittest.main()
