"""Explainable, causal verification of mechanically selected Fibonacci anchors.

This module audits a proposed swing; it does NOT choose which discretionary
swing the user would draw. Inspect candles only up to the decision bar.
A valid selected impulse must have its stop-side and target-side extremes
at the two anchor candles, within numerical floating-point tolerance.
"""
from math import isfinite, isclose


def audit_swing_geometry(candles, *, hundred_index, zero_index, asof_index, side):
    """Return a reproducible geometric audit, independent of trade PnL.

    A long swing requires the 100% low to be the minimum and the 0% high
    to be the maximum of [hundred_index, zero_index]. Short is symmetric.
    An invalid extreme is REJECTED by the experimental impulse generator.
    No price after asof_index is ever inspected.
    """
    if (side not in ("long", "short") or
            not all(isinstance(x, int) for x in
                    (hundred_index, zero_index, asof_index)) or
            not (0 <= hundred_index < zero_index <= asof_index < len(candles))):
        raise ValueError("invalid swing anchor indices or side")
    selected=candles[hundred_index:zero_index+1]
    known=candles[:asof_index+1]
    if any(c.get("confirmed") is not True for c in known):
        raise ValueError("unconfirmed candle in swing audit history")
    highs=[float(b["high"]) for b in selected]
    lows=[float(b["low"]) for b in selected]
    if not all(isfinite(x) and x>0 for x in highs+lows):
        raise ValueError("non-finite swing prices")
    if any(h<l for h,l in zip(highs,lows)):
        raise ValueError("invalid swing candle")
    if side=="long":
        stop=float(candles[hundred_index]["low"])
        target=float(candles[zero_index]["high"])
        actual_stop=min(lows)
        actual_target=max(highs)
    else:
        stop=float(candles[hundred_index]["high"])
        target=float(candles[zero_index]["low"])
        actual_stop=max(highs)
        actual_target=min(lows)
    # The tolerance corrects only floating representation, not an ATR
    # buffer or an invented discretionary change of swing anchor.
    stop_valid=isclose(stop,actual_stop,rel_tol=1e-12,abs_tol=1e-12)
    target_valid=isclose(target,actual_target,rel_tol=1e-12,abs_tol=1e-12)
    directional=(target>stop) if side=="long" else (target<stop)
    return {
        "stop_extreme_valid":stop_valid,
        "target_extreme_valid":target_valid,
        "anchors_valid":bool(stop_valid and target_valid and directional),
        "directional_valid":directional,
        "stop_anchor_price":stop,
        "target_anchor_price":target,
        "true_stop_extreme_within_span":actual_stop,
        "true_target_extreme_within_span":actual_target,
        "swing_duration_bars":zero_index-hundred_index,
        "confirmation_lag_bars":asof_index-zero_index,
        "swing_fraction":abs(target-stop)/stop,
        "hundred_anchor_ts":int(candles[hundred_index]["ts"]),
        "zero_anchor_ts":int(candles[zero_index]["ts"]),
        "signal_ts":int(candles[asof_index]["ts"]),
        "warning":"Geometric validity does not establish that these anchors match the user's discretionary RFM."
    }
