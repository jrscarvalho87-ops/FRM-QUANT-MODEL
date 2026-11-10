"""Causal structural-liquidity relevance PROXIES for a selected Fibonacci swing.

"Relevant" is a user judgment awaiting annotated examples. These summaries
describe location, survival and structural age without adopting new RFM gates.
No invented distance-to-Gold-Zone or distance-to-take-profit requirement.
"""
from math import isfinite


def summarize_liquidity_for_swing(zones, *, hundred_price, zero_price,
                                  hundred_anchor_ts, zero_anchor_ts,
                                  signal_ts, interval_ms=900000):
    if not (interval_ms>0 and 0<=hundred_anchor_ts<zero_anchor_ts<=signal_ts):
        raise ValueError("invalid swing context timestamps")
    low,high=sorted((float(hundred_price),float(zero_price)))
    if not (isfinite(low) and isfinite(high) and 0<low<high):
        raise ValueError("invalid swing context prices")
    cutoff=signal_ts+interval_ms
    rows=[]
    for z in zones:
        price=float(z["price"])
        anchor=int(z["anchor_ts"])
        known=int(z["known_after_close_ts"])
        if not isfinite(price) or price<=0 or anchor>signal_ts or known>cutoff:
            raise ValueError("liquidity zone is nonfinite or from the future")
        kind=str(z["type"])
        not_breached=z.get("breached_after_confirmation") is False
        in_range=low<=price<=high
        formed_during_impulse=hundred_anchor_ts<=anchor<=zero_anchor_ts
        known_before_impulse=known<=hundred_anchor_ts
        # The Fibonacci extremes themselves are naturally high/low pivots.
        # Counting them as "extra liquidity" makes all setups pass by
        # construction. Keep them in raw counts, exclude them from the
        # INDEPENDENT structural-liquidity descriptors.
        is_fibonacci_anchor=anchor in (hundred_anchor_ts,zero_anchor_ts)
        rows.append({
            "type":kind,"price":price,"anchor_ts":anchor,
            "known_after_close_ts":known,
            "in_swing_price_range":in_range,
            "formed_during_impulse":formed_during_impulse,
            "known_before_impulse":known_before_impulse,
            "is_fibonacci_anchor":is_fibonacci_anchor,
            "unbreached_at_signal":not_breached,
            "bars_since_known":max(0,(cutoff-known)//interval_ms),
        })
    in_range=[r for r in rows if r["in_swing_price_range"]]
    unbreached_in_range=[r for r in in_range if r["unbreached_at_signal"]]
    during=[r for r in in_range if r["formed_during_impulse"]]
    before=[r for r in in_range if r["known_before_impulse"]]
    both=[r for r in in_range if r["unbreached_at_signal"]
          and (r["formed_during_impulse"] or r["known_before_impulse"])]
    independent=[r for r in in_range if not r["is_fibonacci_anchor"]]
    independent_unbreached=[
        r for r in independent if r["unbreached_at_signal"]]
    independent_contextual=[
        r for r in independent_unbreached
        if r["formed_during_impulse"] or r["known_before_impulse"]]
    # Liquidity can also be external to the selected Fibonacci amplitude.
    # Keep levels on either side without inventing a maximum price distance.
    independent_unbreached_all=[
        r for r in rows if not r["is_fibonacci_anchor"] and
        r["unbreached_at_signal"]]
    external_above=[
        r for r in independent_unbreached_all if r["price"]>high]
    external_below=[
        r for r in independent_unbreached_all if r["price"]<low]
    return {
        "all_known_zone_count":len(rows),
        "in_swing_price_range_count":len(in_range),
        "unbreached_in_swing_count":len(unbreached_in_range),
        "formed_during_swing_count":len(during),
        "known_before_swing_count":len(before),
        "unbreached_contextual_count":len(both),
        "in_swing_distinct_types":len({r["type"] for r in in_range}),
        "unbreached_contextual_distinct_types":len({r["type"] for r in both}),
        "independent_in_swing_count":len(independent),
        "independent_unbreached_count":len(independent_unbreached),
        "independent_unbreached_contextual_count":len(independent_contextual),
        "independent_unbreached_contextual_types":len({
            r["type"] for r in independent_contextual}),
        "independent_unbreached_external_above_count":len(external_above),
        "independent_unbreached_external_below_count":len(external_below),
        "independent_unbreached_external_types":len({
            r["type"] for r in external_above+external_below}),
        "observed_zone_types":sorted({r["type"] for r in in_range}),
        "independent_unbreached_contextual_levels":independent_contextual,
        "unbreached_contextual_levels":both,
        "warning":"Fibonacci anchors are excluded from independent structural counts; external levels can be anywhere outside the Fib range. No proximity requirement, claim of real liquidity, or approved entry threshold."
    }
