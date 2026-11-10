# RFM Quant — Quantitative research plan (v1)

## Research objective
**Input → Model → Output → Strategy → Simulated Orders.**
Input: confirmed historical OHLCV, timestamps and instrument metadata.
Model: compute only signal-time-available features (structure, FVG, swing, volatility, volume).
Output: candidate setup and optional predicted probability of positive net R.
Strategy: user-confirmed Fibonacci Gold Zone 67–75%, stop at 100%, target at 0%; optional confluences. Precise automated swing selection remains a **provisional pivot-breakout hypothesis**.
Orders: backtesting only, no exchange order API or account access.

## RFM rules currently supported by the user
- Long: Fibonacci 0% at the upper extreme and 100% at the lower extreme. Short: reverse.
- Entry within 67–75% Gold Zone, stop around 100%, target around 0%.
- FVG/imbalance, BOS or CHoCH, liquidity sweep and 4H premium/discount provide context, but none should be silently made mandatory across all setups.
- POC is optional and uses the range from the Fibonacci anchor candle to the last closed decision candle. Current OHLCV POC is an **approximation**, not true traded volume by price.
- Exact swing anchor selection, entry policy within the zone, stop buffer, FVG mitigation and objective confluence weights are not fully confirmed.

## What the quantitative code actually does
- `research/export_research.py` fetches public historical candles from the deployed read-only API, runs the provisional candidate generator and conservative order simulator, saves candles/events/trades as CSV, and then invokes Pandas/NumPy/XGBoost research when trades exist.
- `research/quant_pipeline.py` builds time-safe features from candles up to each signal close, labels only executed/closed trades, and evaluates XGBoost with expanding chronological folds. **Training labels must be known (trade exit before test signal).**
- A simple baseline win probability is scored against XGBoost using Brier score. Better Brier score is NOT proof of profit or of a useful trading filter.
- If fewer than 105 labelled closed trades exist at defaults, the walk-forward returns insufficient data. No invented win rate, accuracy or trading performance.
- No tuning on the test folds, no predictions from future candles, no deployment of ML signals to trading.
- OHLCV max 2,000 bars per fetch is not sufficient to claim robust historical generalization; multiple archived, non-overlapping periods and historically representative instruments are needed.

## Reproducible run
```bash
pip install -r requirements-research.txt
python -m research.export_research --symbol BTC-USDT-SWAP --bar 15m --bars 2000
jupyter lab notebooks/01_rfm_quant_research.ipynb
```
The research export produces `research_outputs/BTC-USDT-SWAP/15m/{candles,events,trades,report}.csv/json` where available. No performance numbers are prefilled.

## Next validation gates
1. Agree on objective swing anchoring and entry rules using the user's annotated historical screenshots.
2. Audit simulator fill behavior, fees, funding and exchange instrument sizing.
3. Gather long-duration timestamped datasets with continuity checks and preserved snapshots.
4. Backtest the frozen strategy across multiple markets and regimes.
5. Use untouched chronological holdouts and walk-forward evaluation; report uncertainty and parameter sensitivity.
6. Only consider paper trading after independent validation. Never auto-submit real orders from the research environment.
