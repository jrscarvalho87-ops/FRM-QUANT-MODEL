"""Instrument catalog interpretation and longer-window OHLC quality screening."""
from decimal import Decimal
from statistics import median
from history import INTERVAL_MS


def catalog_status(instruments, symbols):
    """Do not substitute similarly named tokens or invent contracts."""
    by_base = {}
    for inst in instruments:
        inst_id = inst.get("instId", "")
        pieces = inst_id.split("-")
        if len(pieces) != 3 or pieces[2] != "SWAP":
            continue
        by_base.setdefault(pieces[0], []).append(inst)
    result = []
    for symbol in symbols:
        variants = by_base.get(symbol, [])
        live = [v for v in variants if v.get("state") == "live"]
        usdt = next((v for v in live if v["instId"] == f"{symbol}-USDT-SWAP"), None)
        usdc = next((v for v in live if v["instId"] == f"{symbol}-USDC-SWAP"), None)
        result.append({
            "symbol": symbol,
            "usdt_swap": usdt["instId"] if usdt else None,
            "usdc_swap": usdc["instId"] if usdc else None,
            "other_swap_ids": [v["instId"] for v in live if v not in (usdt, usdc)],
            "status": "usdt_swap_available" if usdt else (
                "usdc_swap_available" if usdc else "not_in_public_usdt_usdc_swap_catalog"),
            "history_verified": False, "liquidity_verified": False,
        })
    return result


def screen_window(history, minimum_days=90.0, max_gaps=0.005,
                  max_zero_volume=0.01, max_extreme_fraction=0.02):
    """Review window integrity; NOT endorsement for real trading."""
    candles = history["candles"]
    n = len(candles)
    bar = history["bar"]
    if bar not in INTERVAL_MS:
        raise ValueError("unsupported bar")
    days = history["coverage_days"]
    missing = history["missing_intervals"]
    gap_fraction = history["gap_fraction"] if history["gap_fraction"] is not None else 1.0
    zero_vol = sum(Decimal(row["volume_contracts"]) == 0 for row in candles)
    max_bar_range = 0.15 if INTERVAL_MS[bar] <= INTERVAL_MS["15m"] else 0.30
    extreme = sum(
        (Decimal(row["high"]) - Decimal(row["low"])) / Decimal(row["open"]) > Decimal(str(max_bar_range))
        for row in candles
    )
    zero_fraction = zero_vol / n if n else 1.0
    extreme_fraction = extreme / n if n else 1.0
    median_range = median(
        (float((Decimal(c["high"]) - Decimal(c["low"])) / Decimal(c["open"])) for c in candles)
    ) if n else None
    flags = []
    if days < minimum_days:
        flags.append("insufficient_lookback_days")
    if gap_fraction > max_gaps:
        flags.append("missing_candles")
    if zero_fraction > max_zero_volume:
        flags.append("zero_volume_candles")
    if extreme_fraction > max_extreme_fraction:
        flags.append("unusually_wide_candles")
    if history["rejected"]["malformed"]:
        flags.append("malformed_candles")
    if history["rejected"]["duplicate"]:
        flags.append("duplicate_candles")
    return {
        "status": "window_quality_pass" if not flags else "review_required",
        "flags": flags,
        "bar": bar, "bars_checked": n, "coverage_days": days,
        "required_days": minimum_days, "missing_intervals": missing,
        "gap_fraction": gap_fraction, "zero_volume_fraction": round(zero_fraction,5),
        "extreme_range_fraction": round(extreme_fraction,5),
        "median_range_fraction": round(median_range,6) if median_range is not None else None,
        "max_range_threshold_fraction": max_bar_range,
        "spread_checked": False, "funding_checked": False, "order_book_checked": False,
        "interpretation": "OHLC data screening only. Passing does NOT imply executable strategy, stable liquidity, or predictive edge.",
    }
