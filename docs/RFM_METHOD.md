# RFM Quant — specification log

## What is implemented (v0.8)
- Market universe: 31 requested assets, **including GRAM (not GRASS)**.
- Exact instrument matching against OKX's current public SWAP catalog; no guessed mappings.
- Confirmed 15m / 1H / 4H and other OHLCV candle collection, max 2,000 bars per request.
- Bounded backwards pagination, de-duplication, no filling missing candles.
- Quality screening for gaps, zero volume and abnormal bar ranges (heuristics, not liquidity approval).
- Experimental BOS detector based on pivots confirmed **only after** a right-hand window of closed bars.
- Experimental three-candle FVG detector, first known at the third candle's close.
- Execution simulator for **externally supplied** signals with next-bar entry eligibility, stop-first ambiguity, stop gaps, risk sizing, costs, and a cap on exposure.
- Win rate, expectancy in R, profit factor, closed-trade drawdown and sample trades.
- No trading credentials, live orders, predictions, or profit guarantees.

## RFM detection — pending precise rule agreement
We should NOT silently force a guessed trade signal from BOS/FVG events.
Known intent:
1. Context: 4H premium/discount, informational; 15m signal generation.
2. BOS counts only once its candle closes.
3. Bullish/bearish FVG is a three-candle gap and only exists at the third candle close.
4. A liquidity sweep and CHoCH can be evidence, but not every setup needs CHoCH.
5. Entry is intended around Fibonacci 67% or 75%, with the imbalance/FVG overlapping.
6. Stop and take profit on every trade; planned risk/reward at least 2:1.

### Fibonacci orientation confirmed from user screenshots (2026-11-10)
- Bullish: 0% at the upper swing extreme, 100% at the lower swing extreme. Buy on a retracement into 67–75%.
- Bearish: 100% at the upper swing extreme, 0% at the lower swing extreme. Sell on a retracement into 67–75%.
- Protective stop at/near 100% and target at/near 0%; the screenshots do not establish whether a buffer beyond 100% is mandatory.
- Reward/risk on a normalized 0-to-100 swing: entry 67 => reward 67, risk 33 => 2.0303R; entry 75 => reward 75, risk 25 => 3R. Fees, slippage, buffers and execution price can reduce these ratios.
- FVG/imbalance overlaps the retracement zone in the examples; BOS, CHoCH and liquidity sweeps are shown as context. User clarified on 2026-11-10 that BOS, CHoCH and liquidity sweep are NOT individually mandatory. Some discretionary entries use FVG within Gold Zone plus HTF alignment alone. CHoCH can replace BOS. Volume Profile is also consulted, but the exact signal rule (POC/VAH/VAL/HVN/LVN) is not specified. Do not treat it as mandatory until confirmed.
- The precise swing-selection/anchor algorithm and whether the first touch of 67 or 75 is used remain unresolved. These are necessary to prevent discretionary cherry-picking and future leakage.

## Data restrictions and audit
- Contract visibility is not proof of regional account eligibility.
- A 90-day 4H OHLC window may pass while 15m has missing candles or terrible spreads.
- Pairs must be screened against OHLC consistency and liquidity, including real spreads, order-book depth, fees and trading volume.
- Today's surviving coins are not the same as the historical universe (survivorship bias).
- Funding, liquidations, tick-level stop/TP ordering, partial fills, taxes, delistings, and market impact are **not modeled** yet.
- This simulator uses conservative stop-first sequencing when TP and SL both touch inside a single candle, excludes unresolved positions at sample end, and reports closed-trade drawdown only.
- Any result requires out-of-sample and walk-forward validation, realistic total costs, enough trades, and Monte Carlo robustness before any inference about edge.

## Planned next milestones
1. Test all components and confirm deployed HTTP endpoints and rendering.
2. Review Fibonacci anchor+stop with example TradingView screenshot.
3. Generate RFM candidate entries from confirmed structure, overlap with FVG and rule-based Fib levels; add explicit non-anticipation tests.
4. Extend dataset beyond the limited API and persist reproducible dataset snapshots.
5. Include funding, spreads and real contract specifications, realistic fill assumptions, out-of-sample splits, and parameter sensitivity.
6. Add statistical reports, reject weak assets, and run simulated paper-trading only.

The app is a research tool, not a broker or financial return generator.


## Confirmation logic clarification (2026-11-10)
The RFM is discretionary in its current form. The user sometimes trades with just a FVG inside the Gold Zone and HTF alignment; liquidity sweep is not always inspected, and CHoCH may replace BOS. Volume Profile is consulted exclusively via POC (Point of Control), not VAH or VAL. POC is optional confirmation; its calculation window and confluence distance remain unspecified.

**Research design:** record binary/typed features separately: `fvg_in_gold_zone`, `bos_direction`, `choch_direction`, `liquidity_sweep`, `alignment`, `volume_profile_context`. Do not conflate a missing condition with a failed setup. Define candidate families for stratified testing (e.g. Gold Zone + FVG + alignment; Gold Zone + FVG + alignment + CHoCH; with/without sweep) and compare their out-of-sample results after adequate sample sizes. Avoid fitting weights to the same data used for evaluation. The rules for choosing Fib anchors, FVG validity, POC calculation window and POC confluence tolerance remain to be specified before producing automatic trade signals.

## Volume Profile clarification (2026-11-10)
The user explicitly confirmed that only **POC** is used, never VAH or VAL. Treat POC as optional context, not a hard entry gate. A historical POC must be computed from data available at signal time; a POC derived from the full future sample would introduce look-ahead bias. Exact price-at-volume POC generally requires volume-at-price information or an explicit approximation method; do not label the highest-volume candle as a true POC.

## POC range rule confirmed (2026-11-10)
The user uses a manually anchored volume profile beginning at the candle where the Fibonacci is anchored, extending to the current analysis candle. For research, treat this as a dynamically extending fixed-range profile: start at the Fibonacci anchor candle, end at the most recently CLOSED candle as of the signal decision. Never use later candles when calculating historical POC. POC is optional confluence, not a mandatory entry criterion; VAH/VAL are not used. Exact volume-at-price requires granular data or a documented approximation, and binning/price proximity rules are not yet defined. The anchor-selection rule is also not yet fully mechanical.

## v0.9 implementation: POC lab and additional market events
- `/poc` is a browser-based, manual Fib anchor and historical decision-time lab. It loads confirmed OKX candles with date selection, long/short 0/100 levels, optional FVG bounds and optional user-provided 4H context.
- `POST /api/research/poc` spreads each confirmed candle's contract volume **uniformly** across its price range to form a discretized OHLCV proxy. This is **not** the real tick-level Volume Profile/TradingView POC.
- Profile window is exactly `anchor_ts` through `asof_ts` (both are candle OPEN timestamps). The output includes `known_after_close_ts`. Future bars are removed before binning. Gaps and unconfirmed endpoint candles are refused.
- POC exact-overlap with Gold Zone is a separate feature; no invented proximity threshold. FVG bounds supplied manually are not certified historical FVGs.
- Experimental SSL and BSL sweeps: wick beyond a previously confirmed swing, then candle close back across the swing level. One sweep per confirmed pivot. CHoCH candidates: confirmed direction break opposite to previous detected break. Both are **heuristics**, not mandatory entries or proof of edge.
- Automated RFM pivot selection remains unapproved; the manual anchors intentionally avoid claiming discretionary chart interpretations are fully objective.
