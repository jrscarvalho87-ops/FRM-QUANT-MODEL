import unittest
from rfm_candidates import generate_candidates
from execution import simulate


def candles(highs,lows,closes=None):
    if closes is None:
        closes=[(h+l)/2 for h,l in zip(highs,lows)]
    return [{"ts":(i+1)*900000,"open":str(c),"high":str(h),
             "low":str(l),"close":str(c),"confirmed":True}
            for i,(h,l,c) in enumerate(zip(highs,lows,closes))]


class CandidateTests(unittest.TestCase):
    def bullish(self):
        highs=[100,102,105,108,104,101,103,107,109,111,112]
        lows=[90,91,92,94,90,80,88,91,94,96,98]
        closes=[95,97,99,100,97,90,95,100,107,110,109]
        return candles(highs,lows,closes)

    def bearish(self):
        highs=[110,109,108,106,110,120,112,109,106,104,102]
        lows=[100,98,95,92,96,99,97,93,91,89,88]
        closes=[105,103,101,100,105,110,106,100,94,90,91]
        return candles(highs,lows,closes)

    def test_bullish_breakout_known_only_after_close(self):
        bars=self.bullish()
        result=generate_candidates(bars,pivot_span=2)
        self.assertGreaterEqual(result["signal_count"],1)
        event=next(e for e in result["events"] if e["side"]=="long")
        self.assertEqual(event["known_after_close_ts"],event["signal_ts"]+900000)
        self.assertEqual(event["hundred_price"],80)
        self.assertLessEqual(event["anchor_0_ts"],event["signal_ts"])

    def test_bearish_breakout(self):
        result=generate_candidates(self.bearish(),pivot_span=2)
        self.assertGreaterEqual(result["signal_count"],1)
        self.assertEqual(result["signals"][0]["side"],"short")
        self.assertGreater(result["signals"][0]["stop"],result["signals"][0]["entry"])
        self.assertLess(result["signals"][0]["take"],result["signals"][0]["entry"])

    def test_future_candles_do_not_change_existing_signal(self):
        bars=self.bullish()
        early=generate_candidates(bars[:-1],pivot_span=2)
        later=generate_candidates(bars,pivot_span=2)
        self.assertEqual(early["signals"],later["signals"][:len(early["signals"])])

    def test_fvg_is_optional(self):
        bars=self.bullish()
        baseline=generate_candidates(bars,pivot_span=2,require_fvg=False)
        strict=generate_candidates(bars,pivot_span=2,require_fvg=True)
        self.assertLessEqual(strict["signal_count"],baseline["signal_count"])

    def test_no_data_gap(self):
        bars=self.bullish()
        bars[4]["ts"]+=1
        with self.assertRaisesRegex(ValueError,"gaps"):
            generate_candidates(bars,pivot_span=2)

    def test_no_unconfirmed_bar(self):
        bars=self.bullish()
        bars[-1]["confirmed"]=False
        with self.assertRaisesRegex(ValueError,"Unconfirmed"):
            generate_candidates(bars,pivot_span=2)

    def test_no_lookahead_fill_at_signal_candle(self):
        bars=self.bullish()
        candidate=generate_candidates(bars,pivot_span=2)
        report=simulate(bars,candidate["signals"],interval_ms=900000)
        self.assertTrue(all(t["entry_ts"]>t["signal_ts"] for t in report["trades"]))

    def test_no_candles_no_claims(self):
        report=generate_candidates([])
        self.assertEqual(report["signal_count"],0)
        self.assertEqual(report["signals"],[])


if __name__=="__main__":
    unittest.main()
