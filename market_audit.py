"""Conservative first-pass quality screening for confirmed OHLCV candles.

This is a SAMPLE screen, not proof that an instrument has years of history
or enough order-book depth for executable trading.
"""
from decimal import Decimal
from statistics import median
from data_quality import normalize_candles, gap_report


def audit_sample(raw, interval_ms=900000, min_bars=80, max_gap_fraction=0.01,
                 max_zero_volume_fraction=0.02, max_extreme_fraction=0.02,
                 extreme_range_fraction=0.15):
    rows, rejected = normalize_candles(raw)
    n = len(rows)
    gaps = gap_report(rows, interval_ms) if n else 0
    zero_vol = sum(Decimal(r["volume_contracts"]) == 0 for r in rows)
    extreme = sum(
        (Decimal(r["high"]) - Decimal(r["low"])) / Decimal(r["open"]) > Decimal(str(extreme_range_fraction))
        for r in rows
    )
    observed = max(1, n + gaps)
    gap_fraction = gaps / observed
    zero_fraction = zero_vol / n if n else 1.0
    extreme_fraction = extreme / n if n else 1.0
    ranges = [float((Decimal(r["high"]) - Decimal(r["low"])) / Decimal(r["open"])) for r in rows]
    reasons = []
    if n < min_bars:
        reasons.append("insufficient_sample")
    if gap_fraction > max_gap_fraction:
        reasons.append("missing_candles")
    if zero_fraction > max_zero_volume_fraction:
        reasons.append("zero_volume")
    if extreme_fraction > max_extreme_fraction:
        reasons.append("extreme_intrabar_ranges")
    if rejected["malformed"] or rejected["duplicate"]:
        reasons.append("invalid_or_duplicate_candles")
    return {
        "status": "sample_pass" if not reasons else "review",
        "reasons": reasons, "confirmed_bars": n, "missing_intervals": gaps,
        "gap_fraction": round(gap_fraction, 5),
        "zero_volume_fraction": round(zero_fraction, 5),
        "extreme_range_fraction": round(extreme_fraction, 5),
        "median_bar_range_fraction": round(median(ranges), 6) if ranges else None,
        "rejected": rejected,
        "warning": "Only a short recent sample; liquidity, spreads, history length, funding and contract availability still need separate verification."
    }
