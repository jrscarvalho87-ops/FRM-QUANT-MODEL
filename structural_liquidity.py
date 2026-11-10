"""Causal structural-liquidity FEATURES, not a user-approved entry score.

BSL/SSL: confirmed swing highs/lows; EQH/EQL: pairs of confirmed pivots
within a provisional ATR tolerance. Previous day/week levels count only if
an entire UTC calendar period is present in the historical sample.
No future candle may influence features calculated at asof_index.
"""
from math import isfinite

DAY_MS = 86_400_000
WEEK_MS = 7 * DAY_MS
# 1970-01-01 was a Thursday; ISO-like Monday UTC week starts.
MONDAY_OFFSET_MS = 3 * DAY_MS


def _complete_period(bars, start, length, interval_ms):
    if length % interval_ms:
        return None
    selected = [b for b in bars if start <= b["ts"] < start + length]
    if len(selected) != length // interval_ms:
        return None
    if selected[0]["ts"] != start or selected[-1]["ts"] != start + length - interval_ms:
        return None
    if any(b["ts"] - a["ts"] != interval_ms for a, b in zip(selected, selected[1:])):
        return None
    return selected


def structural_liquidity(candles, asof_index, *, interval_ms=900_000,
                         pivot_span=3, lookback_bars=240, atr_period=14,
                         equal_atr_tolerance=0.15):
    """Return features known after the close of candles[asof_index].

    Thresholds are RESEARCH PARAMETERS, not claims about the user's rules.
    The 'zone_count' is a count of observed levels, not an entry filter.
    """
    if not (isinstance(asof_index, int) and isinstance(candles, (list, tuple))
            and 0 <= asof_index < len(candles)
            and isinstance(interval_ms, int) and interval_ms > 0
            and 2 <= pivot_span <= 10 and lookback_bars >= 2*pivot_span+1
            and 5 <= atr_period <= 100 and 0 <= equal_atr_tolerance <= 2):
        raise ValueError("invalid structural liquidity arguments")
    bars = []
    for row in candles[:asof_index+1]:
        if row.get("confirmed") is not True:
            raise ValueError("unconfirmed candle at decision time")
        t = int(row["ts"])
        o,h,l,c = (float(row[k]) for k in ("open", "high", "low", "close"))
        if not all(isfinite(v) and v > 0 for v in (o,h,l,c)) or not l <= min(o,c) <= max(o,c) <= h:
            raise ValueError("invalid OHLC")
        if bars and t - bars[-1]["ts"] != interval_ms:
            raise ValueError("historical gap; structural context not reliable")
        bars.append({"ts":t,"high":h,"low":l,"close":c})
    if len(bars) < 2*pivot_span+1:
        return {"status":"warmup", "zone_count":0,"bsl_count":0,"ssl_count":0,
                "eqh_pairs":0,"eql_pairs":0,"previous_day_available":False,
                "previous_week_available":False,"zones":[]}
    a = len(bars)-1
    tr = []
    for j in range(max(0,a-atr_period+1),a+1):
        prior = bars[j-1]["close"] if j else bars[j]["close"]
        tr.append(max(bars[j]["high"]-bars[j]["low"],
                      abs(bars[j]["high"]-prior), abs(bars[j]["low"]-prior)))
    atr = sum(tr)/len(tr)
    tolerance = max(equal_atr_tolerance*atr, bars[-1]["close"]*1e-9)
    piv_hi, piv_lo = [], []
    for j in range(max(pivot_span,a-lookback_bars+1),a-pivot_span+1):
        high = bars[j]["high"]
        low = bars[j]["low"]
        other = [k for k in range(j-pivot_span,j+pivot_span+1) if k != j]
        if all(high > bars[k]["high"] for k in other):
            piv_hi.append({"type":"BSL","price":high,"anchor_ts":bars[j]["ts"],
                           "known_after_close_ts":bars[j+pivot_span]["ts"]+interval_ms})
        if all(low < bars[k]["low"] for k in other):
            piv_lo.append({"type":"SSL","price":low,"anchor_ts":bars[j]["ts"],
                           "known_after_close_ts":bars[j+pivot_span]["ts"]+interval_ms})
    def equal_pairs(pivots):
        pairs=[]
        for n, p in enumerate(pivots):
            prior = next((q for q in reversed(pivots[:n])
                          if abs(q["price"]-p["price"]) <= tolerance),None)
            if prior is not None:
                pairs.append((prior,p))
        return pairs
    eqh=equal_pairs(piv_hi)
    eql=equal_pairs(piv_lo)
    current_day_start = bars[-1]["ts"] // DAY_MS * DAY_MS
    current_week_start = (bars[-1]["ts"] + MONDAY_OFFSET_MS) // WEEK_MS * WEEK_MS - MONDAY_OFFSET_MS
    prev_day = _complete_period(bars,current_day_start-DAY_MS,DAY_MS,interval_ms)
    prev_week = _complete_period(bars,current_week_start-WEEK_MS,WEEK_MS,interval_ms)
    zones=piv_hi+piv_lo
    for name, period in (("PD",prev_day),("PW",prev_week)):
        if period is None:
            continue
        close_ts=period[-1]["ts"]+interval_ms
        zones.extend([
            {"type":name+"H","price":max(b["high"] for b in period),
             "anchor_ts":period[0]["ts"],"known_after_close_ts":close_ts},
            {"type":name+"L","price":min(b["low"] for b in period),
             "anchor_ts":period[0]["ts"],"known_after_close_ts":close_ts},
        ])
    for kind,pairs in (("EQH",eqh),("EQL",eql)):
        for earlier,later in pairs:
            zones.append({"type":kind,"price":(earlier["price"]+later["price"])/2,
                          "anchor_ts":earlier["anchor_ts"],
                          "known_after_close_ts":later["known_after_close_ts"]})
    asof_close_ts=bars[-1]["ts"]+interval_ms
    if any(z["known_after_close_ts"]>asof_close_ts for z in zones):
        raise ValueError("future information detected in structural feature")
    return {"status":"ok","zone_count":len(zones),
            "bsl_count":len(piv_hi),"ssl_count":len(piv_lo),
            "eqh_pairs":len(eqh),"eql_pairs":len(eql),
            "previous_day_available":prev_day is not None,
            "previous_week_available":prev_week is not None,
            "atr":round(atr,12),"equal_price_tolerance":round(tolerance,12),
            "asof_ts":bars[-1]["ts"],"known_after_close_ts":asof_close_ts,
            "zones":zones}
