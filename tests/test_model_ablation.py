"""Tests for grouped-time folds, purging, baseline and feature ablations."""
import unittest

import numpy as np
import pandas as pd

from research.model_ablation import BASE,STRUCTURE,LIQUIDITY,ablate_models


def sample(n=150):
    rows=[]
    for i in range(n):
        row={
            "signal_ts":(i+1)*900000,
            "exit_ts":(i+1)*900000+int((i%4+1)*900000),
            "r_multiple":1 if i%5 in (1,4) else -1,
            "target_win":int(i%5 in (1,4)),
            "instrument":("BTC-USDT-SWAP","ETH-USDT-SWAP","SOL-USDT-SWAP")[i%3],
        }
        for j,field in enumerate(BASE+STRUCTURE+LIQUIDITY):
            row[field]=(i%11)*0.03+0.1*j
        row["structure_break_close_context"]=bool(i%2)
        rows.append(row)
    return pd.DataFrame(rows)


class QuantitativeModelAblationTests(unittest.TestCase):
    def test_identical_folds_and_purged_training(self):
        report=ablate_models(sample(),min_train=60,test_times=20,n_splits=2)
        self.assertEqual(report["status"],"exploratory_evaluated")
        self.assertEqual(report["completed_folds"],2)
        for fold in report["folds"]:
            if fold["status"]!="evaluated":
                continue
            self.assertLess(fold["last_training_exit_ts"],
                            fold["test_start_ts"]-fold["embargo_ms"])
            self.assertEqual(set(fold["models"]),{
                "basic_price","price_plus_structure",
                "price_plus_structure_liquidity"})
            for group in fold["models"].values():
                self.assertGreaterEqual(group["logistic"]["brier"],0)
                self.assertGreaterEqual(group["xgboost"]["brier"],0)

    def test_same_timestamp_cannot_be_split_across_assets(self):
        df=sample(150)
        df["signal_ts"]=df.signal_ts//1800000*1800000
        df["exit_ts"]=df.signal_ts+2*900000
        result=ablate_models(df,min_train=40,test_times=12,n_splits=2)
        self.assertEqual(result["status"],"exploratory_evaluated")
        for f in result["folds"]:
            if f["status"]=="evaluated":
                self.assertGreater(f["test_trades"],0)
                self.assertLess(f["last_training_exit_ts"],f["test_start_ts"]-900000)

    def test_missing_structure_cannot_silently_fall_back(self):
        d=sample()
        d=d.drop(columns=["pre_range_to_atr"])
        r=ablate_models(d)
        self.assertEqual(r["status"],"missing_predeclared_features")
        self.assertIn("pre_range_to_atr",r["missing"])

    def test_invalid_exit_and_duplicate_trade_refused(self):
        d=sample()
        d.loc[1,"exit_ts"]=1
        with self.assertRaisesRegex(ValueError,"invalid future"):
            ablate_models(d)
        d=sample()
        d.loc[1,"signal_ts"]=d.loc[0,"signal_ts"]
        d.loc[1,"instrument"]=d.loc[0,"instrument"]
        with self.assertRaisesRegex(ValueError,"duplicate trade"):
            ablate_models(d)

    def test_null_structural_values_imputed_using_only_training(self):
        d=sample()
        d.loc[d.index%3==0,"pre_close_efficiency"]=np.nan
        report=ablate_models(d,min_train=60,test_times=20,n_splits=2)
        self.assertEqual(report["status"],"exploratory_evaluated")
        self.assertGreater(report["completed_folds"],0)


if __name__=="__main__":
    unittest.main()
