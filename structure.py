"""Experimental BOS and FVG detector (NOT trading signals).

Pivots become known only after 'span' future candles have fully CLOSED.
An event's detected_at_ts always marks when it could first be known.
"""
from math import isfinite


def scan_structure(candles, pivot_span=3, min_fvg_fraction=0.0005, max_events=200):
    if not (2 <= pivot_span <= 10 and 0 <= min_fvg_fraction <= 0.1):
        raise ValueError("invalid detector configuration")
    bars=list(candles)
    if max_events < 1 or max_events > 2000:
        raise ValueError("invalid event limit")
    n=len(bars)
    if not n:
        return {"n_bars":0,"bos":[],"fvg":[],"pivots":[],"warning":"Experimental analysis, no entry signals."}
    ts=[int(c["ts"]) for c in bars]
    if ts!=sorted(set(ts)):
        raise ValueError("unsorted or duplicated timestamps")
    for c in bars:
        if c.get("confirmed") is not True:
            raise ValueError("unconfirmed candle")
    highs=[float(c["high"]) for c in bars]
    lows=[float(c["low"]) for c in bars]
    closes=[float(c["close"]) for c in bars]
    if not all(isfinite(x) and x>0 for x in highs+lows+closes):
        raise ValueError("invalid prices")
    pivots=[]
    bos=[]
    fvg=[]
    last_high=None
    last_low=None
    for i in range(n):
        j=i-pivot_span
        if j>=pivot_span:
            h=highs[j]
            l=lows[j]
            if all(h > highs[k] for k in range(j-pivot_span,j+pivot_span+1) if k!=j):
                last_high={"level":h,"pivot_ts":ts[j],"confirmed_at_ts":ts[i]}
                pivots.append({"kind":"pivot_high",**last_high})
            if all(l < lows[k] for k in range(j-pivot_span,j+pivot_span+1) if k!=j):
                last_low={"level":l,"pivot_ts":ts[j],"confirmed_at_ts":ts[i]}
                pivots.append({"kind":"pivot_low",**last_low})
        if i>=1 and last_high and ts[i]>last_high["confirmed_at_ts"]:
            level=last_high["level"]
            if closes[i]>level and closes[i-1]<=level:
                bos.append({"direction":"bullish","detected_at_ts":ts[i],
                            "broken_level":level,"swing_pivot_ts":last_high["pivot_ts"],
                            "swing_confirmed_ts":last_high["confirmed_at_ts"]})
        if i>=1 and last_low and ts[i]>last_low["confirmed_at_ts"]:
            level=last_low["level"]
            if closes[i]<level and closes[i-1]>=level:
                bos.append({"direction":"bearish","detected_at_ts":ts[i],
                            "broken_level":level,"swing_pivot_ts":last_low["pivot_ts"],
                            "swing_confirmed_ts":last_low["confirmed_at_ts"]})
        if i>=2:
            if lows[i]>highs[i-2]:
                gap=(lows[i]-highs[i-2])/closes[i]
                if gap>=min_fvg_fraction:
                    fvg.append({"direction":"bullish","detected_at_ts":ts[i],
                                "lower":highs[i-2],"upper":lows[i],"gap_fraction":round(gap,6)})
            if highs[i]<lows[i-2]:
                gap=(lows[i-2]-highs[i])/closes[i]
                if gap>=min_fvg_fraction:
                    fvg.append({"direction":"bearish","detected_at_ts":ts[i],
                                "lower":highs[i],"upper":lows[i-2],"gap_fraction":round(gap,6)})
    return {"n_bars":n,"pivot_span":pivot_span,
            "bos":bos[-max_events:],"fvg":fvg[-max_events:],
            "pivots":pivots[-max_events:],
            "counts":{"bos_bullish":sum(x["direction"]=="bullish" for x in bos),
                      "bos_bearish":sum(x["direction"]=="bearish" for x in bos),
                      "fvg_bullish":sum(x["direction"]=="bullish" for x in fvg),
                      "fvg_bearish":sum(x["direction"]=="bearish" for x in fvg)},
            "warning":"Experimental price-action event detection only. No auto-generated RFM trade signals or measured edge."}
