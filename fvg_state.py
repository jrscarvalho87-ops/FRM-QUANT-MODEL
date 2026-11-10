"""Causal three-candle FVG detection and partial/full mitigation tracking.

A formed FVG is never reused in a Gold Zone after that part of the gap
has been traded through. Uses only bars known at asof_index. Price-gap
proxy is not an assertion that a trade will fill or win.
"""
from math import isfinite


def active_fvgs_overlapping_zone(candles, asof_index, side, zone_low, zone_high,
                                 *, start_index=2):
    if not (isinstance(candles,(list,tuple)) and
            isinstance(asof_index,int) and 0<=asof_index<len(candles)
            and isinstance(start_index,int) and 0<=start_index<=asof_index
            and side in ("long","short")
            and isfinite(float(zone_low)) and isfinite(float(zone_high))
            and 0<float(zone_low)<float(zone_high)):
        raise ValueError("invalid FVG arguments")
    # Ignore future data *completely* (including unconfirmed future bars).
    bars = candles[:asof_index+1]
    for b in bars:
        if b.get("confirmed") is not True:
            raise ValueError("unconfirmed historical FVG candle")
    highs=[float(b["high"]) for b in bars]
    lows=[float(b["low"]) for b in bars]
    if not all(isfinite(x) and x>0 for x in highs+lows):
        raise ValueError("invalid FVG candle")
    result=[]
    for j in range(max(2,start_index),asof_index+1):
        if side=="long":
            lower, upper=highs[j-2],lows[j]
            if upper<=lower:continue
            # A long FVG fills from the upper boundary downwards.
            active_upper=min(upper,min(lows[j+1:],default=upper))
            active_lower=lower
        else:
            lower,upper=highs[j],lows[j-2]
            if upper<=lower:continue
            # A short FVG fills from the lower boundary upwards.
            active_lower=max(lower,max(highs[j+1:],default=lower))
            active_upper=upper
        if active_upper<=active_lower:
            continue
        overlap_low=max(active_lower,float(zone_low))
        overlap_high=min(active_upper,float(zone_high))
        if overlap_high>overlap_low:
            result.append({"formed_ts":int(bars[j]["ts"]),
                           "original_low":lower,"original_high":upper,
                           "active_low":active_lower,"active_high":active_upper,
                           "gold_overlap_low":overlap_low,
                           "gold_overlap_high":overlap_high})
    return result
