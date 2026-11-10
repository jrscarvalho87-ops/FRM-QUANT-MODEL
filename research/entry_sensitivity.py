"""Causal ENTRY-TOUCH sensitivity on saved candidate signals.

Compares predeclared Gold Zone prices (67%/75%) and limit-order expiries.
This is NOT an order-execution, win-rate, or profit backtest: touching a price
does not guarantee an exchange fill or a still-valid FVG/setup.
No future candle contributes to a signal; later bars test only its outcome.
"""
import argparse
import csv
import json
from pathlib import Path
from statistics import median


def touch_sensitivity(candles, signals, *, levels=(67,75), expiries=(8,32),
                      interval_ms=900000):
    if interval_ms<=0 or not all(0<x<=100 for x in levels) or not all(1<=x<=96 for x in expiries):
        raise ValueError("invalid sensitivity settings")
    bars=list(candles)
    timestamps=[int(b["ts"]) for b in bars]
    if timestamps != sorted(set(timestamps)):
        raise ValueError("candles must be sorted and unique")
    if any(b.get("confirmed") is not True for b in bars):
        raise ValueError("unconfirmed historical candle")
    if any(b-a!=interval_ms for a,b in zip(timestamps,timestamps[1:])):
        raise ValueError("history contains missing intervals")
    ix={t:k for k,t in enumerate(timestamps)}
    output=[]
    for level in levels:
        for expiry in expiries:
            fills=[]
            for s in signals:
                t=int(s["signal_ts"])
                if t not in ix:
                    raise ValueError("signal timestamp is outside supplied candles")
                side=s["side"]
                if side not in ("long","short"):
                    raise ValueError("invalid side")
                stop,take=float(s["stop"]),float(s["take"])
                if side=="long" and stop>=take or side=="short" and stop<=take:
                    raise ValueError("invalid Fib orientation")
                entry=take+(level/100)*(stop-take)
                at=ix[t]
                for j in range(at+1,min(len(bars),at+1+expiry)):
                    b=bars[j]
                    if (side=="long" and float(b["low"])<=entry) or (
                        side=="short" and float(b["high"])>=entry):
                        fills.append(j-at)
                        break
            n=len(signals)
            output.append({"entry_fib_percent":level,"expiry_bars":expiry,
                           "candidate_count":n,"touched":len(fills),
                           "untouched":n-len(fills),
                           "touch_rate_pct":round(100*len(fills)/n,2) if n else None,
                           "median_bars_until_touch":median(fills) if fills else None})
    return {"method":"price_touches_only_not_executed_trades",
            "warnings":[
                "Original candidate generator uses BOS as mandatory trigger, unlike the user's RFM.",
                "An order may lose validity before touching; these counts do not check subsequent FVG invalidation.",
                "No price/limit fill probability, fees, funding, PnL or independent holdout assessed.",
                "Changing entry level or expiry is hypothetical and not approval of a new strategy rule."
            ],
            "results":output}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--candles",required=True)
    p.add_argument("--signals",required=True)
    p.add_argument("--interval-ms",type=int,default=900000)
    p.add_argument("--output")
    a=p.parse_args()
    with open(a.candles,encoding="utf-8",newline="") as f:
        candles=list(csv.DictReader(f))
    for b in candles:
        b["confirmed"]=b["confirmed"].strip().lower() in ("true","1")
    with open(a.signals,encoding="utf-8",newline="") as f:
        signals=list(csv.DictReader(f))
    result=touch_sensitivity(candles,signals,interval_ms=a.interval_ms)
    value=json.dumps(result,ensure_ascii=False,indent=2)
    if a.output:
        Path(a.output).write_text(value,encoding="utf-8")
    print(value)


if __name__=="__main__":main()
