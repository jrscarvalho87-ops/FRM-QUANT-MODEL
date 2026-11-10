import unittest
from htf_context import four_hour_context

MS=900000

class FourHourContextTests(unittest.TestCase):
    def bars(self,n):
        return [{"ts":i*MS,"open":100,"high":115,
                 "low":95,"close":100,"confirmed":True}
                for i in range(n)]

    def test_complete_4h_range_only(self):
        bars=self.bars(32)
        bars[-1]["close"]=110
        r=four_hour_context(bars,31,lookback_4h_bars=2)
        self.assertEqual(r["status"],"ok")
        self.assertEqual(r["position"],"premium")
        self.assertEqual(r["last_completed_4h_end_ts"],32*MS)

    def test_cannot_use_incomplete_4h(self):
        bars=self.bars(31)
        self.assertEqual(
            four_hour_context(bars,30,lookback_4h_bars=2)["status"],
            "insufficient_complete_4h_periods")

    def test_future_bar_ignored(self):
        bars=self.bars(33)
        bars[32].update({"high":999,"low":1,"confirmed":False})
        earlier=four_hour_context(bars[:32],31,lookback_4h_bars=2)
        later=four_hour_context(bars,31,lookback_4h_bars=2)
        self.assertEqual(earlier,later)

    def test_bad_sample_rejected(self):
        bars=self.bars(32)
        bars[12]["ts"]+=1
        with self.assertRaisesRegex(ValueError,"gap"):
            four_hour_context(bars,31,lookback_4h_bars=2)

if __name__=="__main__":
    unittest.main()
