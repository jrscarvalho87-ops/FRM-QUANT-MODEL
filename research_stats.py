"""Transparent, deterministic exploratory trade-level bootstrap diagnostics.

This is NOT market-path Monte Carlo. It resamples observed closed trades,
assumes iid trade outcomes, and cannot repair overfitting or selection bias.
"""
import random
import math


def bootstrap_r_multiples(trades, *, iterations=1000, seed=42):
    if not (100 <= iterations <= 5000 and isinstance(seed,int) and 0 <= seed <= 2**32-1):
        raise ValueError("Invalid bootstrap settings")
    values=[float(t["r_multiple"]) for t in trades]
    if not all(math.isfinite(v) for v in values):
        raise ValueError("Nonfinite R multiples")
    n=len(values)
    if n<10:
        return {"status":"insufficient_sample","observed_trades":n,
                "minimum_trades":10,"iterations":0,
                "warning":"At least 10 observed closed trades required for a diagnostic; 10 is still a very small sample."}
    rng=random.Random(seed)
    means=[]
    worst_streaks=[]
    for _ in range(iterations):
        sample=[values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample)/n)
        streak=0
        longest=0
        for r in sample:
            streak=streak+1 if r<0 else 0
            longest=max(longest,streak)
        worst_streaks.append(longest)
    means.sort()
    worst_streaks.sort()
    def pct(xs,p):
        return round(xs[min(len(xs)-1,max(0,int((len(xs)-1)*p)))],5)
    return {
        "status":"exploratory_bootstrap","observed_trades":n,
        "iterations":iterations,"seed":seed,
        "observed_mean_r":round(sum(values)/n,5),
        "mean_r_p05":pct(means,.05),"mean_r_median":pct(means,.5),
        "mean_r_p95":pct(means,.95),
        "prob_bootstrap_mean_r_below_zero":round(sum(x<0 for x in means)/iterations,4),
        "longest_loss_streak_p95":pct(worst_streaks,.95),
        "warnings":[
            "Trade-level iid bootstrap; NOT a simulation of market prices or order flow.",
            "Same in-sample trades are resampled; selection bias and overfitting remain.",
            "Results are not forecasts, probabilities of future profit or proof of edge."
        ]
    }
