# RFM Quant v47 — More valid trade observations (research only)

**2026-11-12, BTC/ETH/SOL/ZEC USD-M, Nov 2025–Oct 2026, 15m.** Does not place orders or establish profitability. Reconciled all four original v38 filtered ledgers without discrepancy.

## Three noninterchangeable research policies

| Scenario | Eligible candidates | Closed outcomes TP/SL/BE | TP | SL | BE | Sum net R (resolved only) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Original v38: pending order expires on context transition | 14 | 2 | 1 | 1 | 0 | +0.801711 |
| A: **no context-based expiry** (original triggers, cost and BE maintained) | 14 | 6 | 2 | 4 | 0 | **-0.384518** |
| B: A plus **experimental** Asian High/Low (00:00–08:00 UTC) | 20 | 8 | 2 | 5 | 1 | **-1.707851** |

Hypothetical execution costs: fee 5bps **each side** and stop slippage 2bps; 15m OHLC can leave intrabar paths unresolved. These figures are not a win-rate estimate, and all original exit/position constraints remain approximate.

## Main bottleneck

From 233 Fib/FVG candidates: **14 valid named sweeps**, **202 have zero raw named sweeps in the 4-hour window**, **17 have sweeps that were invalidated** by a later close past the reference. Of 219 sweep rejects, 211 had an otherwise valid structural trigger. Current experimental level family includes PDH/PDL, PWH/PWL, EQH/EQL; **Asian High/Low was missing**.

The isolated Asian level hypothesis uses the 00:00–08:00 UTC range only *after* session close, detects first wick sweep with close back in range, enforces direction and four-hour lookback, and rejects levels invalidated by later closes. **This specific session convention has not been approved by the strategy owner and was not chosen to improve in-sample returns.** It creates six additional confluence candidates, two additional closed outcomes (one loss and one gross-BE), and historical performance becomes worse, not better.

## Decisions

- No claim of a 60–70% win rate; sample size remains critically insufficient.
- Do not remove sweep/trigger requirements or select a session window based on win rate.
- A is an audit of the user-stated no-arbitrary-expiry logic, not proof of faithful execution: the model still uses a provisional 2% reversal threshold, and 67% fib SL always equals anchor 100%.
- Keep the original filtered engine and published app unchanged; the local v47 research package has **22 passing automated tests**, source OHLCV, all candidate/execution ledgers, and a checksum-verified historical backfill helper.
- **Next genuinely useful input:** 2024-11 through 2025-10 Binance USD-M historical 15m files, to extend the same four markets to 24 months. A Windows one-click Python downloader with monthly official SHA-256 validation is provided locally; no external downloads were completed from the execution environment. New samples should be held out from parameter selection.

This commit contains **documentation only**, not the source scripts or data, and should remain a draft PR until code review. No deployment, trade execution, account or exchange integration is authorized.
