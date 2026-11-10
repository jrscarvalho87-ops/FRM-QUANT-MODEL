"""Export reproducible REAL OKX historical data and experimental RFM proxies.

No exchange credentials or orders. Expands beyond the production API's
2,000-candle request cap using read-only, cursor-paginated candle pages.
Two candidate models are compared: a provisional pivot-impulse detector
WITHOUT mandatory BOS and a legacy pivot-breakout detector. Neither is a
validated reproduction of the user's discretionary RFM.

Run: python -m research.export_research --symbol BTC-USDT-SWAP --bar 15m --bars 10000
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd

from execution import simulate
from rfm_candidates import generate_candidates
from rfm_impulse_candidates import generate_impulse_candidates
from research.quant_pipeline import prepare_dataset, walk_forward
from history import INTERVAL_MS


def fetch_candles(client, base_url, instrument, bar, target):
    """Page backwards without filling gaps or pretending exhaustion is coverage."""
    if not 100 <= target <= 20000 or bar not in ("15m", "1H", "4H"):
        raise ValueError("Invalid research coverage")
    base = base_url.rstrip("/")
    response = client.get(base + "/api/okx/history", params={
        "inst_id":instrument, "bar":bar, "bars":min(2000,target)})
    response.raise_for_status()
    first = response.json()
    if first.get("missing_intervals") or first.get("rejected",{}).get("malformed"):
        raise ValueError("Initial historical page contains gaps or malformed candles")
    unique = {int(b["ts"]):b for b in first["candles"]}
    pages = int(first.get("pages_requested",0))
    exhausted = bool(first.get("history_exhausted",False))
    while len(unique) < target and unique and not exhausted:
        oldest = min(unique)
        response = client.get(base + "/api/okx/candles", params={
            "inst_id":instrument, "bar":bar, "limit":100, "after":oldest})
        response.raise_for_status()
        page = response.json()
        pages += 1
        if page.get("rejected",{}).get("malformed") or page.get("missing_intervals"):
            raise ValueError("An older historical page contains gaps/malformed candles")
        added = 0
        for candle in page.get("candles",[]):
            t = int(candle["ts"])
            if t < oldest and t not in unique:
                unique[t] = candle
                added += 1
        if added == 0 or added < 100:
            exhausted = True
    bars = [unique[t] for t in sorted(unique)[-target:]]
    if len(bars) < 100:
        raise ValueError("Not enough confirmed historical bars to run research")
    interval = INTERVAL_MS[bar]
    for n,b in enumerate(bars):
        if b.get("confirmed") is not True:
            raise ValueError("Unconfirmed bar in research sample")
        if n and int(b["ts"]) - int(bars[n-1]["ts"]) != interval:
            raise ValueError("Historical gap across pages; backtest refused")
    return bars, {"instrument":instrument, "timeframe":bar, "source":"OKX read-only candles",
                  "requested_bars":target, "returned_bars":len(bars),
                  "exhausted_before_target":len(bars)<target,
                  "pages_requested":pages,
                  "first_ts":int(bars[0]["ts"]), "last_ts":int(bars[-1]["ts"]),
                  "retrieved_utc":datetime.now(timezone.utc).isoformat()}


def run_research(candles, instrument, bar, entry_level=75,
                 liquidity_min_zones=0, metadata=None,
                 candidate_model="impulse_no_bos"):
    """Compare execution with vs without +1R break-even on identical signals.

    Mechanical candidates, not a validated or faithful user-RFM backtest.
    Both variants are simulated chronologically from the same input OHLCV.
    """
    if candidate_model not in ("impulse_no_bos","breakout_bos"):
        raise ValueError("candidate_model must be impulse_no_bos or breakout_bos")
    if candidate_model=="impulse_no_bos":
        if liquidity_min_zones:
            raise ValueError("no approved structural liquidity filter in impulse mode")
        model=generate_impulse_candidates(
            candles,interval_ms=INTERVAL_MS[bar],entry_level=entry_level,
            max_signals=5000)
    else:
        model=generate_candidates(
            candles,interval_ms=INTERVAL_MS[bar],entry_level=entry_level,
            require_fvg=True,liquidity_min_zone_count=liquidity_min_zones,
            max_signals=5000)
    if model["truncated"]:
        raise ValueError("Candidate list was truncated: refuse partial backtest")
    with_be=simulate(candles,model["signals"],interval_ms=INTERVAL_MS[bar],
                     move_stop_to_be_at_r=1.0)
    without_be=simulate(candles,model["signals"],interval_ms=INTERVAL_MS[bar],
                        move_stop_to_be_at_r=None)
    sb=with_be["summary"]
    sn=without_be["summary"]
    report={
        "instrument":instrument,"timeframe":bar,
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "data":metadata or {"bars":len(candles)},
        "candidate_model":candidate_model,
        "candidate_count":model["signal_count"],
        "execution_summary":sb,
        "without_break_even":sn,
        "break_even_comparison":{
            "with_be_closed":sb["closed_trades"],
            "without_be_closed":sn["closed_trades"],
            "be_stop_exits":sb["break_even_stop_exits"],
            "equity_delta_with_minus_without":round(
                sb["ending_equity"]-sn["ending_equity"],6),
            "net_return_pct_delta":round(
                sb["net_return_pct"]-sn["net_return_pct"],6),
            "warning":"Different trade lifetimes may change skipped overlapping signals; "
                      "this is a portfolio-simulation comparison, not paired trade causality."
        },
        "parameter_assumptions":{
            "entry_level":entry_level,"active_fvg_in_gold_zone_required":True,
            "liquidity_min_zones_experimental":liquidity_min_zones,
            "bos_required_by_proxy":candidate_model=="breakout_bos",
            "poc_is_optional_ohlcv_proxy":True,
            "be_trigger_r":1.0,"be_fill_rule":"next_candle_only_conservative",
            "fee_bps_per_side":5,"slippage_bps_per_side":2,
            "initial_equity":10000,"risk_pct":1,"max_exposure":1
        },
        "status":"exploratory_not_user_approved_or_out_of_sample",
        "limitations":[
            "Fibonacci pivot anchors and structural-liquidity relevance are provisional, not user-approved.",
            "No BOS filter in impulse_no_bos mode; a pivot-pair still must be confirmed.",
            "The structural liquidity proxy is recorded but not yet mandatory despite liquidity being essential in the RFM.",
            "Only completed trades have training labels: selection and survivorship bias remain.",
            "OHLC BE applies only from next bar after 1R; intrabar chronology unresolved.",
            "Fees/slippage assumed; funding, spread variability, impact and liquidation absent."
        ]
    }
    if with_be["trades"]:
        dataset=prepare_dataset(pd.DataFrame(candles),
                                pd.DataFrame(model["events"]),
                                pd.DataFrame(with_be["trades"]))
        report["walk_forward"]=walk_forward(dataset)
    else:
        dataset=pd.DataFrame()
        report["walk_forward"]={"status":"insufficient_data",
                                "reason":"no completed trades"}
    return {"model":model,"execution":with_be,
            "without_break_even_execution":without_be,
            "dataset":dataset,"report":report}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://rfm-quant.onrender.com")
    parser.add_argument("--symbol", default="BTC-USDT-SWAP")
    parser.add_argument("--bar", choices=["15m","1H","4H"], default="15m")
    parser.add_argument("--bars", type=int, default=10000)
    parser.add_argument("--entry-level", type=int, choices=[67,75], default=75)
    parser.add_argument("--liquidity-min-zones", type=int, default=0)
    parser.add_argument("--candidate-model",choices=["impulse_no_bos","breakout_bos"],default="impulse_no_bos")
    parser.add_argument("--output", default="research_outputs")
    a = parser.parse_args()
    if not 100<=a.bars<=20000:
        parser.error("--bars must be 100..20000")
    if not 0<=a.liquidity_min_zones<=50:
        parser.error("--liquidity-min-zones must be 0..50; experimental, not user-approved")
    with httpx.Client(timeout=120,follow_redirects=True) as client:
        candles, meta = fetch_candles(client,a.base_url,a.symbol,a.bar,a.bars)
    result = run_research(candles,a.symbol,a.bar,a.entry_level,a.liquidity_min_zones,meta,candidate_model=a.candidate_model)
    out = Path(a.output) / a.symbol / a.bar
    out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(candles).to_csv(out/"candles.csv",index=False)
    pd.DataFrame(result["model"]["events"]).to_csv(out/"events.csv",index=False)
    pd.DataFrame(result["model"]["signals"]).to_csv(out/"signals.csv",index=False)
    pd.DataFrame(result["execution"]["trades"]).to_csv(out/"trades.csv",index=False)
    pd.DataFrame(result["without_break_even_execution"]["trades"]).to_csv(out/"trades_without_be.csv",index=False)
    result["dataset"].to_csv(out/"model_dataset.csv",index=False)
    (out/"report.json").write_text(
        json.dumps(result["report"],ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result["report"],ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
