# RFM Quant v46 — Causal integration and RFM candidate execution audit

**Research-only | 12 November 2026.** This GitHub change documents a reproducible local integration. It does **not** change the deployed app, API, or trading execution.

## Sources
- v38: 233 provisional Fibonacci/FVG setup candidates, filtered trade ledger and outcomes.
- v43/v44: market regime classification and temporally validated 15-minute price-direction predictions.
- v45: causal 1-hour HMM and logistic benchmarks, with multiple initializations.
- Original 15-minute OHLCV history: 35,040 bars per BTC/ETH/SOL/ZEC asset.

## Exact reconciliation

| Market | Candidate setups | Filter-eligible | Resolved trades |
|---|---:|---:|---:|
| BTCUSDT | 20 | 5 | 1 |
| ETHUSDT | 29 | 2 | 0 |
| SOLUSDT | 29 | 2 | 1 |
| ZECUSDT | 155 | 5 | 0 |
| **Total** | **233** | **14** | **2** |

Filtered ledger statuses for the 14 eligible candidates: 5 `CANCEL_ZERO`, 5 `CANCEL_CONTEXT`, 1 `SKIPPED_OVERLAP`, 1 `AMBIGUOUS_ENTRY_BE`, 1 `TP`, 1 `SL`. The two resolved trades return +1.906621R and −1.104910R, sum +0.801711R; **this cannot establish an edge**.

All four market filtered operation ledgers reconcile with the feature store. **Important key fix:** `context_id` alone is not unique; joins use asset, context ID and signal timestamp.

## Model-forecast join
- Match 15m logistic forecast at the candidate's signal timestamp. Prediction is computed using closed bars up to signal −15m.
- Match 1h HMM forecast for the current UTC hour only if it was produced at the *start* of the hour and no more than 59m45s before the candidate signal. No target-hour outcome is imported.
- Recompute 4h context using only the preceding *completed* 4h candle. Future-bar perturbation test passes.
- 123/233 candidates and 12/14 eligible candidates have recorded forecast series. Only **one of the two resolved eligible trades** has a forecast (prior to March 2026, there was no recorded walk-forward prediction).
- Trade outcome labels remain missing for 231/233 candidate setups. The model predicts **market direction**, not probability that a setup hits its TP before SL.

## Verification
- **20/20** local integration/causality tests passed.
- Standalone v46 ZIP includes extraction of only the required v38, v43, v45 inputs, source-code auditor, tests, SHA-256 manifest, CSVs, and a technical report.
- Verified a fresh ZIP extraction reproduces the candidate table **byte-for-byte**.
- No trading-success model has been trained: 2 resolved outcomes are insufficient; no historical RFM win-rate estimate is defensible.

## v47 priorities
Audit 10 cancellations, ambiguous intrabar sequence, blocked overlapping order, and faithful RFM entry/SL/TP/BE rule representation; collect genuinely new labels without changing historical filters to inflate win rate. Hold off on empirical Monte Carlo until enough resolved trades and realistic cost uncertainty exist.

**Scope:** This is a documentation update only; the package's executable code has not been pushed here. Keep the draft PR separate from main/Render deployment pending review.
