"""Candle validation for research. Never repair corrupt OHLC by guessing."""
from decimal import Decimal, InvalidOperation


def normalize_candles(raw):
    """Return chronological, confirmed, valid candles and rejection counters."""
    counters = {"unconfirmed": 0, "malformed": 0, "duplicate": 0}
    by_ts = {}
    for c in raw:
        try:
            if len(c) < 9:
                raise ValueError("short candle")
            if c[8] != "1":
                counters["unconfirmed"] += 1
                continue
            ts = int(c[0])
            if ts <= 0:
                raise ValueError("timestamp")
            o, h, l, close = (Decimal(str(x)) for x in c[1:5])
            vol = Decimal(str(c[5]))
            if not all(x.is_finite() for x in (o, h, l, close, vol)):
                raise ValueError("non-finite")
            if l <= 0 or o <= 0 or h <= 0 or close <= 0 or vol < 0:
                raise ValueError("negative or zero")
            if h < max(o, close, l) or l > min(o, close):
                raise ValueError("inconsistent OHLC")
            if ts in by_ts:
                counters["duplicate"] += 1
                continue
            by_ts[ts] = {"ts": ts, "open": str(o), "high": str(h), "low": str(l),
                         "close": str(close), "volume_contracts": str(vol),
                         "volume_base": str(c[6]), "volume_quote": str(c[7]),
                         "confirmed": True}
        except (ValueError, TypeError, IndexError, InvalidOperation):
            counters["malformed"] += 1
    return [by_ts[k] for k in sorted(by_ts)], counters


def gap_report(candles, interval_ms):
    """Count missing whole bar slots, without filling them."""
    if interval_ms <= 0:
        raise ValueError("interval_ms must be positive")
    missing = 0
    for left, right in zip(candles, candles[1:]):
        diff = right["ts"] - left["ts"]
        if diff > interval_ms:
            missing += max(0, (diff // interval_ms) - 1)
    return missing
