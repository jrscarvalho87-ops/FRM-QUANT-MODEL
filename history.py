"""Bounded OKX history pagination: candle data only, no credentials or orders.

OKX's 'after' parameter requests older candles than the supplied timestamp.
Pages are de-duplicated, sorted chronologically, and never forward-filled.
"""
import asyncio
from data_quality import normalize_candles, gap_report

INTERVAL_MS = {
    "1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000,
    "30m": 1_800_000, "1H": 3_600_000, "2H": 7_200_000,
    "4H": 14_400_000, "6H": 21_600_000, "12H": 43_200_000,
    "1D": 86_400_000, "1Dutc": 86_400_000,
}


async def fetch_history(fetch_page, inst_id, bar="15m", bars=600, page_size=100):
    """Fetch <= 2,000 requested confirmed bars; returns data quality metadata.

    fetch_page(path, params) is an async function; this separation allows offline tests.
    The endpoint can return fewer bars than requested if OKX has less history.
    """
    if not (1 <= bars <= 2000):
        raise ValueError("bars must be between 1 and 2000")
    if bar not in INTERVAL_MS:
        raise ValueError("unsupported timeframe")
    if not (1 <= page_size <= 100):
        raise ValueError("page_size must be between 1 and 100")
    all_rows = []
    cursor = None
    seen_cursors = set()
    pages = 0
    exhausted = False
    while pages < (bars + page_size - 1) // page_size + 2:
        params = {"instId": inst_id, "bar": bar, "limit": str(page_size)}
        if cursor is not None:
            params["after"] = str(cursor)
        page = await fetch_page("/api/v5/market/history-candles", params)
        pages += 1
        if not page:
            exhausted = True
            break
        all_rows.extend(page)
        timestamps = []
        for c in page:
            try:
                timestamps.append(int(c[0]))
            except (TypeError, ValueError, IndexError):
                continue
        if not timestamps:
            exhausted = True
            break
        oldest = min(timestamps)
        if oldest in seen_cursors or (cursor is not None and oldest >= cursor):
            exhausted = True
            break
        seen_cursors.add(oldest)
        cursor = oldest
        rows_so_far, _ = normalize_candles(all_rows)
        if len(rows_so_far) >= bars:
            break
        if len(page) < page_size:
            exhausted = True
            break
        await asyncio.sleep(0.15)

    all_confirmed, rejected = normalize_candles(all_rows)
    rows = all_confirmed[-bars:]
    n = len(rows)
    missing = gap_report(rows, INTERVAL_MS[bar])
    return {
        "instrument": inst_id, "bar": bar, "requested_bars": bars,
        "returned_bars": n, "pages_requested": pages,
        "history_exhausted": exhausted, "missing_intervals": missing,
        "gap_fraction": round(missing / (n + missing), 6) if n + missing else None,
        "first_ts": rows[0]["ts"] if rows else None,
        "last_ts": rows[-1]["ts"] if rows else None,
        "coverage_days": round((rows[-1]["ts"] - rows[0]["ts"]) / 86_400_000, 2) if n > 1 else 0,
        "rejected": rejected, "candles": rows,
        "warnings": [
            "Data are public OKX candles, not a full quality or execution certification.",
            "Only confirmed candles; missing intervals are not interpolated.",
            "Funding, spread, order-book depth, delistings and historical survivorship bias are not included."
        ],
    }
