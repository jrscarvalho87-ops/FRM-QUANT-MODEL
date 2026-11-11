"""Causal, descriptive range-vs-expansion context tests."""
import copy
import unittest

from market_structure_context import describe_structure_context


def bars():
    result=[]
    for i in range(82):
        price=100+(i%4-1.5)*.22
        o=price-0.1
        c=price+0.1
        h=max(o,c)+.3
        l=min(o,c)-.3
        if 51<=i<=58:
            price=100+2.0*(i-50)
            o=price-0.5
            c=price+0.4
            h=c+0.6
            l=o-0.6
        result.append({"ts":(i+1)*900000,"open":o,"high":h,
                       "low":l,"close":c,"volume_contracts":100,
                       "confirmed":True})
    return result


class StructureContextTests(unittest.TestCase):
    def calc(self,c):
        return describe_structure_context(c,hundred_index=50,
            zero_index=58,asof_index=61,pivot_span=2)

    def test_peak_expansion_compared_with_prior_atr(self):
        result=self.calc(bars())
        self.assertEqual(result["status"],"ok")
        self.assertEqual(result["pre_context_bars"],48)
        self.assertEqual(result["swing_candle_count"],9)
        self.assertGreater(result["swing_peak_tr_to_pre_atr"],3)
        self.assertGreater(result["swing_mean_tr_to_pre_atr"],1)
        self.assertGreaterEqual(result["swing_largest_bar_share"],0)
        self.assertLessEqual(result["swing_largest_bar_share"],1)

    def test_no_future_candle_may_affect_past(self):
        c=bars()
        before=self.calc(c[:62])
        changed=copy.deepcopy(c)
        for row in changed[62:]:
            row.update({"high":10000,"low":1,"open":20,
                        "close":20,"volume_contracts":1000000,
                        "confirmed":False})
        self.assertEqual(before,self.calc(changed))
        self.assertEqual(before,self.calc(changed[:62]))

    def test_weak_volume_is_measured_not_mandatory(self):
        b=bars()
        b[61]["volume_contracts"]=2
        d=self.calc(b)
        self.assertLess(d["signal_vs_previous_20_volume_ratio"],1.0)
        self.assertEqual(d["status"],"ok")

    def test_no_pre_history_returns_nullable_measures(self):
        d=describe_structure_context(bars(),hundred_index=4,
            zero_index=8,asof_index=11,pivot_span=2)
        self.assertEqual(d["status"],"prehistory_incomplete")
        self.assertIsNone(d["pre_range_to_atr"])
        self.assertIsNone(d["swing_peak_tr_to_pre_atr"])

    def test_unconfirmed_history_rejected(self):
        b=bars()
        b[55]["confirmed"]=False
        with self.assertRaisesRegex(ValueError,"confirmed"):
            self.calc(b)

    def test_future_anchor_and_invalid_price_rejected(self):
        b=bars()
        with self.assertRaisesRegex(ValueError,"invalid causal"):
            describe_structure_context(b,hundred_index=50,
                zero_index=64,asof_index=61)
        b[55]["low"]=-1
        with self.assertRaisesRegex(ValueError,"invalid historical"):
            self.calc(b)


if __name__=="__main__":
    unittest.main()
