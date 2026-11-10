"""Explicitly experimental, fully deterministic RFM candidate generator.

This is a NEW testable hypothesis, not a claim to reproduce the user's
discretionary Fibonacci anchors. A swing is selected using confirmed pivots:
bullish: latest confirmed pivot low preceding a close above a confirmed pivot
high; bearish: latest confirmed pivot high preceding a close below a confirmed
pivot low. Both pivot extremes must be in correct chronological order.
Only CLOSED candles may contribute to a signal.
"""
from math import isfinite
from fibonacci import levels


def generate_candidates(candles, *, pivot_span=3, expiry_bars=8,
                        entry_level=75, require_fvg=False,
                        min_swing_fraction=0.005, interval_ms=900000,
                        max_signals=200):
    if not (2 <= pivot_span <= 10 and 1 <= expiry_bars <= 96
            and entry_level in (67,75) and 0 <= min_swing_fraction <= .25
            and interval_ms > 0 and 1 <= max_signals <= 200):
        raise ValueError("Invalid candidate generator settings")
    bars=list(candles)
    if len(bars)>2000:
        raise ValueError("At most 2000 candles")
    times=[int(b["ts"]) for b in bars]
    if times!=sorted(set(times)):
        raise ValueError("Candles must be unique and chronological")
    if any(times[i]-times[i-1]!=interval_ms for i in range(1,len(times))):
        raise ValueError("No backtest candidates across candle gaps")
    for b in bars:
        if b.get("confirmed") is not True:
            raise ValueError("Unconfirmed candle in candidate window")
    highs=[float(b["high"]) for b in bars]
    lows=[float(b["low"]) for b in bars]
    closes=[float(b["close"]) for b in bars]
    if not all(isfinite(v) and v>0 for v in highs+lows+closes):
        raise ValueError("Invalid prices")
    if any(l>min(c,h) or h<max(c,l) for l,h,c in zip(lows,highs,closes)):
        raise ValueError("Invalid candle ranges")

    latest_high=None
    latest_low=None
    signals=[]
    events=[]
    last_break_high_ts=None
    last_break_low_ts=None
    for i in range(len(bars)):
        pivot=i-pivot_span
        if pivot>=pivot_span:
            hi=highs[pivot]
            lo=lows[pivot]
            if all(hi>highs[k] for k in range(pivot-pivot_span,pivot+pivot_span+1) if k!=pivot):
                latest_high={"price":hi,"ts":times[pivot],"confirmed_ts":times[i],"index":pivot}
            if all(lo<lows[k] for k in range(pivot-pivot_span,pivot+pivot_span+1) if k!=pivot):
                latest_low={"price":lo,"ts":times[pivot],"confirmed_ts":times[i],"index":pivot}

        if i==0:
            continue
        candidates=[]
        if (latest_high and latest_low
                and latest_low["index"]<latest_high["index"]
                and times[i]>latest_high["confirmed_ts"]
                and closes[i]>latest_high["price"] and closes[i-1]<=latest_high["price"]
                and latest_high["ts"]!=last_break_high_ts):
            candidates.append(("long",latest_high,latest_low))
            last_break_high_ts=latest_high["ts"]
        if (latest_high and latest_low
                and latest_high["index"]<latest_low["index"]
                and times[i]>latest_low["confirmed_ts"]
                and closes[i]<latest_low["price"] and closes[i-1]>=latest_low["price"]
                and latest_low["ts"]!=last_break_low_ts):
            candidates.append(("short",latest_low,latest_high))
            last_break_low_ts=latest_low["ts"]
        for side,broken,opposite in candidates:
            # The 0% is the known extreme of the move at signal close,
            # not an unknown future high/low.
            zero_idx=(max(range(broken["index"],i+1),key=lambda k:highs[k]) if side=="long"
                      else min(range(broken["index"],i+1),key=lambda k:lows[k]))
            zero=highs[zero_idx] if side=="long" else lows[zero_idx]
            hundred=opposite["price"]
            if side=="long" and zero<=hundred or side=="short" and zero>=hundred:
                continue
            if abs(zero-hundred)/hundred<min_swing_fraction:
                continue
            fib=levels(zero,hundred,side)
            fvg=[]
            for j in range(max(2,broken["index"]),i+1):
                if side=="long" and lows[j]>highs[j-2]:
                    lower,upper=highs[j-2],lows[j]
                elif side=="short" and highs[j]<lows[j-2]:
                    lower,upper=highs[j],lows[j-2]
                else:
                    continue
                if min(upper,fib["entry_zone_high"])>max(lower,fib["entry_zone_low"]):
                    fvg.append({"lower":lower,"upper":upper,
                                "known_after_close_ts":times[j]+interval_ms})
            fvg_overlap=bool(fvg)
            if require_fvg and not fvg_overlap:
                continue
            entry=fib["level_67"] if entry_level==67 else fib["level_75"]
            # The execution simulator is responsible for next-bar eligibility,
            # risk sizing, fills, costs and conservative exit ordering.
            sig={"signal_ts":times[i],"side":side,"entry":entry,
                 "stop":hundred,"take":zero,"expiry_bars":expiry_bars}
            signals.append(sig)
            events.append({
                "signal_ts":times[i],"known_after_close_ts":times[i]+interval_ms,
                "side":side,"anchor_100_ts":opposite["ts"],
                "anchor_0_ts":times[zero_idx],"zero_price":zero,"hundred_price":hundred,
                "entry_level":entry_level,"fvg_overlaps_gold_zone":fvg_overlap,
                "fvg_count":len(fvg),"broken_pivot_ts":broken["ts"],
                "notes":"Candidate based on confirmed pivots and breakout, not discretionary RFM."
            })
    truncated=len(signals)>max_signals
    signals=signals[-max_signals:]
    events=events[-max_signals:]
    return {
        "hypothesis":"confirmed_pivot_breakout_fibonacci_v1",
        "status":"experimental_not_user_approved",
        "settings":{"pivot_span":pivot_span,"expiry_bars":expiry_bars,
                    "entry_level":entry_level,"require_fvg":require_fvg,
                    "min_swing_fraction":min_swing_fraction},
        "signal_count":len(signals),"truncated":truncated,
        "signals":signals,"events":events,
        "warnings":[
            "Mechanical candidate, not a faithful reproduction of discretionary RFM.",
            "FVG overlap is a simple three-candle price-gap heuristic, not an unfilled-FVG validity test.",
            "No Volume Profile/POC confirmation or higher-timeframe alignment is included in candidate selection.",
            "Anchors and signals use only candles known at the decision candle close.",
            "Historical survivorship, funding, spreads and real execution remain unmodelled."
        ]
    }
