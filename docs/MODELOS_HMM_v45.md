# RFM Quant v45 — HMM regimes: findings (research only)

**12 Nov 2026.** Source, data, outputs and 18 passing tests are in the downloadable v45 research ZIP provided in the ChatGPT project conversation. This GitHub change is **documentation only**. It does not modify the API, website or Render deployment.

## Method

- BTC, ETH, SOL and ZEC, 1h bars assembled from 15m candles, Nov 2025–Oct 2026.
- 23,520 hourly targets across Mar–Oct 2026; each monthly fit uses the previous 90 days only.
- Causal *forward-filtered* Gaussian hidden Markov model, 2/3 states; features: hourly return, 4h momentum, rolling 24h volatility and volume ratio. **No smoothed future-state inference**.
- Three initializations per model (seeds 41, 43, 47), choose the model with highest **training-only** likelihood. Compare with simple trained volatility/trend rules, logistic regression, and historical prior. Target is next-hour positive return, **not RFM trade profit**.

## Results (out-of-training-month historical predictions)

| Model | Brier (lower better) | Direction accuracy |
|---|---:|---:|
| Simple vol/trend rules | **0.249886** | 51.38% |
| Logistic regression | 0.250018 | 51.72% |
| Historical training prior | 0.250160 | 49.25% |
| HMM 2 states (multistart) | 0.250177 | 49.67% |
| HMM 3 states (multistart) | 0.253286 | 49.26% |

5,000 synchronized weekly block resamples (36 UTC weeks): historical baseline Brier minus 2-state HMM = -0.000017, percentile 95% interval [-0.000208, +0.000168]; minus 3-state HMM = -0.003126, interval [-0.004632, -0.001853]. Exploratory intervals only; model selection and earlier historical exposure prevent formal validation claims.

18 automated tests passed locally: causality perturbation, month splits, posterior mass, reproducibility, metrics and bootstrap.

## Decision

**Do not integrate HMM into RFM entry logic.** The two-state variant has not demonstrated incremental predictive quality and the three-state variant has worse results. Market-directional accuracy does not equal RFM win rate. Only **2 RFM filtered trades are resolved** in the research set, so no RFM win-rate model or empirical Monte Carlo is defensible.

Next: unified causal feature store for the original RFM backtesting funnel, more verified resolved trade outcomes and genuinely unseen evaluation data. Volatility EWMA-15m remains research baseline; neither it nor logistic/HMM is an obligatory execution filter.

**Scope:** no trading orders or credentials; no app or backend code changes.
