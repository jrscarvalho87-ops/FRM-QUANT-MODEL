"""Re-audit archived REAL OKX candles after fixing Fibonacci anchor geometry.

No fresh API calls: reads the immutable historic GitHub Actions snapshot
downloaded by .github/workflows/geometry-audit.yml. Not an independent holdout.
Compares legacy candidates with verified in-swing extremes and replays the
updated BOS-free, active-FVG, +1R BE research proxy.

Run: python -m research.audit_geometry_snapshot \
  --input research_outputs/public_sample --output research_outputs/geometry_audit
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from swing_geometry import audit_swing_geometry
from research.export_research import run_research

INSTRUMENTS=("BTC-USDT-SWAP","ETH-USDT-SWAP","SOL-USDT-SWAP")


def old_anchor_audit(candles, old_events):
    times={int(b["ts"]):i for i,b in enumerate(candles)}
    rows=[]
    for e in old_events:
        signal=int(e["signal_ts"])
        hundred=int(e["anchor_100_ts"])
        zero=int(e["anchor_0_ts"])
        if any(t not in times for t in (hundred,zero,signal)):
            raise ValueError("Archived event refers to a missing candle")
        report=audit_swing_geometry(
            candles,hundred_index=times[hundred],
            zero_index=times[zero],asof_index=times[signal],
            side=str(e["side"]))
        rows.append({
            "signal_ts":signal,"side":e["side"],
            "anchor_100_ts":hundred,"anchor_0_ts":zero,
            "anchors_valid":report["anchors_valid"],
            "stop_extreme_valid":report["stop_extreme_valid"],
            "target_extreme_valid":report["target_extreme_valid"],
            "swing_duration_bars":report["swing_duration_bars"],
            "true_stop_extreme":report["true_stop_extreme_within_span"],
            "true_target_extreme":report["true_target_extreme_within_span"]
        })
    return rows


def _load_candles(filename):
    df=pd.read_csv(filename)
    if "confirmed" not in df:
        raise ValueError("missing confirmed metadata")
    values=df["confirmed"].astype(str).str.strip().str.lower()
    if not values.isin(["true","false","1","0"]).all():
        raise ValueError("invalid confirmed metadata")
    df["confirmed"]=values.isin(["true","1"])
    candles=df.to_dict(orient="records")
    if not candles or not all(b["confirmed"] is True for b in candles):
        raise ValueError("unconfirmed archival candle")
    return candles


def run_archived_audit(source_dir,output_dir):
    source_dir=Path(source_dir)
    output_dir=Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    results={"status":"experimental_historical_geometry_audit",
             "generated_utc":datetime.now(timezone.utc).isoformat(),
             "source":"archived public OKX confirmed candles",
             "source_workflow":"https://github.com/jrscarvalho87-ops/FRM-QUANT-MODEL/actions/runs/42898175611",
             "instruments":[],
             "warnings":[
                 "This is a historical rerun of an already inspected time period, not a fresh out-of-sample test.",
                 "A geometrically correct swing does not confirm the user's discretionary Fibonacci anchor choice.",
                 "Liquidity structural relevance remains a hypothesis feature, not yet an accepted entry filter.",
                 "The provisional RFM still does not reproduce the complete strategy or prove an edge."
             ]}
    for instrument in INSTRUMENTS:
        root=source_dir/instrument/"15m"
        candles=_load_candles(root/"candles.csv")
        old=pd.read_csv(root/"impulse_no_bos"/"events.csv")
        old_rows=old.to_dict(orient="records")
        audited=old_anchor_audit(candles,old_rows)
        invalid=[r for r in audited if not r["anchors_valid"]]
        saved_path=root/"impulse_no_bos"/"report.json"
        old_report=json.loads(saved_path.read_text(encoding="utf-8"))
        reevaluated=run_research(
            candles,instrument,"15m",entry_level=75,
            liquidity_min_zones=0,
            metadata={"bars":len(candles),"origin":"archived_public_snapshot"},
            candidate_model="impulse_no_bos")
        candidate=reevaluated["model"]
        fresh_events=candidate["events"]
        # Refuse all non-geometrical signals from the fixed generator.
        new_audit=old_anchor_audit(candles,fresh_events)
        if any(not r["anchors_valid"] for r in new_audit):
            raise AssertionError("New generator emitted invalid Fibonacci anchors")
        if candidate["truncated"]:
            raise AssertionError("Truncated signals in audited sample")
        dest=output_dir/instrument
        dest.mkdir(parents=True,exist_ok=True)
        pd.DataFrame(audited).to_csv(dest/"previous_anchor_audit.csv",index=False)
        pd.DataFrame(fresh_events).to_csv(dest/"new_events.csv",index=False)
        pd.DataFrame(candidate["signals"]).to_csv(dest/"new_signals.csv",index=False)
        pd.DataFrame(reevaluated["execution"]["trades"]).to_csv(
            dest/"new_trades_be_1R.csv",index=False)
        pd.DataFrame(reevaluated["without_break_even_execution"]["trades"]).to_csv(
            dest/"new_trades_without_be.csv",index=False)
        reevaluated["dataset"].to_csv(dest/"new_model_dataset.csv",index=False)
        (dest/"new_report.json").write_text(
            json.dumps(reevaluated["report"],ensure_ascii=False,indent=2),
            encoding="utf-8")
        s={
            "instrument":instrument,"candle_count":len(candles),
            "prior_generated_candidates":len(old_rows),
            "prior_invalid_anchor_count":len(invalid),
            "prior_invalid_anchor_pct":round(
                100*len(invalid)/len(old_rows),3) if old_rows else None,
            "new_candidates":candidate["signal_count"],
            "rejected_invalid_anchor_candidates":candidate["rejected"]["invalid_fibonacci_anchor_extrema"],
            "new_anchors_invalid":sum(not r["anchors_valid"] for r in new_audit),
            "prior_with_be":old_report["execution_summary"],
            "new_with_be":reevaluated["execution"]["summary"],
            "new_without_be":reevaluated["without_break_even_execution"]["summary"],
            "new_walk_forward_status":reevaluated["report"]["walk_forward"]["status"],
        }
        results["instruments"].append(s)
        print(json.dumps(s,ensure_ascii=False),flush=True)
    (output_dir/"summary.json").write_text(
        json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
    return results


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",default="research_outputs/public_sample")
    parser.add_argument("--output",default="research_outputs/geometry_audit")
    args=parser.parse_args()
    run_archived_audit(args.input,args.output)


if __name__=="__main__":
    main()
