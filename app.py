"""RFM Quant: read-only market-data API starter. No orders or trading credentials."""
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
import httpx

app = FastAPI(title="RFM Quant", version="0.1.0")
OKX_BASE = "https://www.okx.com"
WATCHLIST = ["BTC","ETH","SOL","BNB","ZEC","HYPE","XRP","ENA","TAO","NEAR","RENDER","ONDO","PUMP","INJ","AVAX","ADA","PEPE","SUI","LINK","SEI","DOGE","BCH","LTC","TRX","WLD","AAVE","UNI","XLM","ARB","OP"]

@app.get("/")
async def home():
    return {"project":"RFM Quant","status":"starter","mode":"research_only","docs":"/docs"}

@app.get("/health")
async def health():
    return {"status":"ok","timestamp_utc":datetime.now(timezone.utc).isoformat()}

@app.get("/api/watchlist")
async def watchlist():
    return {"symbols":WATCHLIST,"count":len(WATCHLIST),"note":"Requested assets; not all contracts are guaranteed to exist."}

@app.get("/api/okx/swaps")
async def swaps():
    """Fetch current live instrument metadata, not historic availability."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(f"{OKX_BASE}/api/v5/public/instruments",params={"instType":"SWAP"})
            response.raise_for_status()
            payload = response.json()
        if payload.get("code") != "0":
            raise HTTPException(status_code=502,detail="OKX returned an error")
        instruments = payload.get("data",[])
        selected = [i for i in instruments if i.get("baseCcy") in WATCHLIST or i.get("instId","").split("-")[0] in WATCHLIST]
        return {"source":"OKX public API","instruments":selected,"count":len(selected)}
    except (httpx.HTTPError,ValueError) as exc:
        raise HTTPException(status_code=502,detail=f"OKX data unavailable: {type(exc).__name__}") from exc
