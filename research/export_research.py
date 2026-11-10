"""Export historical research data from the public RFM Quant API.

Run: python -m research.export_research --symbol BTC-USDT-SWAP
No exchange credentials or live orders. Refuses gaps and truncated signals.
"""
import argparse
import json
from pathlib import Path
import httpx
import pandas as pd
from execution import simulate
from rfm_candidates import generate_candidates
from research.quant_pipeline import prepare_dataset,walk_forward
from history import INTERVAL_MS

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--base-url",default="https://rfm-quant.onrender.com")
    p.add_argument("--symbol",default="BTC-USDT-SWAP")
    p.add_argument("--bar",choices=["15m","1H","4H"],default="15m")
    p.add_argument("--bars",type=int,default=2000)
    p.add_argument("--output",default="research_outputs")
    a=p.parse_args()
    if not 100<=a.bars<=2000:p.error("--bars must be 100..2000")
    with httpx.Client(timeout=120) as client:
        r=client.get(a.base_url.rstrip("/")+"/api/okx/history",
                     params={"inst_id":a.symbol,"bar":a.bar,"bars":a.bars})
        r.raise_for_status()
        h=r.json()
    if h["missing_intervals"] or h["rejected"].get("malformed"):
        raise ValueError("historical gaps or malformed bars; backtest refused")
    candles=h["candles"]
    model=generate_candidates(candles,interval_ms=INTERVAL_MS[a.bar],max_signals=200)
    if model["truncated"]:
        raise ValueError("candidate list truncated; not a full-sample backtest")
    sim=simulate(candles,model["signals"],interval_ms=INTERVAL_MS[a.bar])
    out=Path(a.output)/a.symbol/a.bar
    out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(candles).to_csv(out/"candles.csv",index=False)
    event_cols=["signal_ts","known_after_close_ts","side","anchor_100_ts",
                "anchor_0_ts","zero_price","hundred_price","entry_level",
                "fvg_overlaps_gold_zone","fvg_count","broken_pivot_ts","notes"]
    trade_cols=["side","signal_ts","entry_ts","exit_ts","entry_price","exit_price",
                "stop_price","take_price","planned_rr","quantity","pnl","r_multiple",
                "equity_before","equity_after","exit_reason"]
    pd.DataFrame(model["events"],columns=event_cols).to_csv(out/"events.csv",index=False)
    pd.DataFrame(sim["trades"],columns=trade_cols).to_csv(out/"trades.csv",index=False)
    report={"instrument":a.symbol,"timeframe":a.bar,"bars":len(candles),
            "candidate_count":model["signal_count"],
            "execution_summary":sim["summary"],
            "status":"experimental_not_user_approved",
            "data_first_ts":h["first_ts"],"data_last_ts":h["last_ts"]}
    if sim["trades"]:
        data=prepare_dataset(pd.DataFrame(candles),pd.DataFrame(model["events"]),
                             pd.DataFrame(sim["trades"]))
        data.to_csv(out/"model_dataset.csv",index=False)
        report["walk_forward"]=walk_forward(data)
    else:
        report["walk_forward"]={"status":"insufficient_data","reason":"no closed trades"}
    (out/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(report,indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
