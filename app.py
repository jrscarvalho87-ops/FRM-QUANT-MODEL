"""RFM Quant read-only market-data API. No orders or trading credentials."""
from datetime import datetime, timezone
import re

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path
from data_quality import normalize_candles, gap_report
from market_audit import audit_sample
from history import fetch_history, INTERVAL_MS
from universe import catalog_status, screen_window
from execution import simulate
from structure import scan_structure
from fibonacci import levels as fib_levels
from volume_profile import approximate_poc
from rfm_candidates import generate_candidates

app = FastAPI(title="RFM Quant", version="0.11.0")
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

@app.get("/poc")
async def poc_lab():
    """Dedicated Fibonacci and dynamic POC research interface."""
    return FileResponse(Path(__file__).resolve().parent / "static" / "poc.html")


@app.get("/health")
async def health():
    return {"status":"ok","version":app.version,"timestamp_utc":datetime.now(timezone.utc).isoformat()}

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


def validate_swap_and_bar(inst_id: str, bar: str):
    if not re.fullmatch(r"[A-Z0-9]+-[A-Z0-9]+-SWAP", inst_id):
        raise HTTPException(status_code=400, detail="Expected OKX SWAP instrument ID")
    if bar not in INTERVAL_MS:
        raise HTTPException(status_code=400, detail="Unsupported timeframe")


@app.get("/api/okx/universe")
async def universe():
    """Current OKX instrument catalog; DOES NOT claim historical data validity."""
    catalog = await okx_get("/api/v5/public/instruments", {"instType":"SWAP"})
    results = catalog_status(catalog, WATCHLIST)
    return {"count":len(results), "available_usdt":sum(bool(r["usdt_swap"]) for r in results),
            "assets":results, "note":"Contract availability varies by region and account."}


@app.get("/api/okx/history")
async def history_endpoint(
    inst_id: str = Query("BTC-USDT-SWAP", min_length=7, max_length=40),
    bar: str = Query("4H"),
    bars: int = Query(600, ge=1, le=2000),
):
    validate_swap_and_bar(inst_id, bar)
    return await fetch_history(okx_get, inst_id, bar=bar, bars=bars)


@app.get("/api/okx/coverage/{symbol}")
async def coverage(
    symbol: str,
    bar: str = Query("4H"),
    bars: int = Query(650, ge=100, le=2000),
    minimum_days: float = Query(90.0, ge=1, le=365),
    quote: str = Query("USDT", pattern="^(USDT|USDC)$"),
):
    symbol = symbol.upper()
    if symbol not in WATCHLIST:
        raise HTTPException(status_code=404, detail="Symbol not in selected universe")
    inst_id = f"{symbol}-{quote}-SWAP"
    validate_swap_and_bar(inst_id, bar)
    catalog = await okx_get("/api/v5/public/instruments", {"instType":"SWAP"})
    available = {item["instId"] for item in catalog if item.get("state") == "live"}
    if inst_id not in available:
        return {"symbol":symbol,"instrument":inst_id,"status":"no_live_selected_swap",
                "warning":"Public catalog only. No historical coverage was checked."}
    h = await fetch_history(okx_get, inst_id, bar=bar, bars=bars)
    report = screen_window(h, minimum_days=minimum_days)
    return {"symbol":symbol,"instrument":inst_id,"quality":report,
            "oldest_ts":h["first_ts"],"newest_ts":h["last_ts"],
            "pages":h["pages_requested"],"history_exhausted":h["history_exhausted"]}


@app.get("/api/research/fibonacci-rr-check")
async def fibonacci_rr_check():
    """Arithmetic illustration of user-confirmed RFM orientation (before costs)."""
    return {"assumption":"RFM: 0% is target-side, 100% is stop-side; 67–75% are entry retracement levels.",
            "examples":[{"entry":75,"risk":25,"reward":75,"rr":3.0},
                        {"entry":67,"risk":33,"reward":67,"rr":round(67/33,4)}],
            "warning":"Theoretical RR before fees, slippage and any buffer beyond the 100% level. No algorithmic swing anchoring approved yet."}


@app.post("/api/research/simulate")
async def simulate_supplied_signals(body: dict):
    """OHLC + externally supplied signals. No order placement or invented RFM entries."""
    candles = body.get("candles")
    signals = body.get("signals")
    settings = body.get("settings", {})
    if not isinstance(candles,list) or not isinstance(signals,list) or not isinstance(settings,dict):
        raise HTTPException(status_code=400,detail="Provide candles[], signals[] and settings{}")
    if len(candles)>2000 or len(signals)>200:
        raise HTTPException(status_code=413,detail="Too many candles or signals")
    if not all(isinstance(row,dict) for row in candles+signals):
        raise HTTPException(status_code=400,detail="Candles and signals must be objects")
    allowed = {"initial_equity","risk_pct","fee_bps","slippage_bps",
               "max_exposure","min_rr","interval_ms","max_hold_bars"}
    if set(settings) - allowed:
        raise HTTPException(status_code=400,detail="Unknown simulation setting")
    try:
        return simulate(candles, signals, **settings)
    except (ValueError,TypeError,KeyError,OverflowError) as exc:
        raise HTTPException(status_code=400,detail="Invalid simulation inputs: " + str(exc)) from exc


@app.get("/api/research/structure")
async def structure_endpoint(
    inst_id: str = Query("BTC-USDT-SWAP",min_length=7,max_length=40),
    bar: str = Query("15m"),
    bars: int = Query(650,ge=100,le=2000),
    pivot_span: int = Query(3,ge=2,le=10),
):
    """Experimental confirmed BOS/FVG events, never trade recommendations."""
    validate_swap_and_bar(inst_id,bar)
    history_data = await fetch_history(okx_get,inst_id,bar=bar,bars=bars)
    if history_data["missing_intervals"] or history_data["rejected"]["malformed"]:
        raise HTTPException(status_code=422,detail="Structure requires continuous valid candles")
    result=scan_structure(history_data["candles"],pivot_span=pivot_span,max_events=30,interval_ms=INTERVAL_MS[bar])
    return {"instrument":inst_id,"bar":bar,"history_coverage_days":history_data["coverage_days"],
            **result}


@app.get("/api/research/fibonacci-levels")
async def fibonacci_levels(
    zero: float = Query(...,gt=0),
    hundred: float = Query(...,gt=0),
    side: str = Query(...,pattern="^(long|short)$"),
):
    """Compute chart levels only. Does not choose anchors or generate signals."""
    try:
        return fib_levels(zero,hundred,side)
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc


@app.post("/api/research/poc")
async def research_poc(body: dict):
    """OHLCV POC proxy over a dynamic, no-future Fib-anchored time window.

    Caller supplies candles already downloaded from the public API.
    Does not compute a true traded-volume-by-price profile.
    """
    candles = body.get("candles")
    if not isinstance(candles,list) or len(candles) > 2000:
        raise HTTPException(status_code=400,detail="Expected at most 2000 candles")
    if not all(isinstance(row,dict) for row in candles):
        raise HTTPException(status_code=400,detail="Candles must be objects")
    bar=body.get("bar","15m")
    if bar not in INTERVAL_MS:
        raise HTTPException(status_code=400,detail="Invalid bar")
    allowed={"candles","bar","anchor_ts","asof_ts","bins","zero_price","hundred_price","side"}
    if set(body) - allowed:
        raise HTTPException(status_code=400,detail="Unknown POC field")
    try:
        return approximate_poc(
            candles,body["anchor_ts"],body["asof_ts"],bins=body.get("bins",48),
            interval_ms=INTERVAL_MS[bar],zero_price=body.get("zero_price"),
            hundred_price=body.get("hundred_price"),side=body.get("side")
        )
    except (ValueError,TypeError,KeyError,OverflowError) as exc:
        raise HTTPException(status_code=400,detail="Invalid POC inputs: "+str(exc)) from exc


@app.post("/api/research/candidate-backtest")
async def candidate_backtest(body: dict):
    """Experimental pivot-breakout hypothesis, never user-approved RFM signals.

    Accepts only user-supplied confirmed OHLCV candles, no exchange orders.
    """
    candles=body.get("candles")
    settings=body.get("candidate_settings",{})
    execution_settings=body.get("execution_settings",{})
    if not isinstance(candles,list) or len(candles)>2000 or not all(isinstance(c,dict) for c in candles):
        raise HTTPException(status_code=400,detail="Expected up to 2000 candle objects")
    if not isinstance(settings,dict) or not isinstance(execution_settings,dict):
        raise HTTPException(status_code=400,detail="Expected candidate_settings and execution_settings objects")
    allowed={"pivot_span","expiry_bars","entry_level","require_fvg","min_swing_fraction","max_signals"}
    execution_allowed={"initial_equity","risk_pct","fee_bps","slippage_bps",
                       "max_exposure","min_rr","max_hold_bars"}
    if set(settings)-allowed or set(execution_settings)-execution_allowed:
        raise HTTPException(status_code=400,detail="Unsupported backtest setting")
    bar=body.get("bar","15m")
    if bar not in INTERVAL_MS:
        raise HTTPException(status_code=400,detail="Unsupported timeframe")
    if set(body)-{"candles","candidate_settings","execution_settings","bar"}:
        raise HTTPException(status_code=400,detail="Unsupported backtest field")
    try:
        candidates=generate_candidates(candles,interval_ms=INTERVAL_MS[bar],**settings)
        report=simulate(candles,candidates["signals"],interval_ms=INTERVAL_MS[bar],
                        **execution_settings)
        report["signal_source"]="experimental_confirmed_pivot_hypothesis"
        report["warnings"].append("This is NOT the user's fully specified RFM; it tests a provisional pivot-breakout interpretation.")
        return {"candidate_model":candidates,"execution":report,
                "warning":"Exploratory in-sample research only. No out-of-sample edge validated."}
    except (ValueError,TypeError,KeyError,OverflowError,ZeroDivisionError) as exc:
        raise HTTPException(status_code=400,detail="Invalid candidate backtest: "+str(exc)) from exc
