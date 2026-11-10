import unittest
from volume_profile import approximate_poc


def bar(i, lo=100, hi=110, vol=10, conf=True):
    return {"ts":(i+1)*900000,"low":str(lo),"high":str(hi),
            "volume_contracts":str(vol),"confirmed":conf}


class PocTests(unittest.TestCase):
    def test_historical_cutoff_prevents_lookahead(self):
        candles=[bar(0,100,110,100),bar(1,101,109,100),bar(2,140,150,1000000)]
        r=approximate_poc(candles,900000,1800000,bins=10)
        self.assertEqual(r["future_bars_ignored"],1)
        self.assertLess(r["poc_price_approx"],110)
        self.assertEqual(r["known_after_close_ts"],2700000)

    def test_dynamic_recalculation_when_candle_arrives(self):
        candles=[bar(0,100,110,100),bar(1,100,110,100),bar(2,130,140,1000)]
        previous=approximate_poc(candles,900000,1800000,bins=8)
        current=approximate_poc(candles,900000,2700000,bins=8)
        self.assertGreater(current["poc_price_approx"],previous["poc_price_approx"])

    def test_exact_gold_zone_overlap(self):
        candles=[bar(i,101,102,50) for i in range(3)]
        long=approximate_poc(candles,900000,2700000,bins=8,
                             zero_price=105,hundred_price=100,side="long")
        short=approximate_poc(candles,900000,2700000,bins=8,
                              zero_price=100,hundred_price=105,side="short")
        self.assertTrue(long["gold_zone"]["poc_inside_zone"])
        self.assertFalse(short["gold_zone"]["poc_inside_zone"])

    def test_reject_missing_candle(self):
        with self.assertRaisesRegex(ValueError,"Missing"):
            approximate_poc([bar(0),bar(2)],900000,2700000)

    def test_reject_anchor_not_in_history(self):
        with self.assertRaisesRegex(ValueError,"anchor"):
            approximate_poc([bar(1),bar(2)],900000,2700000)

    def test_reject_zero_volume(self):
        with self.assertRaisesRegex(ValueError,"zero contract"):
            approximate_poc([bar(0,vol=0),bar(1,vol=0)],900000,1800000)

    def test_ignore_unconfirmed(self):
        with self.assertRaisesRegex(ValueError,"As-of"):
            approximate_poc([bar(0),bar(1,conf=False)],900000,1800000)

    def test_flat_candle_keeps_its_volume(self):
        r=approximate_poc([bar(0,100,100),bar(1,100,110)],900000,1800000,bins=8)
        self.assertAlmostEqual(r["total_contract_volume"],20)

    def test_duplicate_rejected(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            approximate_poc([bar(0),bar(0),bar(1)],900000,1800000)

    def test_without_fib_no_unsupported_confluence_claim(self):
        r=approximate_poc([bar(0),bar(1)],900000,1800000,bins=8)
        self.assertNotIn("gold_zone",r)


if __name__=="__main__":
    unittest.main()
