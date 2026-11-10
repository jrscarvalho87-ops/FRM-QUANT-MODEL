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
import hashlib
import httpx
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
    if df["ts"].duplicated().any() or not df["ts"].is_monotonic_increasing:
        raise ValueError("Archived candle timestamps must be unique and increasing")
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



# The fixed market window and checksums were calculated from the
# already archived, publicly sourced 2026-11-10 30k-candle snapshot.
PINNED_LAST_TS=1794342600000
PINNED_FIRST_TS=1785343500000
PINNED_BARS=10000
EXPECTED_SHA256={
    "BTC-USDT-SWAP":"d8d0a0dce22769664ee42ee6939523f07e390ea18fafea5fe5ff2680a14046f9",
    "ETH-USDT-SWAP":"644e2f69a533a817297fd04daff86a2c1cc0c21cf084a0bf788e08bbf8648c76",
    "SOL-USDT-SWAP":"6848722b2a9eca258cda2e57fc134ba4a5a7546a6e275bdcb212b9e5a3892062",
}
PREVIOUS_AUDITED={
    "BTC-USDT-SWAP":{"candidates":310,"invalid_anchors":19,"trades_be":80,
                     "return_pct_be":-10.4401},
    "ETH-USDT-SWAP":{"candidates":334,"invalid_anchors":33,"trades_be":82,
                     "return_pct_be":-6.0838},
    "SOL-USDT-SWAP":{"candidates":333,"invalid_anchors":32,"trades_be":90,
                     "return_pct_be":-11.1068},
}


def history_fingerprint(candles):
    """Canonical OHLCV fingerprint, not exchange authenticity certification."""
    cols=("open","high","low","close","volume_contracts")
    lines=(
        "|".join([str(int(row["ts"]))]+
                 [format(float(row[key]),".10g") for key in cols])
        for row in candles
    )
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def run_pinned_audit(base_url,output_dir):
    """Fetch exact archived UTC window from read-only public API, fail on drift."""
    from research.export_research import fetch_candles
    output_dir=Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    result={
        "status":"experimental_frozen_market_window",
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "reference_workflow":"https://github.com/jrscarvalho87-ops/FRM-QUANT-MODEL/actions/runs/42898175611",
        "pinned_first_ts":PINNED_FIRST_TS,"pinned_last_ts":PINNED_LAST_TS,
        "warnings":[
            "These are already examined past market prices, not a pristine chronological holdout.",
            "Fingerprint verifies identity with previously downloaded OHLCV; no claim of data/exchange authenticity.",
            "Geometric Fibonacci verification is necessary but does not reproduce the user's discretionary anchors.",
            "No structural liquidity relevance threshold is approved or required by this experimental generator.",
            "All trade results are synthetic backtest executions without funding or real order-book fills."
        ],"instruments":[]}
    with httpx.Client(timeout=120,follow_redirects=True) as client:
        for instrument in INSTRUMENTS:
            print(json.dumps({"instrument":instrument,
                              "phase":"fetch_frozen_historical_candles",
                              "expected_last_ts":PINNED_LAST_TS}),flush=True)
            candles,metadata=fetch_candles(
                client,base_url,instrument,"15m",PINNED_BARS,
                last_bar_ts=PINNED_LAST_TS)
            if (len(candles)!=PINNED_BARS or
                    int(candles[0]["ts"])!=PINNED_FIRST_TS or
                    int(candles[-1]["ts"])!=PINNED_LAST_TS):
                raise ValueError("Frozen historical window mismatch: refusing comparison")
            fingerprint=history_fingerprint(candles)
            if fingerprint!=EXPECTED_SHA256[instrument]:
                raise ValueError(
                    "Historical OHLCV fingerprint differs from archived snapshot "
                    "for "+instrument+"; refusing a misleading before/after comparison")
            rerun=run_research(
                candles,instrument,"15m",entry_level=75,
                metadata=metadata,candidate_model="impulse_no_bos")
            new=rerun["model"]
            times={int(b["ts"]):i for i,b in enumerate(candles)}
            new_audit=old_anchor_audit(candles,new["events"])
            if new["truncated"] or any(not a["anchors_valid"] for a in new_audit):
                raise AssertionError("New candidate list is truncated or contains invalid anchors")
            dest=output_dir/instrument
            dest.mkdir(parents=True,exist_ok=True)
            pd.DataFrame(new["events"]).to_csv(dest/"events.csv",index=False)
            pd.DataFrame(new["signals"]).to_csv(dest/"signals.csv",index=False)
            pd.DataFrame(rerun["execution"]["trades"]).to_csv(
                dest/"trades_with_BE_1R.csv",index=False)
            pd.DataFrame(rerun["without_break_even_execution"]["trades"]).to_csv(
                dest/"trades_without_BE.csv",index=False)
            rerun["dataset"].to_csv(dest/"model_dataset.csv",index=False)
            (dest/"report.json").write_text(
                json.dumps(rerun["report"],ensure_ascii=False,indent=2),
                encoding="utf-8")
            events=new["events"]
            context=[int(e["liquidity_unbreached_contextual_count"])
                     for e in events]
            independent_context=[
                int(e["liquidity_independent_unbreached_contextual_count"])
                for e in events]
            zero_context=sum(x==0 for x in context)
            zero_independent=sum(x==0 for x in independent_context)
            old=PREVIOUS_AUDITED[instrument]
            stats={
                "instrument":instrument,"status":"verified_same_ohlcv_history",
                "candle_count":len(candles),
                "sha256_ohlcv":fingerprint,
                "old_candidates":old["candidates"],
                "old_invalid_anchor_count":old["invalid_anchors"],
                "old_trades_with_be":old["trades_be"],
                "old_return_pct_be":old["return_pct_be"],
                "new_candidate_count":new["signal_count"],
                "new_rejected_invalid_anchor_count":new["rejected"]["invalid_fibonacci_anchor_extrema"],
                "new_invalid_anchors":0,
                "liquidity_context_zero_count":zero_context,
                "liquidity_context_observed_rate_pct":
                    round(100*(len(context)-zero_context)/len(context),2)
                    if context else None,
                "liquidity_independent_zero_count":zero_independent,
                "liquidity_independent_present_pct":
                    round(100*(len(independent_context)-zero_independent)/
                          len(independent_context),2)
                    if independent_context else None,
                "liquidity_independent_mean_count":
                    round(sum(independent_context)/len(independent_context),4)
                    if independent_context else None,
                "new_trades_with_be":rerun["execution"]["summary"]["closed_trades"],
                "new_return_pct_be":rerun["execution"]["summary"]["net_return_pct"],
                "new_trades_without_be":rerun["without_break_even_execution"]["summary"]["closed_trades"],
                "new_return_pct_without_be":rerun["without_break_even_execution"]["summary"]["net_return_pct"],
                "walk_forward_status":rerun["report"]["walk_forward"]["status"],
                "bootstrap_status":rerun["report"]["block_bootstrap"]["status"],
            }
            result["instruments"].append(stats)
            print(json.dumps(stats,ensure_ascii=False),flush=True)
    (output_dir/"summary.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",default="research_outputs/public_sample")
    parser.add_argument("--output",default="research_outputs/geometry_audit")
    parser.add_argument("--source",choices=("archived","pinned-api"),default="archived")
    parser.add_argument("--base-url",default="https://rfm-quant.onrender.com")
    args=parser.parse_args()
    if args.source=="pinned-api":
        run_pinned_audit(args.base_url,args.output)
    else:
        run_archived_audit(args.input,args.output)


if __name__=="__main__":
    main()
