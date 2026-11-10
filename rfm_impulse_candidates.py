"""RFM experiment: confirmed swing-impulse candidates WITHOUT mandatory BOS.

Not the user's discretionary RFM. Anchors are a provisional causal pivot-pair
proxy; FVG must survive and overlap 67–75% Gold Zone. Confirmed structural
liquidity is measured as an *unvalidated feature*, not an invented entry rule.
For historical research only; no orders or forecasts.
"""
from math import isfinite

from fibonacci import levels
from fvg_state import active_fvgs_overlapping_zone
from structural_liquidity import structural_liquidity
from volume_profile import approximate_poc
from htf_context import four_hour_context


def generate_impulse_candidates(candles, *, pivot_span=3, expiry_bars=8,
                                entry_level=75, min_swing_fraction=0.005,
                                interval_ms=900000, max_signals=5000):
    if not (2<=pivot_span<=10 and 1<=expiry_bars<=96 and entry_level in (67,75)
            and 0<=min_swing_fraction<=.25 and interval_ms>0
            and 1<=max_signals<=5000):
        raise ValueError("invalid experimental impulse settings")
    bars=list(candles)
    if len(bars)>20000:
        raise ValueError("at most 20000 historical candles")
    times=[int(b["ts"]) for b in bars]
    if times!=sorted(set(times)):
        raise ValueError("historical timestamps must be strictly increasing")
    if any(b-a!=interval_ms for a,b in zip(times,times[1:])):
        raise ValueError("historical gaps are not allowed")
    prices={}
    for key in ("open","high","low","close"):
        prices[key]=[float(b[key]) for b in bars]
    for n,b in enumerate(bars):
        if b.get("confirmed") is not True:
            raise ValueError("only confirmed historical candles are allowed")
        o,h,l,c=(prices[k][n] for k in ("open","high","low","close"))
        if not all(isfinite(v) and v>0 for v in (o,h,l,c)) or l>min(o,c) or h<max(o,c):
            raise ValueError("invalid historical OHLC")
    highs,lows,closes=(prices[k] for k in ("high","low","close"))
    high_pivots=[]
    low_pivots=[]
    signals=[]
    events=[]
    rejected={"no_prior_opposite_pivot":0,"swing_too_small":0,
              "gold_zone_already_touched":0,"no_active_gold_fvg":0}
    for i in range(2*pivot_span,len(bars)):
        p=i-pivot_span
        other=[k for k in range(p-pivot_span,p+pivot_span+1) if k!=p]
        is_high=all(highs[p]>highs[k] for k in other)
        is_low=all(lows[p]<lows[k] for k in other)
        # An outside candle can sometimes be both; the anchors are ambiguous.
        if is_high and is_low:
            continue
        if is_high:
            high_pivots.append({"index":p,"price":highs[p],"ts":times[p],
                                "confirmed_ts":times[i]})
        if is_low:
            low_pivots.append({"index":p,"price":lows[p],"ts":times[p],
                               "confirmed_ts":times[i]})
        if not (is_high or is_low):
            continue
        side="long" if is_high else "short"
        opposite_pivots=low_pivots if is_high else high_pivots
        opposite=next((x for x in reversed(opposite_pivots) if x["index"]<p),None)
        if opposite is None:
            rejected["no_prior_opposite_pivot"]+=1
            continue
        hundred=opposite["price"]
        zero=highs[p] if side=="long" else lows[p]
        if side=="long" and zero<=hundred or side=="short" and zero>=hundred:
            rejected["swing_too_small"]+=1
            continue
        if abs(zero-hundred)/hundred<min_swing_fraction:
            rejected["swing_too_small"]+=1
            continue
        fib=levels(zero,hundred,side)
        # The pivot is only *known* after pivot_span right bars. If 67%
        # was already touched during confirmation, this would be a
        # retroactive signal. Never allow that to be traded as a new order.
        passed=bars[p+1:i+1]
        if (side=="long" and (closes[i]<=fib["level_67"]
            or any(float(b["low"])<=fib["level_67"] for b in passed))) or (
            side=="short" and (closes[i]>=fib["level_67"]
            or any(float(b["high"])>=fib["level_67"] for b in passed))):
            rejected["gold_zone_already_touched"]+=1
            continue
        fvg=active_fvgs_overlapping_zone(
            bars,i,side,fib["entry_zone_low"],fib["entry_zone_high"],
            start_index=max(2,opposite["index"]))
        if not fvg:
            rejected["no_active_gold_fvg"]+=1
            continue
        liquidity=structural_liquidity(
            bars,i,pivot_span=pivot_span,interval_ms=interval_ms)
        # Location measured across the structural swing, not necessarily
        # close to Gold Zone or TP. No user-approved threshold is imposed.
        in_swing=[z for z in liquidity["zones"]
                  if fib["entry_zone_low"]>=0 and
                  min(hundred,zero)<=z["price"]<=max(hundred,zero)]
        # Break-of-structure is a *separate, optional* heuristic feature:
        # did a candle close beyond the previously confirmed opposite high/low?
        same_side_pivots=high_pivots if is_high else low_pivots
        preceding=next((x for x in reversed(same_side_pivots[:-1])
                        if x["index"]<opposite["index"]),None)
        prior_break=False
        if preceding:
            if side=="long":
                prior_break=any(c>preceding["price"]
                                for c in closes[opposite["index"]+1:i+1])
            else:
                prior_break=any(c<preceding["price"]
                                for c in closes[opposite["index"]+1:i+1])
        htf=four_hour_context(bars,i,interval_ms=interval_ms)
        poc_price=None
        poc_in_zone=None
        if "volume_contracts" in bars[i] and times[opposite["index"]]>0:
            try:
                poc=approximate_poc(
                    bars[opposite["index"]:i+1],times[opposite["index"]],
                    times[i],interval_ms=interval_ms,zero_price=zero,
                    hundred_price=hundred,side=side)
                poc_price=poc["poc_price_approx"]
                poc_in_zone=poc["gold_zone"]["poc_inside_zone"]
            except ValueError:
                pass
        entry=fib["level_67"] if entry_level==67 else fib["level_75"]
        signals.append({"signal_ts":times[i],"side":side,"entry":entry,
                        "stop":hundred,"take":zero,"expiry_bars":expiry_bars})
        events.append({
            "signal_ts":times[i],"known_after_close_ts":times[i]+interval_ms,
            "side":side,"anchor_100_ts":opposite["ts"],
            "anchor_0_ts":times[p],
            "zero_price":zero,"hundred_price":hundred,
            "entry_level":entry_level,"fvg_overlaps_gold_zone":True,
            "fvg_count":len(fvg),
            "liquidity_zone_count":liquidity["zone_count"],
            "liquidity_structure_zone_count":len(in_swing),
            "liquidity_bsl_count":liquidity["bsl_count"],
            "liquidity_ssl_count":liquidity["ssl_count"],
            "liquidity_eqh_pairs":liquidity["eqh_pairs"],
            "liquidity_eql_pairs":liquidity["eql_pairs"],
            "liquidity_previous_day_available":liquidity["previous_day_available"],
            "liquidity_previous_week_available":liquidity["previous_week_available"],
            "structure_break_close_context":prior_break,
            "htf_4h_premium_discount_proxy":htf["position"],
            "htf_4h_fraction":htf["fraction"],
            "poc_in_gold_zone_proxy":poc_in_zone,
            "poc_price_approx":poc_price,
            "notes":"Confirmed opposite pivots; no BOS entry gate. Provisional swing selection."
        })
    truncated=len(signals)>max_signals
    return {"hypothesis":"confirmed_pivot_impulse_no_bos_v1",
            "status":"experimental_not_user_approved",
            "settings":{"pivot_span":pivot_span,"expiry_bars":expiry_bars,
                        "entry_level":entry_level,
                        "min_swing_fraction":min_swing_fraction,
                        "require_active_fvg":True,
                        "bos_required":False,
                        "liquidity_filter_approved":False},
            "signal_count":min(len(signals),max_signals),
            "truncated":truncated,"signals":signals[-max_signals:],
            "events":events[-max_signals:],"rejected":rejected,
            "warnings":[
                "Pivot-pair anchors are mechanical assumptions, not the user's validated RFM.",
                "FVG in Gold Zone is required; liquidity is measured but relevance threshold is not approved.",
                "A close past an earlier confirmed pivot is an optional BOS-like feature, not a BOS filter.",
                "4H premium/discount uses a provisional rolling range of completed 4H candles; informational only.",
                "An earlier Gold Zone touch is conservatively rejected to avoid retroactive pending orders.",
                "Only post-confirmation bars are eligible for execution; costs and BE are in execution.py.",
                "No historical survival, funding, actual exchange fills or independent edge validation."
            ]}
