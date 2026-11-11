"""RFM Fibonacci price arithmetic, independent of swing-selection rules.

The zero anchor is always the target-side extreme and 100 is the stop-side
extreme. This module does not generate signals or use future candles.
"""
from math import isfinite


def levels(zero_price: float, hundred_price: float, side: str):
    zero = float(zero_price)
    hundred = float(hundred_price)
    if side not in ("long", "short"):
        raise ValueError("side must be long or short")
    if not (isfinite(zero) and isfinite(hundred) and zero > 0 and hundred > 0 and zero != hundred):
        raise ValueError("invalid Fibonacci anchors")
    if side == "long" and not zero > hundred:
        raise ValueError("long requires 0% above 100%")
    if side == "short" and not zero < hundred:
        raise ValueError("short requires 0% below 100%")
    return {
        "side": side, "zero": zero, "hundred": hundred,
        # Explicit user drawing interaction: click high -> low in uptrend,
        # low -> high in downtrend, on wick extremes. This is a user-facing
        # draw direction, not a claim that the high came first in time.
        "drawing_start_extreme": "high" if side=="long" else "low",
        "drawing_end_extreme": "low" if side=="long" else "high",
        "drawing_start_price": zero,
        "drawing_end_price": hundred,
        "anchor_source": "high_low_wicks_not_candle_bodies",
        "level_67": zero + .67 * (hundred - zero),
        "level_75": zero + .75 * (hundred - zero),
        "entry_zone_low": min(zero + .67*(hundred-zero),zero + .75*(hundred-zero)),
        "entry_zone_high": max(zero + .67*(hundred-zero),zero + .75*(hundred-zero)),
        "rr_at_67": 67/33, "rr_at_75": 3.0,
        "note": "Theoretical RR only, with stop exactly at 100 and TP exactly at 0, before costs.",
    }
