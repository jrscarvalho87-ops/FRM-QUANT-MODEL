"""Export reproducible REAL OKX historical data and experimental RFM proxies.

No exchange credentials or orders. Expands beyond the production API's
2,000-candle request cap using read-only, cursor-paginated candle pages.
The candidate generator still requires a pivot breakout, unlike the user's
RFM, so reported outcomes must NEVER be labeled validated RFM performance.

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
                 liquidity_min_zones=0, metadata=None):
    """Analyze an experimental BOS-based RFM proxy, not the user's exact method."""
    model = generate_candidates(candles, interval_ms=INTERVAL_MS[bar],
                                entry_level=entry_level, require_fvg=True,
                                liquidity_min_zone_count=liquidity_min_zones,
                                max_signals=5000)
    if model["truncated"]:
        raise ValueError("Candidate list was truncated: refuse partial backtest")
    sim = simulate(candles, model["signals"], interval_ms=INTERVAL_MS[bar])
    report = {
        "instrument":instrument,"timeframe":bar,
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "data":metadata or {"bars":len(candles)},
        "candidate_count":model["signal_count"],
        "execution_summary":sim["summary"],
        "parameter_assumptions":{
            "entry_level":entry_level,
            "active_fvg_in_gold_zone_required":True,
            "liquidity_min_zones_experimental":liquidity_min_zones,
            "bos_required_by_proxy":True,
            "poc_is_optional_ohlcv_proxy":True
        },
        "status":"exploratory_not_user_approved_or_out_of_sample",
        "limitations":[
            "BOS is REQUIRED by this provisional signal generator but optional in the user's RFM.",
            "Fibonacci swing anchors and structural-liquidity thresholds have not been approved.",
            "Selected completed trades may exclude unfilled candidates and introduce sample bias.",
            "Costs are assumed; funding, spread variability, liquidation and market impact are absent."
        ]
    }
    if sim["trades"]:
        dataset = prepare_dataset(pd.DataFrame(candles),
                                  pd.DataFrame(model["events"]),
                                  pd.DataFrame(sim["trades"]))
        report["walk_forward"] = walk_forward(dataset)
    else:
        dataset = pd.DataFrame()
        report["walk_forward"] = {"status":"insufficient_data","reason":"no completed trades"}
    return {"model":model,"execution":sim,"dataset":dataset,"report":report}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://rfm-quant.onrender.com")
    parser.add_argument("--symbol", default="BTC-USDT-SWAP")
    parser.add_argument("--bar", choices=["15m","1H","4H"], default="15m")
    parser.add_argument("--bars", type=int, default=10000)
    parser.add_argument("--entry-level", type=int, choices=[67,75], default=75)
    parser.add_argument("--liquidity-min-zones", type=int, default=0)
    parser.add_argument("--output", default="research_outputs")
    a = parser.parse_args()
    if not 100<=a.bars<=20000:
        parser.error("--bars must be 100..20000")
    if not 0<=a.liquidity_min_zones<=50:
        parser.error("--liquidity-min-zones must be 0..50; experimental, not user-approved")
    with httpx.Client(timeout=120,follow_redirects=True) as client:
        candles, meta = fetch_candles(client,a.base_url,a.symbol,a.bar,a.bars)
    result = run_research(candles,a.symbol,a.bar,a.entry_level,a.liquidity_min_zones,meta)
    out = Path(a.output) / a.symbol / a.bar
    out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(candles).to_csv(out/"candles.csv",index=False)
    pd.DataFrame(result["model"]["events"]).to_csv(out/"events.csv",index=False)
    pd.DataFrame(result["model"]["signals"]).to_csv(out/"signals.csv",index=False)
    pd.DataFrame(result["execution"]["trades"]).to_csv(out/"trades.csv",index=False)
    result["dataset"].to_csv(out/"model_dataset.csv",index=False)
    (out/"report.json").write_text(
        json.dumps(result["report"],ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result["report"],ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
