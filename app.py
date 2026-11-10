"""RFM Quant read-only market-data API. No orders or trading credentials."""
from datetime import datetime, timezone
import re

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path
from data_quality import normalize_candles, gap_report
from market_audit import audit_sample

app = FastAPI(title="RFM Quant", version="0.5.0")
OKX_BASE = "https://www.okx.com"
WATCHLIST = ["BTC","ETH","SOL","ZEC","XRP","BNB","RENDER","AVAX","ADA","TAO","NEAR","ONDO","PUMP","CRV","LTC","UNI","SUI","LINK","ENA","AERO","PEPE","DOGE","WIF","GRAM","AAVE","ARB","WLD","VIRTUALS","INJ","DOT","WLFI"]
BARS = {"1m","3m","5m","15m","30m","1H","2H","4H","6H","12H","1D","1Dutc"}

async def okx_get(path: str, params: dict):
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{OKX_BASE}{path}",params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502,detail=f"OKX data unavailable: {type(exc).__name__}") from exc
    if payload.get("code") != "0":
        raise HTTPException(status_code=502,detail={"source":"OKX","code":payload.get("code"),"message":payload.get("msg")})
    return payload.get("data",[])

@app.get("/")
async def home():
    return FileResponse(Path(__file__).resolve().parent / "static" / "index.html")

@app.get("/health")
async def health():
    return {"status":"ok","timestamp_utc":datetime.now(timezone.utc).isoformat()}

@app.get("/api/watchlist")
async def watchlist():
    return {"symbols":WATCHLIST,"count":len(WATCHLIST),"note":"Watchlist does not guarantee contract availability."}

@app.get("/api/okx/swaps")
async def swaps():
    instruments = await okx_get("/api/v5/public/instruments",{"instType":"SWAP"})
    selected = [i for i in instruments if i.get("instId","").split("-")[0] in WATCHLIST]
    return {"source":"OKX public API","instruments":selected,"count":len(selected)}

@app.get("/api/okx/candles")
async def candles(
    inst_id: str = Query("BTC-USDT-SWAP",min_length=7,max_length=40),
    bar: str = Query("15m"),
    limit: int = Query(100,ge=1,le=100),
    after: int | None = Query(None,ge=1),
):
    """One bounded page of historical OHLCV candles; after is an OKX millisecond cursor."""
    if not re.fullmatch(r"[A-Z0-9]+-[A-Z0-9]+-SWAP",inst_id):
        raise HTTPException(status_code=400,detail="Expected an OKX SWAP instrument ID")
    if bar not in BARS:
        raise HTTPException(status_code=400,detail="Unsupported bar")
    params = {"instId":inst_id,"bar":bar,"limit":str(limit)}
    if after is not None:
        params["after"] = str(after)
    data = await okx_get("/api/v5/market/history-candles",params)
    rows, rejected = normalize_candles(data)
    interval_ms = {"1m":60000,"3m":180000,"5m":300000,"15m":900000,
                   "30m":1800000,"1H":3600000,"2H":7200000,"4H":14400000,
                   "6H":21600000,"12H":43200000,"1D":86400000,"1Dutc":86400000}[bar]
    return {"instrument":inst_id,"bar":bar,"count":len(rows),"candles":rows,
            "oldest_ts":rows[0]["ts"] if rows else None,
            "newest_ts":rows[-1]["ts"] if rows else None,
            "rejected":rejected,"missing_intervals":gap_report(rows,interval_ms),
            "note":"Validated confirmed candles only. No interpolation; gap counts are within this page only. No backtest results."}

@app.get("/api/okx/audit/{symbol}")
async def audit_symbol(symbol: str):
    """Audit a recent 100-bar 15m sample; not full historical certification."""
    symbol = symbol.upper()
    if symbol not in WATCHLIST:
        raise HTTPException(status_code=404, detail="Symbol not on watchlist")
    instruments = await okx_get("/api/v5/public/instruments",{"instType":"SWAP"})
    ids = {i.get("instId") for i in instruments if i.get("state") == "live"}
    inst_id = f"{symbol}-USDT-SWAP"
    if inst_id not in ids:
        return {"symbol":symbol,"instrument":inst_id,"status":"unavailable",
                "reason":"No live USDT SWAP contract in OKX public instrument catalog"}
    raw = await okx_get("/api/v5/market/history-candles",
                        {"instId":inst_id,"bar":"15m","limit":"100"})
    return {"symbol":symbol,"instrument":inst_id,"sample":audit_sample(raw)}
