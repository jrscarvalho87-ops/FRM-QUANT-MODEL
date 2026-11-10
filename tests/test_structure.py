import unittest
from structure import scan_structure


def candle(i, high, low, close):
    return {"ts":(i+1)*900000,"high":str(high),"low":str(low),"close":str(close),"confirmed":True}


class StructureTests(unittest.TestCase):
    def test_bullish_bos_after_pivot_confirmation(self):
        highs=[105,106,108,120,112,110,111,122]
        lows=[95,96,98,100,99,98,97,106]
        closes=[100,101,102,110,109,107,108,121]
        bars=[candle(i,highs[i],lows[i],closes[i]) for i in range(len(highs))]
        events=scan_structure(bars,pivot_span=3)
        bulls=[b for b in events["bos"] if b["direction"]=="bullish"]
        self.assertEqual(len(bulls),1)
        self.assertEqual(bulls[0]["detected_at_ts"],bars[7]["ts"])
        self.assertEqual(bulls[0]["known_after_close_ts"],bars[7]["ts"]+900000)
        self.assertEqual(bulls[0]["swing_confirmed_ts"],bars[6]["ts"])
        self.assertEqual(bulls[0]["swing_pivot_ts"],bars[3]["ts"])

    def test_three_candle_bullish_fvg_detected_at_third_close(self):
        bars=[candle(0,100,95,98),candle(1,102,99,101),candle(2,107,104,106)]
        events=scan_structure(bars)
        self.assertEqual(len(events["fvg"]),1)
        self.assertEqual(events["fvg"][0]["detected_at_ts"],bars[2]["ts"])
        self.assertEqual(events["fvg"][0]["known_after_close_ts"],bars[2]["ts"]+900000)
        self.assertEqual(events["fvg"][0]["lower"],100)
        self.assertEqual(events["fvg"][0]["upper"],104)

    def test_bearish_fvg(self):
        bars=[candle(0,110,100,105),candle(1,105,95,100),candle(2,90,80,85)]
        events=scan_structure(bars)
        self.assertEqual(events["fvg"][0]["direction"],"bearish")

    def test_no_future_pivot_on_short_history(self):
        highs=[105,106,108,120,112,110]
        lows=[95,96,98,100,99,98]
        closes=[100,101,102,110,109,107]
        bars=[candle(i,highs[i],lows[i],closes[i]) for i in range(6)]
        events=scan_structure(bars)
        self.assertEqual(events["pivots"],[])
        self.assertEqual(events["bos"],[])

    def test_unconfirmed_not_allowed(self):
        b=candle(0,100,90,95)
        b["confirmed"]=False
        with self.assertRaises(ValueError):
            scan_structure([b])


if __name__=="__main__":
    unittest.main()
