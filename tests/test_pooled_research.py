import tempfile
import unittest
from pathlib import Path

import pandas as pd

from research.pooled_walk_forward import load_pooled

INSTRUMENTS=("BTC-USDT-SWAP","ETH-USDT-SWAP","SOL-USDT-SWAP")

class PooledResearchTests(unittest.TestCase):
    def write(self,root,rows):
        for symbol in INSTRUMENTS:
            path=Path(root)/symbol/"15m"/"impulse_no_bos"
            path.mkdir(parents=True)
            pd.DataFrame(rows).to_csv(path/"model_dataset.csv",index=False)

    def test_dedicated_asset_indicators_and_chronology(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp,[{"signal_ts":20,"exit_ts":40,"r_multiple":-0.1,
                            "target_win":0},
                            {"signal_ts":10,"exit_ts":30,"r_multiple":2,
                            "target_win":1}])
            d=load_pooled(tmp)
            self.assertEqual(len(d),6)
            self.assertTrue(d.signal_ts.is_monotonic_increasing)
            self.assertEqual(int(d.asset_btc.sum()),2)
            self.assertEqual(int(d.asset_eth.sum()),2)
            self.assertEqual(int(d.asset_sol.sum()),2)

    def test_reject_trade_exit_before_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp,[{"signal_ts":20,"exit_ts":10,"r_multiple":-1,
                            "target_win":0}])
            with self.assertRaisesRegex(ValueError,"before signal"):
                load_pooled(tmp)

if __name__=="__main__":
    unittest.main()
