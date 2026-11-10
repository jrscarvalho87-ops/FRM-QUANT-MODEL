import unittest
import numpy as np
import pandas as pd
from research.quant_pipeline import prepare_dataset,walk_forward

class QuantResearchTests(unittest.TestCase):
    def sample(self,n=300):
        ts=np.arange(n,dtype=np.int64)*900000
        close=100+np.arange(n)*.03+np.sin(np.arange(n)/3)
        candles=pd.DataFrame({"ts":ts,"open":close,"high":close+1,
            "low":close-1,"close":close,"volume_contracts":100+np.arange(n)%10,
            "confirmed":True})
        ids=ts[20::2]
        events=pd.DataFrame({"signal_ts":ids,"side":["long"]*len(ids),
            "zero_price":[105]*len(ids),"hundred_price":[95]*len(ids),
            "entry_level":[75]*len(ids),"fvg_overlaps_gold_zone":[True]*len(ids)})
        trades=pd.DataFrame({"signal_ts":ids,"exit_ts":ids+900000,
            "r_multiple":np.where(np.arange(len(ids))%3==0,-1,2)})
        return candles,events,trades

    def test_no_future_feature_leak(self):
        c,e,t=self.sample()
        full=prepare_dataset(c,e,t)
        short=prepare_dataset(c.iloc[:100],e[e.signal_ts<c.ts.iloc[100]],
                              t[t.signal_ts<c.ts.iloc[100]])
        cols=["signal_ts","range_pct_12","return_12","volume_ratio_12"]
        pd.testing.assert_frame_equal(
            full[cols].iloc[:len(short)].reset_index(drop=True),
            short[cols].reset_index(drop=True))

    def test_walk_forward_runs_with_purged_training(self):
        d=prepare_dataset(*self.sample())
        result=walk_forward(d,min_train=40,test_size=20,n_splits=3)
        self.assertEqual(result["status"],"evaluated")
        self.assertTrue(all(f["status"]=="evaluated" for f in result["folds"]))

    def test_insufficient_sample(self):
        d=prepare_dataset(*self.sample(70))
        self.assertEqual(walk_forward(d)["status"],"insufficient_data")

    def test_reject_unconfirmed(self):
        c,e,t=self.sample()
        c.loc[0,"confirmed"]=False
        with self.assertRaisesRegex(ValueError,"unconfirmed"):
            prepare_dataset(c,e,t)

if __name__=="__main__":
    unittest.main()
