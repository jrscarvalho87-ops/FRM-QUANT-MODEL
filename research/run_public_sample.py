"""One-shot publicly sourced OHLCV research snapshot for GitHub Actions.

This prints outcomes from REAL historical candles, not fabricated candles.
The mechanical BOS-triggered generator is NOT equivalent to the user's RFM.
No API keys, exchange account, orders, funding, or live trading.
"""
import json
import traceback
from datetime import datetime,timezone
from pathlib import Path

import httpx
import pandas as pd

from research.export_research import fetch_candles, run_research

SAMPLES=[
    ("BTC-USDT-SWAP","15m",4000),
    ("ETH-USDT-SWAP","15m",4000),
]
OUT=Path("research_outputs/public_sample")


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    index={"created_utc":datetime.now(timezone.utc).isoformat(),
           "status":"exploratory_proxy_not_true_RFM",
           "samples":[]}
    with httpx.Client(timeout=120,follow_redirects=True) as client:
        for symbol,bar,count in SAMPLES:
            entry={"instrument":symbol,"bar":bar,"requested_bars":count}
            try:
                candles,metadata=fetch_candles(client,"https://rfm-quant.onrender.com",symbol,bar,count)
                if metadata["exhausted_before_target"]:
                    raise ValueError("Insufficient historical depth for requested research window")
                result=run_research(candles,symbol,bar,entry_level=75,
                                    liquidity_min_zones=0,metadata=metadata)
                folder=OUT/symbol/bar
                folder.mkdir(parents=True,exist_ok=True)
                pd.DataFrame(candles).to_csv(folder/"candles.csv",index=False)
                pd.DataFrame(result["model"]["events"]).to_csv(folder/"events.csv",index=False)
                pd.DataFrame(result["model"]["signals"]).to_csv(folder/"signals.csv",index=False)
                pd.DataFrame(result["execution"]["trades"]).to_csv(folder/"trades.csv",index=False)
                result["dataset"].to_csv(folder/"model_dataset.csv",index=False)
                (folder/"report.json").write_text(
                    json.dumps(result["report"],ensure_ascii=False,indent=2),encoding="utf-8")
                entry.update({"status":"evaluated","first_ts":metadata["first_ts"],
                              "last_ts":metadata["last_ts"],
                              "bars":len(candles),
                              "candidate_count":result["model"]["signal_count"],
                              "execution_summary":result["execution"]["summary"],
                              "walk_forward_status":result["report"]["walk_forward"]["status"]})
            except Exception as exc:
                entry.update({"status":"failed","error":type(exc).__name__+": "+str(exc)})
                traceback.print_exc()
            index["samples"].append(entry)
            print(json.dumps(entry,ensure_ascii=False),flush=True)
    (OUT/"index.json").write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding="utf-8")
    if not any(e["status"]=="evaluated" for e in index["samples"]):
        raise RuntimeError("No historical sample was retrieved; results not invented.")


if __name__=="__main__":
    main()
