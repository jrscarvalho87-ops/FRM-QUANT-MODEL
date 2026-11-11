"""Time-causal market-structure / range-vs-expansion descriptors for RFM.

The RFM user identified faulty auto-selected lows, weak PA/volume and
abrupt expansion instead of an established range. These are DIAGNOSTIC
FEATURES, not invented mandatory setup rules, fitted thresholds or ML labels.

Uses only confirmed candles at/before the decision. Distinguishes chronological
price movement (100% -> 0%) from the TradingView drawing click order:
uptrend: high -> low; downtrend: low -> high.
"""
from math import isfinite


def _efficiency(closes):
    """Close-based net movement / total absolute movement; 0..1."""
    if len(closes)<2:
        return None
    path=sum(abs(b-a) for a,b in zip(closes,closes[1:]))
    return abs(closes[-1]-closes[0])/path if path>0 else 0.0


def _tr(rows,prior_close=None):
    results=[]
    previous=prior_close
    for row in rows:
        h,l,c=(float(row[k]) for k in ("high","low","close"))
        results.append(max(h-l,abs(h-previous),abs(l-previous))
                       if previous is not None else h-l)
        previous=c
    return results


def describe_structure_context(candles, *, hundred_index, zero_index,
                               asof_index, pre_bars=48, atr_bars=14,
                               pivot_span=3):
    """Describe a *candidate* impulse and its preceding balance, not approve it.

    Never require BOS, a sweep, high volume, or a specific range threshold.
    The human must decide whether a swing/low is structurally meaningful.
    """
    if (not isinstance(candles,(list,tuple)) or
        not all(isinstance(i,int) for i in (hundred_index,zero_index,asof_index)) or
        not 0<=hundred_index<zero_index<=asof_index<len(candles) or
        not isinstance(pre_bars,int) or not 8<=pre_bars<=500 or
        not isinstance(atr_bars,int) or not 5<=atr_bars<=pre_bars or
        not isinstance(pivot_span,int) or not 2<=pivot_span<=10):
        raise ValueError("invalid causal market-structure context")
    begin=max(0,hundred_index-pre_bars)
    inspected=candles[begin:asof_index+1]
    if any(row.get("confirmed") is not True for row in inspected):
        raise ValueError("structure feature may only inspect confirmed candles")
    for row in inspected:
        o,h,l,c=(float(row[k]) for k in ("open","high","low","close"))
        if not all(isfinite(v) and v>0 for v in (o,h,l,c)) or not l<=min(o,c)<=max(o,c)<=h:
            raise ValueError("invalid historical structure OHLC")

    pre=candles[begin:hundred_index]
    swing=candles[hundred_index:zero_index+1]
    volumes=[]
    for row in inspected:
        v=row.get("volume_contracts")
        if v is not None and (not isfinite(float(v)) or float(v)<0):
            raise ValueError("invalid structure volume")
    pre_closes=[float(x["close"]) for x in pre]
    swing_closes=[float(x["close"]) for x in swing]
    pre_atr=(sum(_tr(pre[-atr_bars:],
                     float(pre[-atr_bars-1]["close"])
                     if len(pre)>atr_bars else None))/atr_bars
             if len(pre)>=atr_bars else None)
    swing_tr=_tr(swing,prior_close=float(pre[-1]["close"]) if pre else None)
    pre_range=(max(float(x["high"]) for x in pre)-
               min(float(x["low"]) for x in pre)) if pre else None
    # Pivots are counted only when their right-hand confirmation is
    # available by the signal; this is *not* swing anchor selection.
    confirmed_turns=[]
    for p in range(hundred_index+1,zero_index):
        if p-pivot_span<begin or p+pivot_span>asof_index:
            continue
        w=candles[p-pivot_span:p+pivot_span+1]
        anchor=candles[p]
        is_high=all(float(anchor["high"])>float(x["high"])
                    for k,x in enumerate(w) if k!=pivot_span)
        is_low=all(float(anchor["low"])<float(x["low"])
                   for k,x in enumerate(w) if k!=pivot_span)
        if is_high!=is_low:
            confirmed_turns.append((p,"high" if is_high else "low"))
    # An unbroken run of repeated same-type pivots is not a range.
    alternating_turns=sum(a[1]!=b[1]
                          for a,b in zip(confirmed_turns,confirmed_turns[1:]))
    pre_volumes=[float(x["volume_contracts"]) for x in pre
                 if x.get("volume_contracts") is not None]
    swing_volumes=[float(x["volume_contracts"]) for x in swing
                   if x.get("volume_contracts") is not None]
    volume_complete=len(pre_volumes)==len(pre) and len(swing_volumes)==len(swing)
    mean_pre_volume=sum(pre_volumes)/len(pre_volumes) if pre_volumes else None
    mean_swing_volume=sum(swing_volumes)/len(swing_volumes) if swing_volumes else None
    volume_ratio=(mean_swing_volume/mean_pre_volume
                  if volume_complete and mean_pre_volume and mean_swing_volume is not None
                  else None)
    signal_volume_ratio=None
    if asof_index>=20:
        lookback=candles[asof_index-20:asof_index]
        if all(x.get("volume_contracts") is not None for x in lookback) and (
                candles[asof_index].get("volume_contracts") is not None):
            previous_mean=sum(float(x["volume_contracts"]) for x in lookback)/20
            if previous_mean>0:
                signal_volume_ratio=float(candles[asof_index]["volume_contracts"])/previous_mean
    swing_total_tr=sum(swing_tr)
    return {
        "status":"ok" if len(pre)>=atr_bars else "prehistory_incomplete",
        "pre_context_bars":len(pre),
        "swing_candle_count":len(swing),
        "pre_close_efficiency":_efficiency(pre_closes),
        "pre_range_to_atr":pre_range/pre_atr if pre_atr and pre_range is not None else None,
        "swing_close_efficiency":_efficiency(swing_closes),
        "swing_largest_bar_share":max(swing_tr)/swing_total_tr if swing_total_tr else None,
        "swing_peak_tr_to_pre_atr":max(swing_tr)/pre_atr if pre_atr else None,
        "swing_mean_tr_to_pre_atr":(swing_total_tr/len(swing))/pre_atr
                                    if pre_atr else None,
        "interior_confirmed_pivots":len(confirmed_turns),
        "interior_alternating_pivot_pairs":alternating_turns,
        "swing_vs_prior_volume_ratio":volume_ratio,
        "signal_vs_previous_20_volume_ratio":signal_volume_ratio,
        "warning":"Range, expansion, volume and turns are provisional explanatory features. No human-approved entry thresholds or trend gate."
    }
