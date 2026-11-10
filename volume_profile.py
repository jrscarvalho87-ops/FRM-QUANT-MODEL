"""OHLCV-only fixed-range Volume Profile approximation.

True volume-at-price data are not available from aggregate candles. Each
candle's contract volume is spread uniformly across its high-low range.
This MUST NOT be presented as TradingView's tick-level Volume Profile.
The window starts on the Fibonacci anchor and ends at the last confirmed bar
known at the hypothetical decision time. Future candles are ignored.
"""
from math import floor, isfinite


def approximate_poc(candles, anchor_ts, asof_ts, *, bins=48,
                    interval_ms=900000, zero_price=None, hundred_price=None,
                    side=None):
    try:
        anchor_ts, asof_ts, bins, interval_ms = (int(anchor_ts), int(asof_ts),
                                                 int(bins), int(interval_ms))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Invalid timestamp, bin count or interval") from exc
    if not (8 <= bins <= 200 and interval_ms > 0 and anchor_ts > 0 and asof_ts >= anchor_ts):
        raise ValueError("Expected 8..200 bins and a valid historical window")
    if not isinstance(candles,list) or len(candles) > 3000:
        raise ValueError("Expected at most 3000 candles")

    selected = []
    excluded_future = 0
    excluded_unconfirmed = 0
    timestamps = set()
    for bar in candles:
        try:
            ts = int(bar["ts"])
        except (TypeError, ValueError, KeyError, OverflowError) as exc:
            raise ValueError("Invalid candle timestamp") from exc
        if ts > asof_ts:
            excluded_future += 1
            continue
        if ts < anchor_ts:
            continue
        if bar.get("confirmed") is not True:
            excluded_unconfirmed += 1
            continue
        if ts in timestamps:
            raise ValueError("Duplicate candles in selected window")
        timestamps.add(ts)
        try:
            low, high, volume = (float(bar[k]) for k in ("low","high","volume_contracts"))
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            raise ValueError("Invalid OHLCV in window") from exc
        if not all(isfinite(x) for x in (low,high,volume)) or low <= 0 or high < low or volume < 0:
            raise ValueError("Non-finite, negative or inconsistent OHLCV in window")
        selected.append((ts,low,high,volume))
    selected.sort()
    if not selected or selected[0][0] != anchor_ts:
        raise ValueError("Fibonacci anchor timestamp has no confirmed candle")
    if selected[-1][0] != asof_ts:
        raise ValueError("As-of timestamp must be a confirmed candle")
    if any(right[0]-left[0] != interval_ms for left,right in zip(selected,selected[1:])):
        raise ValueError("Missing or irregular candles; no interpolation allowed")

    p_low = min(r[1] for r in selected)
    p_high = max(r[2] for r in selected)
    if p_high <= p_low:
        raise ValueError("Price range has zero width")
    width = (p_high-p_low)/bins
    buckets = [0.0]*bins
    for _,low,high,volume in selected:
        if volume == 0:
            continue
        if high == low:
            idx = max(0,min(bins-1,floor((low-p_low)/width)))
            buckets[idx] += volume
            continue
        first=max(0,min(bins-1,floor((low-p_low)/width)))
        last=max(0,min(bins-1,floor((high-p_low)/width)))
        for idx in range(first,last+1):
            bot=p_low+idx*width
            overlap=max(0.0,min(high,bot+width)-max(low,bot))
            buckets[idx] += volume*overlap/(high-low)

    total_volume = sum(r[3] for r in selected)
    if total_volume <= 0 or not any(buckets):
        raise ValueError("Window has zero contract volume; no POC")
    max_bucket=max(buckets)
    ties=[i for i,v in enumerate(buckets) if abs(v-max_bucket)<=max(1e-10,max_bucket*1e-12)]
    midpoint=(p_low+p_high)/2
    peak=min(ties,key=lambda i:(abs(p_low+(i+.5)*width-midpoint),i))
    poc=p_low+(peak+.5)*width
    result={
        "method":"OHLCV_uniform_high_low_proxy",
        "is_true_traded_volume_poc":False,
        "volume_unit":"contracts",
        "anchor_ts":anchor_ts,"asof_ts":asof_ts,
        "known_after_close_ts":asof_ts+interval_ms,
        "confirmed_bars_used":len(selected),
        "future_bars_ignored":excluded_future,
        "unconfirmed_bars_ignored":excluded_unconfirmed,
        "bins":bins,
        "price_range_low":p_low,"price_range_high":p_high,
        "poc_price_approx":round(poc,10),
        "poc_bin_low":round(p_low+peak*width,10),
        "poc_bin_high":round(p_low+(peak+1)*width,10),
        "total_contract_volume":round(total_volume,8),
        "profile":[{"price":round(p_low+(i+.5)*width,10),"volume_contracts":round(v,8)}
                   for i,v in enumerate(buckets)],
        "warning":"OHLCV approximation only; volume at each traded price unavailable. Not equivalent to TradingView Volume Profile.",
    }
    anchors_provided=any(x is not None for x in (zero_price,hundred_price,side))
    if anchors_provided:
        if any(x is None for x in (zero_price,hundred_price,side)):
            raise ValueError("Provide side, zero_price and hundred_price together")
        from fibonacci import levels
        fib=levels(zero_price,hundred_price,side)
        lower,upper=fib["entry_zone_low"],fib["entry_zone_high"]
        distance=max(lower-poc,poc-upper,0.0)
        result["gold_zone"]={
            "lower":round(lower,10),"upper":round(upper,10),
            "poc_inside_zone":lower <= poc <= upper,
            "distance_from_zone_price":round(distance,10),
            "distance_from_zone_pct_swing":round(
                100*distance/abs(fib["zero"]-fib["hundred"]),5),
            "note":"Exact overlap only; no unapproved near-zone distance threshold. POC optional."
        }
    return result
