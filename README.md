# RFM Quant

Research-only crypto market data and backtest infrastructure. Developed for objective evaluation of the Fibonacci Retrace Model (RFM); **not** an automatic trading bot or evidence of profits.

**App:** https://rfm-quant.onrender.com  
**API documentation:** https://rfm-quant.onrender.com/docs

## What you can do
- Inspect the current public OKX USDT/USDC swap catalog for the 31 requested tokens, including GRAM.
- Load up to 2,000 confirmed candles per historical query and inspect missing intervals, coverage and duplicates.
- Run a preliminary 90-day OHLC quality screening (not a certification of liquidity or fills).
- Find experimental BOS and three-candle FVG structure events on closed candles, without using future price action.
- Supply explicit closed-candle signals and candles to a conservative research execution simulator with commissions, slippage and risk sizing.

**No RFM auto-trade signals yet.** The user confirmed the Fibonacci orientation with bullish and bearish screenshots: entry 67–75%, protective side at 100%, target side at 0%. Theoretical RR is 2.03:1 at 67% and 3:1 at 75% before fees and stop buffers. See [methodology](docs/RFM_METHOD.md).

## Run locally

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
uvicorn app:app --reload
```

Browse http://127.0.0.1:8000 and /docs.

## Read-only endpoints
- `GET /health`
- `GET /api/watchlist`
- `GET /api/okx/universe` — current catalog, no past liquidity guarantee
- `GET /api/okx/history?inst_id=BTC-USDT-SWAP&bar=4H&bars=650`
- `GET /api/okx/coverage/BTC?bar=4H&bars=650&minimum_days=90`
- `GET /api/research/structure?inst_id=BTC-USDT-SWAP&bar=15m&bars=650`
- `GET /api/research/fibonacci-rr-check`
- `POST /api/research/simulate` — requires supplied candle data and explicit signals
- Legacy 100-candle endpoints remain for compatibility.

The simulator **does not** place orders. Funding fees, market depth, liquidations, taxes, and cross-bar intratrade drawdown are currently excluded. Live contract availability, backtest quality and regional eligibility are different questions.

## Deployment
The Render service is configured for Python using `pip install -r requirements.txt` and `uvicorn app:app --host 0.0.0.0 --port $PORT`. See [render.yaml](render.yaml). Code commits to GitHub do not themselves prove a deploy completed; check deployment status on Render.
