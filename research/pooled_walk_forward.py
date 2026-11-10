"""Pooled, chronologically purged XGBoost / logistic / baseline diagnostics.

Reads ONLY labeled completed-trade datasets already exported from real data.
The pooled model is exploratory; trading outcomes across assets can be
correlated. An untouched later holdout is necessary before edge claims.

Run:
 python -m research.pooled_walk_forward --root research_outputs/public_sample
"""
import argparse
import json
from datetime import datetime,timezone
from pathlib import Path

import pandas as pd
from research.quant_pipeline import walk_forward

INSTRUMENTS=("BTC-USDT-SWAP","ETH-USDT-SWAP","SOL-USDT-SWAP")
ASSETS=("btc","eth","sol")


def load_pooled(root, model="impulse_no_bos"):
    if model not in ("impulse_no_bos","breakout_bos"):
        raise ValueError("unsupported candidate model")
    frames=[]
    for instrument in INSTRUMENTS:
        path=Path(root)/instrument/"15m"/model/"model_dataset.csv"
        data=pd.read_csv(path)
        if not {"signal_ts","exit_ts","r_multiple","target_win"}.issubset(data.columns):
            raise ValueError("missing time-safe labeled trade fields: "+str(path))
        if data.empty:
            continue
        data["instrument"]=instrument
        for asset in ASSETS:
            data["asset_"+asset]=int(instrument.startswith(asset.upper()+"-"))
        frames.append(data)
    if not frames:
        raise ValueError("no labeled completed trades; cannot evaluate ML")
    joined=pd.concat(frames,ignore_index=True)
    if (joined["exit_ts"]<joined["signal_ts"]).any():
        raise ValueError("exit occurs before signal")
    joined=joined.sort_values(["signal_ts","instrument"],kind="stable").reset_index(drop=True)
    return joined


def evaluate(root,model="impulse_no_bos",*,min_train=80,test_size=25,n_splits=4):
    data=load_pooled(root,model)
    result=walk_forward(data,min_train=min_train,test_size=test_size,n_splits=n_splits)
    return {
        "status":"exploratory_pooled_not_untouched_holdout",
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "candidate_model":model,"instruments":INSTRUMENTS,
        "completed_trades":len(data),
        "observed_mean_net_r":round(float(data.r_multiple.mean()),6),
        "walk_forward":result,
        "warnings":[
            "Each asset was already explored on this historical period; pooled folds are not a pristine final holdout.",
            "Training labels are purged if their exit occurs after the next fold begins.",
            "Multiple simultaneous crypto signals may be correlated; no multi-asset risk/capital engine is modeled.",
            "This is an experimental mechanical pivot setup, not the user's fully specified RFM.",
            "Brier probability calibration alone cannot prove strategy profitability."
        ]
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",default="research_outputs/public_sample")
    parser.add_argument("--candidate-model",choices=["impulse_no_bos","breakout_bos"],
                        default="impulse_no_bos")
    parser.add_argument("--output")
    a=parser.parse_args()
    result=evaluate(a.root,a.candidate_model)
    encoded=json.dumps(result,ensure_ascii=False,indent=2)
    if a.output:
        path=Path(a.output)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(encoded,encoding="utf-8")
    print(encoded)

if __name__=="__main__":
    main()
