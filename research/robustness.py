"""Conservative moving-block bootstrap of observed NET R-multiples.

An empirical *resampling diagnostic*, never a future market forecast.
Block resampling retains limited adjacent-trade dependence. It does not
generate new OHLCV scenarios, repair sample selection, or validate a strategy.
"""
from math import isfinite
from random import Random


def block_bootstrap_r(trades, *, iterations=2000, block_length=5,
                      risk_fraction=0.01, seed=42, min_trades=30):
    if not (100<=iterations<=10000 and 1<=block_length<=50
            and 0<risk_fraction<=.05 and isinstance(seed,int)
            and 0<=seed<=2**32-1 and min_trades>=30):
        raise ValueError("invalid block bootstrap settings")
    values=[float(t["r_multiple"]) for t in trades]
    if any(not isfinite(x) for x in values):
        raise ValueError("non-finite trade outcome")
    n=len(values)
    if n<min_trades:
        return {"status":"insufficient_data","observed_trades":n,
                "min_trades":min_trades,
                "warnings":["No block-bootstrap probabilities from a tiny sample."]}
    if any(1+r*risk_fraction<=0 for r in values):
        raise ValueError("R multiple too negative for chosen compounding model")
    rng=Random(seed)
    terminal=[]
    dd=[]
    mean_r=[]
    for _ in range(iterations):
        path=[]
        while len(path)<n:
            start=rng.randrange(n)
            path.extend(values[(start+j)%n] for j in range(block_length))
        path=path[:n]
        equity=1.0
        high=1.0
        max_dd=0.0
        for r in path:
            equity*=1+r*risk_fraction
            high=max(high,equity)
            max_dd=max(max_dd,1-equity/high)
        terminal.append(100*(equity-1))
        dd.append(100*max_dd)
        mean_r.append(sum(path)/n)
    terminal.sort()
    dd.sort()
    mean_r.sort()
    def q(sorted_values,p):
        return round(sorted_values[int((len(sorted_values)-1)*p)],5)
    return {
        "status":"exploratory_moving_block_bootstrap",
        "observed_trades":n,"iterations":iterations,
        "seed":seed,"block_length":block_length,
        "risk_fraction":risk_fraction,
        "historical_mean_net_r":round(sum(values)/n,6),
        "mean_r_p05":q(mean_r,.05),"mean_r_p50":q(mean_r,.5),
        "mean_r_p95":q(mean_r,.95),
        "compounded_return_pct_p05":q(terminal,.05),
        "compounded_return_pct_p50":q(terminal,.5),
        "compounded_return_pct_p95":q(terminal,.95),
        "max_closed_trade_drawdown_pct_p50":q(dd,.5),
        "max_closed_trade_drawdown_pct_p95":q(dd,.95),
        "warnings":[
            "In-sample moving-block bootstrap is NOT a market-price simulation or future profit probability.",
            "Block resampling approximates short-range serial dependence but not volatility regimes or changing trade signals.",
            "Fixed 1% reference risk per observed net R and compounded closed-trade equity only.",
            "Trade entry selection, missing fills, funding, slippage variability, liquidations and overlapping signals are not re-simulated.",
            "Minimum 30 observations is only a reporting floor, not adequate proof of a profitable edge."
        ]
    }
