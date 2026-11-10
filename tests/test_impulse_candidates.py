"""Causality and entry-gate checks for pivot-impulse model without BOS."""
import copy
import unittest

from rfm_impulse_candidates import generate_impulse_candidates
from execution import simulate

MS = 900000

def sample():
    ranges=[
        (110,108), (109,107), (108,105), (106,102),
        (104,100), (104,102), (108,105), (112,107),
        (116,110), (119,114), (120,116), (118,115),
        (117,114), (115,104), (116,108),
    ]
    return [{"ts":(i+1)*MS, "open":(h+l)/2,
             "high":h,"low":l,"close":(h+l)/2,
             "volume_contracts":50+i,"confirmed":True}
            for i,(h,l) in enumerate(ranges)]

class ImpulseCandidateTests(unittest.TestCase):
    def test_long_fvg_signal_without_bos(self):
        b=sample()
        result=generate_impulse_candidates(b,pivot_span=2)
        self.assertGreaterEqual(result["signal_count"],1)
        e=next(x for x in result["events"] if x["side"]=="long")
        self.assertEqual(e["signal_ts"],b[12]["ts"])
        self.assertFalse(e["structure_break_close_context"])
        self.assertTrue(e["fvg_overlaps_gold_zone"])
        self.assertEqual(e["hundred_price"],100)
        self.assertEqual(e["zero_price"],120)
        self.assertEqual(result["settings"]["bos_required"],False)
        self.assertLess(e["anchor_0_ts"],e["signal_ts"])

    def test_short_mirror_without_bos(self):
        b=sample()
        for row in b:
            h,l,o,c=row["high"],row["low"],row["open"],row["close"]
            row.update({"high":220-l,"low":220-h,
                        "open":220-o,"close":220-c})
        result=generate_impulse_candidates(b,pivot_span=2)
        self.assertGreaterEqual(result["signal_count"],1)
        e=next(x for x in result["events"] if x["side"]=="short")
        self.assertFalse(e["structure_break_close_context"])
        self.assertTrue(e["fvg_overlaps_gold_zone"])

    def test_causality_future_modifications_not_in_past(self):
        b=sample()
        initial=generate_impulse_candidates(b[:13],pivot_span=2)
        self.assertGreaterEqual(initial["signal_count"],1)
        corrupted=copy.deepcopy(b)
        corrupted[13]["high"]=100000
        corrupted[13]["low"]=0.1
        corrupted[13]["open"]=100
        corrupted[13]["close"]=100
        corrupted[14]["confirmed"]=False
        after=generate_impulse_candidates(corrupted[:13],pivot_span=2)
        self.assertEqual(initial["signals"],after["signals"])
        self.assertEqual(initial["events"],after["events"])

    def test_pivot_needs_right_window_to_confirm(self):
        b=sample()
        self.assertEqual(generate_impulse_candidates(b[:12],pivot_span=2)["signal_count"],0)
        self.assertGreaterEqual(generate_impulse_candidates(b[:13],pivot_span=2)["signal_count"],1)

    def test_previous_gold_touch_cannot_be_retroactive_trade(self):
        b=sample()
        b[11].update({"open":114,"high":118,"low":105,"close":115})
        result=generate_impulse_candidates(b[:13],pivot_span=2)
        self.assertEqual(result["signal_count"],0)
        self.assertGreater(result["rejected"]["gold_zone_already_touched"],0)

    def test_time_of_first_execution_is_after_signal(self):
        b=sample()
        r=generate_impulse_candidates(b,pivot_span=2)
        trades=simulate(b,r["signals"],interval_ms=MS)
        self.assertTrue(all(t["entry_ts"]>t["signal_ts"] for t in trades["trades"]))

    def test_gap_and_unconfirmed_are_rejected(self):
        b=sample()
        b[6]["ts"]+=1
        with self.assertRaisesRegex(ValueError,"gaps"):
            generate_impulse_candidates(b,pivot_span=2)
        b=sample()
        b[-1]["confirmed"]=False
        with self.assertRaisesRegex(ValueError,"confirmed"):
            generate_impulse_candidates(b,pivot_span=2)

if __name__=="__main__":
    unittest.main()
