# RFM Quant

Research-only crypto market data and backtest infrastructure. Developed for objective evaluation of the Fibonacci Retrace Model (RFM); **not** an automatic trading bot or evidence of profits.

**App:** https://rfm-quant.onrender.com  
**Fibonacci + POC lab:** https://rfm-quant.onrender.com/poc  
**API documentation:** https://rfm-quant.onrender.com/docs

## What you can do
- Inspect the current public OKX USDT/USDC swap catalog for the 31 requested tokens, including GRAM.
- Load up to 2,000 confirmed candles per historical query and inspect missing intervals, coverage and duplicates.
- Run a preliminary 90-day OHLC quality screening (not a certification of liquidity or fills).
- Find experimental BOS, three-candle FVG, SSL/BSL sweeps and CHoCH candidates, using only confirmed swings and candle closes.
- Select the Fibonacci starting candle and any historical as-of closed candle to calculate a dynamic fixed-range **POC proxy** (uniform OHLCV volume spread across high/low price bins). Users can enter confirmed bullish/bearish 0/100 anchors, see 67–75% Gold Zone and optional overlap with manually supplied FVG. This is **not** a true tick-based Volume Profile.
- Supply explicit closed-candle signals and candles to a conservative research execution simulator with commissions, slippage and risk sizing.
- From the POC laboratory, perform a **single manual scenario replay** from a chosen historical signal candle with Fib 67 or 75 as limit entry, 100 as stop and 0 as target. This is not an auto-signal backtest and may have hindsight bias in manually chosen Fibonacci anchors.

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
- `GET /api/research/fibonacci-levels?zero=82212.9&hundred=81141.4&side=long`
- `POST /api/research/poc` — supplied confirmed candles + Fib anchor timestamps; excludes any future bars
- `POST /api/research/simulate` — requires supplied candle data and explicit signals
- Legacy 100-candle endpoints remain for compatibility.

The simulator **does not** place orders. Funding fees, market depth, liquidations, taxes, and cross-bar intratrade drawdown are currently excluded. Live contract availability, backtest quality and regional eligibility are different questions.

## Deployment
The Render service is configured for Python using `pip install -r requirements.txt` and `uvicorn app:app --host 0.0.0.0 --port $PORT`. See [render.yaml](render.yaml). Code commits to GitHub do not themselves prove a deploy completed; check deployment status on Render.
\n## Manual replay assumptions (v0.10 beta)\nA single hypothetical order may be simulated after a user-selected historical candle. Default research parameters: 10,000 USDT fictitious equity, 1% intended risk, capped at 1x notional, fee 5 bps and slippage 2 bps per side, with 2R minimum before fees. The engine uses conservative stop-first resolution for candles touching both TP and SL, and does not assert trades can be filled at quoted prices. The scenario is not proof of a strategy edge.\n
## Experimental automatic candidate backtest (v0.11)
The `POST /api/research/candidate-backtest` endpoint and section 5 of `/poc` implement a deliberately provisional, deterministic pivot-breakout hypothesis. It identifies pivots only after `pivot_span` right-hand candles close, requires an opposing older pivot, then tests the break by candle close. It anchors 100% at the older opposing pivot, 0% at the best observed price extreme through the breakout candle, and offers 67%/75% limit entry. The 3-candle FVG-overlap filter can be toggled; POC, HTF alignment, CHoCH and liquidity sweep are NOT mandatory and are not yet part of candidate selection. The engine applies costs, stops and a maximum exposure cap. These rules are a new hypothesis, **not** the user's fully discretionary RFM.

Results are **in-sample exploratory statistics**, not an out-of-sample validation or claim of profitability. The optional seeded trade-level bootstrap resamples observed closed R multiples, requires at least 10 trades, assumes independence and cannot correct hindsight, parameter fitting, exchange survivorship, funding or liquidity biases. There is no live execution or account connection.

## v0.12 — one-page workflow
The default homepage has been redesigned around **Input → Model → Output → Strategy → Simulated Orders**. The user selects instrument, timeframe, history and Fib entry and clicks a single button. The UI retrieves confirmed OHLCV, generates experimental candidates, backtests them and shows understandable metrics and the simulated order ledger. Advanced research remains available separately at `/poc` and API docs at `/docs`.

This is an interface and workflow improvement, **not** evidence that the provisional pivot-breakout model matches the user's discretionary RFM or that it is profitable. No exchange credentials, live order submission or trading account integration are implemented.
