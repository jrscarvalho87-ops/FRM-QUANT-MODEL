"""Experimental BOS, FVG, liquidity sweep and CHoCH-candidate detector.

Pivots become known only after 'span' future candles have fully CLOSED.
OKX timestamps mark the OPEN of each candle. known_after_close_ts marks the
first possible availability of an event at candle close.
"""
from math import isfinite


def scan_structure(candles, pivot_span=3, min_fvg_fraction=0.0005, max_events=200, interval_ms=900_000):
    if not (2 <= pivot_span <= 10 and 0 <= min_fvg_fraction <= 0.1 and interval_ms > 0):
        raise ValueError("invalid detector configuration")
    bars=list(candles)
    if max_events < 1 or max_events > 2000:
        raise ValueError("invalid event limit")
    n=len(bars)
    if not n:
        return {"n_bars":0,"bos":[],"fvg":[],"pivots":[],"sweeps":[],"choch_candidates":[],"counts":{},"warning":"Experimental analysis, no entry signals."}
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
                last_high={"level":h,"pivot_ts":ts[j],"confirmed_at_ts":ts[i], "confirmed_at_close_ts":ts[i] + interval_ms}
                pivots.append({"kind":"pivot_high",**last_high})
            if all(l < lows[k] for k in range(j-pivot_span,j+pivot_span+1) if k!=j):
                last_low={"level":l,"pivot_ts":ts[j],"confirmed_at_ts":ts[i], "confirmed_at_close_ts":ts[i] + interval_ms}
                pivots.append({"kind":"pivot_low",**last_low})
        if i>=1 and last_high and ts[i]>last_high["confirmed_at_ts"]:
            level=last_high["level"]
            if closes[i]>level and closes[i-1]<=level:
                bos.append({"direction":"bullish","detected_at_ts":ts[i], "known_after_close_ts":ts[i] + interval_ms,
                            "broken_level":level,"swing_pivot_ts":last_high["pivot_ts"],
                            "swing_confirmed_ts":last_high["confirmed_at_ts"]})
        if i>=1 and last_low and ts[i]>last_low["confirmed_at_ts"]:
            level=last_low["level"]
            if closes[i]<level and closes[i-1]>=level:
                bos.append({"direction":"bearish","detected_at_ts":ts[i], "known_after_close_ts":ts[i] + interval_ms,
                            "broken_level":level,"swing_pivot_ts":last_low["pivot_ts"],
                            "swing_confirmed_ts":last_low["confirmed_at_ts"]})
        if i>=2:
            if lows[i]>highs[i-2]:
                gap=(lows[i]-highs[i-2])/closes[i]
                if gap>=min_fvg_fraction:
                    fvg.append({"direction":"bullish","detected_at_ts":ts[i], "known_after_close_ts":ts[i] + interval_ms,
                                "lower":highs[i-2],"upper":lows[i],"gap_fraction":round(gap,6)})
            if highs[i]<lows[i-2]:
                gap=(lows[i-2]-highs[i])/closes[i]
                if gap>=min_fvg_fraction:
                    fvg.append({"direction":"bearish","detected_at_ts":ts[i], "known_after_close_ts":ts[i] + interval_ms,
                                "lower":highs[i],"upper":lows[i-2],"gap_fraction":round(gap,6)})
    # A CHoCH candidate is an opposite-direction confirmed break after a
    # previously observed BOS. This is a heuristic, not certified market trend.
    choch_candidates=[]
    previous_break_direction=None
    for event in sorted(bos,key=lambda e:e["detected_at_ts"]):
        if previous_break_direction is not None and event["direction"] != previous_break_direction:
            choch_candidates.append({**event,"classification":"choch_candidate",
                                     "previous_break_direction":previous_break_direction})
        previous_break_direction=event["direction"]

    # Wick through a previously CONFIRMED pivot followed by a close back
    # inside its level. One sweep maximum per pivot, so the same swing
    # cannot be inflated into repeated opportunities.
    sweeps=[]
    active_high=None
    active_low=None
    pivot_events=sorted(pivots,key=lambda p:p["confirmed_at_ts"])
    pivot_index=0
    used_high=set()
    used_low=set()
    for i,opened_at in enumerate(ts):
        while pivot_index<len(pivot_events) and pivot_events[pivot_index]["confirmed_at_ts"] < opened_at:
            pivot=pivot_events[pivot_index]
            if pivot["kind"]=="pivot_high":
                active_high=pivot
            else:
                active_low=pivot
            pivot_index+=1
        if active_high and active_high["pivot_ts"] not in used_high:
            level=active_high["level"]
            if highs[i]>level and closes[i]<level:
                sweeps.append({"kind":"bsl_sweep","direction":"bearish",
                               "detected_at_ts":opened_at,
                               "known_after_close_ts":opened_at+interval_ms,
                               "pivot_ts":active_high["pivot_ts"],
                               "swept_level":level})
                used_high.add(active_high["pivot_ts"])
        if active_low and active_low["pivot_ts"] not in used_low:
            level=active_low["level"]
            if lows[i]<level and closes[i]>level:
                sweeps.append({"kind":"ssl_sweep","direction":"bullish",
                               "detected_at_ts":opened_at,
                               "known_after_close_ts":opened_at+interval_ms,
                               "pivot_ts":active_low["pivot_ts"],
                               "swept_level":level})
                used_low.add(active_low["pivot_ts"])

    return {"n_bars":n,"pivot_span":pivot_span,
            "bos":bos[-max_events:],"fvg":fvg[-max_events:],
            "pivots":pivots[-max_events:],
            "sweeps":sweeps[-max_events:],
            "choch_candidates":choch_candidates[-max_events:],
            "counts":{"bos_bullish":sum(x["direction"]=="bullish" for x in bos),
                      "bos_bearish":sum(x["direction"]=="bearish" for x in bos),
                      "fvg_bullish":sum(x["direction"]=="bullish" for x in fvg),
                      "fvg_bearish":sum(x["direction"]=="bearish" for x in fvg),
                      "ssl_sweeps":sum(x["kind"]=="ssl_sweep" for x in sweeps),
                      "bsl_sweeps":sum(x["kind"]=="bsl_sweep" for x in sweeps),
                      "choch_candidates":len(choch_candidates)},
            "warning":"Experimental price-action event detection only. No auto-generated RFM trade signals or measured edge."}
