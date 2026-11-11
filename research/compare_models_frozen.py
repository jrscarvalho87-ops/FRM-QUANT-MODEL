"""Run frozen, same-fold model comparisons on three experimental crypto assets.

Consumes existing corrected-geometry executed trade datasets; no market API,
new strategy gates, return-based optimizations or user annotation leakage.
"""
import argparse
import json
from pathlib import Path

import pandas as pd

from research.model_ablation import ablate_models

INSTRUMENTS=("BTC-USDT-SWAP","ETH-USDT-SWAP","SOL-USDT-SWAP")


def evaluate_frozen_models(root):
    root=Path(root)
    parts=[]
    for instrument in INSTRUMENTS:
        path=root/instrument/"model_dataset.csv"
        if not path.is_file():
            raise ValueError("missing frozen trade dataset: "+str(path))
        frame=pd.read_csv(path)
        if frame.empty:
            continue
        frame["instrument"]=instrument
        if frame.duplicated(subset=["signal_ts"]).any():
            raise ValueError("ambiguous same-instrument trade timestamps")
        parts.append(frame)
    if not parts:
        raise ValueError("no historical completed trades")
    all_trades=pd.concat(parts,ignore_index=True)
    report=ablate_models(all_trades,embargo_ms=900000,
                         min_train=80,test_times=25,n_splits=4)
    return {
        "dataset_status":"real_ohlcv_existing_30k_previously_explored",
        "instruments":list(INSTRUMENTS),
        "historical_trade_count":int(len(all_trades)),
        "human_reviewed_setups_used_as_labels":0,
        "market_window_status":"already_explored_no_untouched_holdout",
        "model_evaluation":report,
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",default="research_outputs/geometry_audit")
    parser.add_argument("--output",default="research_outputs/geometry_audit/model_ablation.json")
    args=parser.parse_args()
    report=evaluate_frozen_models(args.root)
    path=Path(args.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),
                    encoding="utf-8")
    print(json.dumps({
        "phase":"quantitative_model_ablation",
        "historical_trade_count":report["historical_trade_count"],
        "status":report["model_evaluation"]["status"],
        "completed_folds":report["model_evaluation"].get("completed_folds"),
        "constant_baseline":report["model_evaluation"].get("constant_baseline_mean"),
        "model_means":report["model_evaluation"].get("model_means")
    },ensure_ascii=False),flush=True)


if __name__=="__main__":
    main()
