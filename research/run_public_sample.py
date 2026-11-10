"""Real OKX historical pilot: compare provisional BOS-free vs BOS-required models.

Saves complete chronological OHLCV, every generated signal and closed trade,
and +1R BE vs no-BE outcomes. It must never be described as verified user RFM.
No live orders or exchange credentials.
"""
import json
import traceback
from datetime import datetime,timezone
from pathlib import Path

import httpx
import pandas as pd
from research.export_research import fetch_candles,run_research

SAMPLES=[
    ("BTC-USDT-SWAP","15m",10000),
    ("ETH-USDT-SWAP","15m",10000),
    ("SOL-USDT-SWAP","15m",10000),
]
MODELS=["impulse_no_bos","breakout_bos"]
OUT=Path("research_outputs/public_sample")


def save_frame(path,rows):
    pd.DataFrame(rows).to_csv(path,index=False)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    index={"created_utc":datetime.now(timezone.utc).isoformat(),
           "status":"experimental_pivot_proxies_not_the_users_RFM",
           "models":MODELS,"samples":[]}
    with httpx.Client(timeout=120,follow_redirects=True) as client:
        for symbol,bar,count in SAMPLES:
            entry={"instrument":symbol,"bar":bar,"requested_bars":count,
                   "model_results":{}}
            try:
                candles,metadata=fetch_candles(
                    client,"https://rfm-quant.onrender.com",symbol,bar,count)
                if metadata["exhausted_before_target"]:
                    raise ValueError("Insufficient historical depth")
                folder=OUT/symbol/bar
                folder.mkdir(parents=True,exist_ok=True)
                save_frame(folder/"candles.csv",candles)
                entry["status"]="retrieved"
                entry["bars"]=len(candles)
                entry["first_ts"]=metadata["first_ts"]
                entry["last_ts"]=metadata["last_ts"]
                for model_name in MODELS:
                    try:
                        result=run_research(
                            candles,symbol,bar,entry_level=75,
                            liquidity_min_zones=0,metadata=metadata,
                            candidate_model=model_name)
                        sub=folder/model_name
                        sub.mkdir(parents=True,exist_ok=True)
                        save_frame(sub/"events.csv",result["model"]["events"])
                        save_frame(sub/"signals.csv",result["model"]["signals"])
                        save_frame(sub/"trades_with_be.csv",result["execution"]["trades"])
                        save_frame(sub/"trades_without_be.csv",
                                   result["without_break_even_execution"]["trades"])
                        result["dataset"].to_csv(sub/"model_dataset.csv",index=False)
                        (sub/"report.json").write_text(json.dumps(
                            result["report"],ensure_ascii=False,indent=2),encoding="utf-8")
                        m={"status":"evaluated","candidates":result["model"]["signal_count"],
                           "with_be":result["execution"]["summary"],
                           "without_be":result["without_break_even_execution"]["summary"],
                           "walk_forward_status":result["report"]["walk_forward"]["status"]}
                    except Exception as exc:
                        m={"status":"failed","error":type(exc).__name__+": "+str(exc)}
                        traceback.print_exc()
                    entry["model_results"][model_name]=m
                    print(json.dumps({"instrument":symbol,"model":model_name,
                                      **m},ensure_ascii=False),flush=True)
            except Exception as exc:
                entry.update({"status":"failed","error":type(exc).__name__+": "+str(exc)})
                traceback.print_exc()
            index["samples"].append(entry)
            print(json.dumps({"instrument":symbol,"status":entry["status"]},
                             ensure_ascii=False),flush=True)
    (OUT/"index.json").write_text(
        json.dumps(index,ensure_ascii=False,indent=2),encoding="utf-8")
    if not any(m.get("status")=="evaluated" for item in index["samples"]
               for m in item["model_results"].values()):
        raise RuntimeError("No historical model evaluated: do not invent statistics.")

if __name__=="__main__":
    main()
