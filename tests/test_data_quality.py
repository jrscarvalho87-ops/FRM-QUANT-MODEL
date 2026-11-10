"""Deterministic tests: python -m unittest discover -s tests -v"""
import unittest
from data_quality import normalize_candles, gap_report


def candle(ts, o="100", h="110", l="90", c="105", confirm="1"):
    return [str(ts),o,h,l,c,"12","12","1200",confirm]


class CandleQualityTests(unittest.TestCase):
    def test_chronological_and_deduplicated(self):
        rows, rejected = normalize_candles([candle(1800000),candle(900000),candle(900000)])
        self.assertEqual([r["ts"] for r in rows],[900000,1800000])
        self.assertEqual(rejected["duplicate"],1)

    def test_unconfirmed_excluded(self):
        rows, rejected = normalize_candles([candle(900000,confirm="0")])
        self.assertEqual(rows,[])
        self.assertEqual(rejected["unconfirmed"],1)

    def test_bad_high_low_excluded(self):
        rows, rejected = normalize_candles([candle(900000,h="99"),candle(1800000,l="106")])
        self.assertEqual(rows,[])
        self.assertEqual(rejected["malformed"],2)

    def test_non_finite_and_negative_excluded(self):
        rows, rejected = normalize_candles([candle(900000,h="NaN"),candle(1800000,o="-2")])
        self.assertEqual(rows,[])
        self.assertEqual(rejected["malformed"],2)

    def test_gap_not_filled(self):
        rows, _ = normalize_candles([candle(900000),candle(3600000)])
        self.assertEqual(gap_report(rows,900000),2)
        self.assertEqual(len(rows),2)


if __name__ == "__main__":
    unittest.main()
