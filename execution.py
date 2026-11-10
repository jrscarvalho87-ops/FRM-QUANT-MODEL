"""Deterministic, single-position research backtester for *supplied* trade signals.

This is an execution engine, NOT the RFM signal generator. No live orders.
A signal becomes eligible strictly after its candle has closed. Both exits
touched in one bar => stop first; data gaps invalidate unresolved trades.
"""
import math


def simulate(candles, signals, *, initial_equity=10_000.0, risk_pct=1.0,
             fee_bps=5.0, slippage_bps=2.0, max_exposure=1.0,
             min_rr=2.0, interval_ms=900_000, max_hold_bars=96):
    if not (initial_equity > 0 and 0 < risk_pct <= 5 and 0 <= fee_bps <= 100
            and 0 <= slippage_bps <= 100 and 0 < max_exposure <= 5
            and min_rr >= 0 and interval_ms > 0 and max_hold_bars >= 1):
        raise ValueError("invalid simulation settings")

    bars = list(candles)
    times = [int(b["ts"]) for b in bars]
    if times != sorted(set(times)):
        raise ValueError("candles must be unique and chronological")
    for b in bars:
        o, h, l, c = (float(b[k]) for k in ("open", "high", "low", "close"))
        if not all(math.isfinite(v) for v in (o,h,l,c)) or min(o,h,l,c) <= 0 or h < max(o,c,l) or l > min(o,c):
            raise ValueError("invalid OHLC candle")
        if b.get("confirmed") is not True:
            raise ValueError("unconfirmed candles cannot be backtested")

    index_by_ts = {t:i for i,t in enumerate(times)}
    equity = float(initial_equity)
    high_water = equity
    max_drawdown = 0.0
    locked_until = -1
    trades = []
    skipped = {}

    def skip(reason):
        skipped[reason] = skipped.get(reason, 0) + 1

    for sig in sorted(signals, key=lambda s:int(s["signal_ts"])):
        sig_time = int(sig["signal_ts"])
        at = index_by_ts.get(sig_time)
        if at is None:
            skip("signal_not_in_data")
            continue
        if at <= locked_until:
            skip("overlapping_signal")
            continue
        try:
            side = sig["side"]
            entry, stop, take = (float(sig[k]) for k in ("entry","stop","take"))
            ttl = int(sig.get("expiry_bars", 8))
            if side not in ("long","short") or not 1 <= ttl <= 96:
                raise ValueError("invalid direction or expiry")
            if not all(math.isfinite(x) and x > 0 for x in (entry,stop,take)):
                raise ValueError("nonfinite prices")
            direction = 1 if side == "long" else -1
            risk_per_unit = direction * (entry - stop)
            reward_per_unit = direction * (take - entry)
            if risk_per_unit <= 0 or reward_per_unit <= 0:
                raise ValueError("invalid stop/take direction")
            planned_rr = reward_per_unit / risk_per_unit
        except (KeyError,ValueError,TypeError,OverflowError,ZeroDivisionError):
            skip("invalid_signal")
            continue
        if planned_rr + 1e-10 < min_rr:
            skip("rr_below_minimum")
            continue

        fill_index = None
        price = None
        invalid_gap = False
        for j in range(at + 1, min(len(bars),at + 1 + ttl)):
            if times[j] - times[j-1] != interval_ms:
                invalid_gap = True
                break
            o, h, l = (float(bars[j][k]) for k in ("open","high","low"))
            if (side == "long" and l <= entry) or (side == "short" and h >= entry):
                fill_index = j
                price = min(o,entry) if side == "long" else max(o,entry)
                break
        if invalid_gap:
            skip("data_gap")
            continue
        if fill_index is None:
            skip("entry_not_filled")
            continue

        slip = slippage_bps / 10_000
        fee = fee_bps / 10_000
        entry_ex = price * (1 + direction * slip)
        stop_ex = stop * (1 - direction * slip)
        stop_risk = direction * (entry_ex - stop_ex)
        if stop_risk <= 0:
            skip("invalid_execution_risk")
            continue
        allocated_risk = equity * risk_pct / 100
        unit_risk_with_costs = stop_risk + fee * (entry_ex + stop_ex)
        units = min(allocated_risk / unit_risk_with_costs,
                    equity * max_exposure / entry_ex)
        if units <= 0:
            skip("zero_size")
            continue

        exit_index = None
        exit_price = None
        reason = None
        for j in range(fill_index, min(len(bars),fill_index + max_hold_bars)):
            if j > fill_index and times[j] - times[j-1] != interval_ms:
                reason = "data_gap"
                break
            b = bars[j]
            o, h, l, c = (float(b[k]) for k in ("open","high","low","close"))
            if direction == 1:
                if o <= stop:
                    exit_price, reason = o, "gap_stop"
                elif o >= take:
                    exit_price, reason = take, "take_profit"
                elif l <= stop:
                    exit_price, reason = stop, "stop_loss"
                elif h >= take:
                    exit_price, reason = take, "take_profit"
            else:
                if o >= stop:
                    exit_price, reason = o, "gap_stop"
                elif o <= take:
                    exit_price, reason = take, "take_profit"
                elif h >= stop:
                    exit_price, reason = stop, "stop_loss"
                elif l <= take:
                    exit_price, reason = take, "take_profit"
            if reason:
                exit_index = j
                break
            if j == fill_index + max_hold_bars - 1:
                exit_index, exit_price, reason = j, c, "time_exit"
                break
        if reason == "data_gap":
            skip("data_gap")
            locked_until = max(locked_until, j)
            continue
        if exit_index is None:
            skip("open_at_sample_end")
            locked_until = len(bars) - 1
            continue

        exit_ex = exit_price * (1 - direction * slip)
        net = direction * (exit_ex - entry_ex) * units - (entry_ex + exit_ex) * units * fee
        before = equity
        equity += net
        high_water = max(high_water, equity)
        max_drawdown = max(max_drawdown, (high_water - equity) / high_water)
        locked_until = exit_index
        trades.append({
            "side": side, "signal_ts": sig_time,
            "entry_ts": times[fill_index], "exit_ts": times[exit_index],
            "entry_price": round(entry_ex, 10), "exit_price": round(exit_ex, 10),
            "stop_price": stop, "take_price": take,
            "planned_rr": round(planned_rr, 4),
            "quantity": round(units, 8), "pnl": round(net, 6),
            "r_multiple": round(net / allocated_risk, 6),
            "equity_before": round(before, 6), "equity_after": round(equity, 6),
            "exit_reason": reason,
        })
    wins = [t["pnl"] for t in trades if t["pnl"] > 0]
    losses = [t["pnl"] for t in trades if t["pnl"] < 0]
    gross_profit = sum(wins)
    gross_loss = -sum(losses)
    return {
        "mode": "research_only", "signal_source": "supplied_externally",
        "settings": {"initial_equity": initial_equity, "risk_pct": risk_pct,
                     "fee_bps_per_side": fee_bps, "slippage_bps_per_side": slippage_bps,
                     "max_exposure": max_exposure, "min_rr": min_rr,
                     "max_hold_bars": max_hold_bars},
        "summary": {
            "signals_received": len(signals), "closed_trades": len(trades),
            "skipped": skipped, "win_rate_pct": round(100*len(wins)/len(trades),2) if trades else None,
            "profit_factor": round(gross_profit/gross_loss,3) if gross_loss else None,
            "profit_factor_unbounded": bool(trades and not gross_loss),
            "expectancy_r": round(sum(t["r_multiple"] for t in trades)/len(trades),4) if trades else None,
            "ending_equity": round(equity,4),
            "net_return_pct": round((equity / initial_equity - 1)*100,4),
            "max_closed_trade_drawdown_pct": round(max_drawdown*100,4),
        },
        "trades": trades,
        "warnings": [
            "No funding costs, liquidations, order-book depth, partial fills or taxes.",
            "Within-bar ambiguity is resolved stop-first; gaps can exceed targeted risk.",
            "Max drawdown is measured on closed-trade equity, not intratrade mark-to-market.",
            "This engine does NOT identify RFM setups or demonstrate an edge."
        ],
    }
