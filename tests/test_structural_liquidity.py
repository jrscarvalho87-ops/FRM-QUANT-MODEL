import copy
import unittest
from structural_liquidity import structural_liquidity

MS=900000

class StructuralLiquidityTests(unittest.TestCase):
    def bars(self,n=300,start=0):
        import math
        out=[]
        for i in range(n):
            c=100+2*math.sin(i*0.27)+0.005*i
            out.append({"ts":start+i*MS,"open":c,"high":c+0.3,
                        "low":c-0.3,"close":c,"confirmed":True})
        return out

    def test_future_candle_changes_do_not_affect_features(self):
        bars=self.bars()
        before=structural_liquidity(bars,180)
        mutated=copy.deepcopy(bars)
        for k in range(181,len(mutated)):
            mutated[k]["high"]+=100000
            mutated[k]["low"]=0.01
            mutated[k]["confirmed"]=False
        after=structural_liquidity(mutated,180)
        self.assertEqual(before,after)
        self.assertGreater(before["bsl_count"],0)
        self.assertGreater(before["ssl_count"],0)

    def test_preceding_day_only_if_complete(self):
        bars=self.bars(210)
        a=structural_liquidity(bars,100)
        self.assertTrue(a["previous_day_available"])
        self.assertTrue(any(z["type"]=="PDH" for z in a["zones"]))
        short=bars[4:]
        b=structural_liquidity(short,96)
        self.assertFalse(b["previous_day_available"])

    def test_reject_gap_or_unconfirmed_prefix(self):
        bars=self.bars()
        bars[50]["ts"]+=100
        with self.assertRaisesRegex(ValueError,"gap"):
            structural_liquidity(bars,90)
        bars=self.bars()
        bars[60]["confirmed"]=False
        with self.assertRaisesRegex(ValueError,"unconfirmed"):
            structural_liquidity(bars,90)

    def test_no_forward_pivot_confirmation(self):
        bars=self.bars(60)
        a=structural_liquidity(bars,40,pivot_span=3)
        self.assertTrue(all(z["known_after_close_ts"]<=bars[40]["ts"]+MS
                            for z in a["zones"]))

    def test_unbreached_zone_flags_are_causal_and_bounded(self):
        bars=self.bars()
        a=structural_liquidity(bars,200,pivot_span=3)
        self.assertGreaterEqual(a["unbreached_zone_count"],0)
        self.assertLessEqual(a["unbreached_zone_count"],a["zone_count"])
        self.assertTrue(all(isinstance(z["breached_after_confirmation"],bool)
                            for z in a["zones"]))
        # A later spike cannot change whether a level was breached at 200.
        other=copy.deepcopy(bars)
        other[201]["high"]=1e9
        other[201]["low"]=1e-9
        self.assertEqual(a,structural_liquidity(other,200,pivot_span=3))

    def test_warmup(self):
        r=structural_liquidity(self.bars(6),5)
        self.assertEqual(r["status"],"warmup")

if __name__=="__main__":unittest.main()
