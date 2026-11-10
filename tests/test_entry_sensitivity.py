import unittest
from research.entry_sensitivity import touch_sensitivity

class EntrySensitivityTests(unittest.TestCase):
    def sample(self):
        candles=[
            {"ts":0,"low":80,"high":101,"confirmed":True},
            {"ts":1,"low":93,"high":100,"confirmed":True},
            {"ts":2,"low":92,"high":100,"confirmed":True},
        ]
        signals=[{"signal_ts":0,"side":"long","stop":90,"take":100}]
        return candles,signals

    def test_no_signal_candle_fill_and_level_sensitivity(self):
        candles,signals=self.sample()
        r=touch_sensitivity(candles,signals,levels=(67,75),expiries=(1,2),
                            interval_ms=1)
        d={(v["entry_fib_percent"],v["expiry_bars"]):v for v in r["results"]}
        self.assertEqual(d[(67,1)]["touched"],1)
        self.assertEqual(d[(75,1)]["touched"],0)
        self.assertEqual(d[(75,2)]["touched"],1)

    def test_reject_gap(self):
        candles,signals=self.sample()
        candles[1]["ts"]=5
        with self.assertRaisesRegex(ValueError,"sorted|interval"):
            touch_sensitivity(candles,signals,interval_ms=1)

    def test_reject_unconfirmed(self):
        candles,signals=self.sample()
        candles[1]["confirmed"]=False
        with self.assertRaisesRegex(ValueError,"unconfirmed"):
            touch_sensitivity(candles,signals,interval_ms=1)

    def test_future_candles_not_needed_for_old_expiry(self):
        candles,signals=self.sample()
        first=touch_sensitivity(candles,signals,levels=(67,),expiries=(1,),
                                interval_ms=1)
        candles[2]["low"]=1
        second=touch_sensitivity(candles,signals,levels=(67,),expiries=(1,),
                                 interval_ms=1)
        self.assertEqual(first,second)

if __name__=="__main__":unittest.main()
