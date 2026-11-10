"""RFM Quant read-only market-data API. No orders or trading credentials."""
from datetime import datetime, timezone
import re

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI(title="RFM Quant", version="0.3.0")
OKX_BASE = "https://www.okx.com"
WATCHLIST = ["BTC","ETH","SOL","BNB","ZEC","HYPE","XRP","ENA","TAO","NEAR","RENDER","ONDO","PUMP","INJ","AVAX","ADA","PEPE","SUI","LINK","SEI","DOGE","BCH","LTC","TRX","WLD","AAVE","UNI","XLM","ARB","OP"]
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
    rows = []
    for c in data:
        if len(c) < 9:
            continue
        rows.append({"ts":int(c[0]),"open":c[1],"high":c[2],"low":c[3],
                     "close":c[4],"volume_contracts":c[5],"volume_base":c[6],
                     "volume_quote":c[7],"confirmed":c[8] == "1"})
    rows.sort(key=lambda r:r["ts"])
    return {"instrument":inst_id,"bar":bar,"count":len(rows),"candles":rows,
            "oldest_ts":rows[0]["ts"] if rows else None,
            "newest_ts":rows[-1]["ts"] if rows else None,
            "note":"Raw market data, not backtest results. Exclude unconfirmed candles from signals."}
