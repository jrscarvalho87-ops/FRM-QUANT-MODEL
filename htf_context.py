"""Causal 4H premium/discount CONTEXT from completed 15m candles.

An experimental rolling-range proxy, NOT the user's discretionary 4H
swing range. It is informational; never rejects entries or invents bias.
Periods are aligned to UTC boundaries; incomplete periods are not used.
"""
from math import isfinite

HTF_MS = 14_400_000


def four_hour_context(candles, asof_index, *, interval_ms=900000,
                      lookback_4h_bars=12):
    if not (isinstance(candles,(list,tuple)) and
            isinstance(asof_index,int) and 0<=asof_index<len(candles)
            and isinstance(interval_ms,int) and interval_ms>0
            and HTF_MS%interval_ms==0 and
            2<=lookback_4h_bars<=100):
        raise ValueError("invalid 4H context settings")
    decision=candles[asof_index]
    if decision.get("confirmed") is not True:
        raise ValueError("unconfirmed decision candle")
    close_ts=int(decision["ts"])+interval_ms
    completed_end=close_ts//HTF_MS*HTF_MS
    first=completed_end-lookback_4h_bars*HTF_MS
    needed=lookback_4h_bars*(HTF_MS//interval_ms)
    if needed<=0:
        raise ValueError("invalid higher-timeframe period")
    tail=[]
    # Only rows that were confirmed and timestamped before decision close.
    for b in candles[:asof_index+1]:
        t=int(b["ts"])
        if first<=t<completed_end:
            if b.get("confirmed") is not True:
                raise ValueError("unconfirmed historical higher-timeframe candle")
            tail.append(b)
    if len(tail)!=needed:
        return {"status":"insufficient_complete_4h_periods",
                "position":"unknown","fraction":None,
                "complete_4h_bars":len(tail)*interval_ms//HTF_MS,
                "lookback_4h_bars":lookback_4h_bars}
    times=[int(b["ts"]) for b in tail]
    if times[0]!=first or times[-1]!=completed_end-interval_ms or any(
            t2-t1!=interval_ms for t1,t2 in zip(times,times[1:])):
        raise ValueError("gap or misalignment in higher timeframe")
    highs=[float(b["high"]) for b in tail]
    lows=[float(b["low"]) for b in tail]
    spot=float(decision["close"])
    if not all(isfinite(v) and v>0 for v in highs+lows+[spot]):
        raise ValueError("invalid higher-timeframe OHLC")
    top=max(highs)
    bottom=min(lows)
    if not top>bottom:
        return {"status":"zero_range","position":"unknown",
                "fraction":None,"lookback_4h_bars":lookback_4h_bars}
    fraction=(spot-bottom)/(top-bottom)
    position="premium" if fraction>.5 else "discount" if fraction<.5 else "equilibrium"
    return {"status":"ok","position":position,
            "fraction":round(fraction,8),
            "lookback_4h_bars":lookback_4h_bars,
            "range_low":bottom,"range_high":top,
            "last_completed_4h_end_ts":completed_end,
            "known_after_close_ts":close_ts,
            "warning":"Rolling confirmed 4H range proxy only; does not identify the user's HTF swing anchors."}
