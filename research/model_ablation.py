"""Predeclared, time-purged ML ablations on historical simulated RFM trades.

Diagnostic models, NOT a replacement for user-approved structural rules.
Single pooled BTC/ETH/SOL time axis, no event sharing between folds, purge
training trades whose exit was unknown at first test signal. All algorithms
see the SAME folds. Models cannot see user annotation decisions or future PnL.
"""
from math import isfinite

import numpy as np
import pandas as pd

BASE=(
    "side_long","swing_fraction","entry_level","hour_utc",
    "range_pct_12","return_12","volume_ratio_12",
)
STRUCTURE=(
    "pre_close_efficiency","pre_range_to_atr",
    "swing_close_efficiency","swing_largest_bar_share",
    "swing_peak_tr_to_pre_atr","swing_mean_tr_to_pre_atr",
    "interior_confirmed_pivots","interior_alternating_pivot_pairs",
    "swing_vs_prior_volume_ratio","signal_vs_previous_20_volume_ratio",
)
LIQUIDITY=(
    "liquidity_independent_unbreached_contextual_count",
    "liquidity_independent_external_above_count",
    "liquidity_independent_external_below_count",
    "liquidity_independent_contextual_types",
    "structure_break_close_context","htf_4h_fraction",
)
FEATURE_GROUPS={
    "basic_price":BASE,
    "price_plus_structure":BASE+STRUCTURE,
    "price_plus_structure_liquidity":BASE+STRUCTURE+LIQUIDITY,
}


def _metrics(prob,y):
    p=np.clip(np.asarray(prob,dtype=float),1e-6,1-1e-6)
    t=np.asarray(y,dtype=float)
    return {
        "brier":round(float(np.mean((p-t)**2)),6),
        "log_loss":round(float(np.mean(-t*np.log(p)-(1-t)*np.log(1-p))),6)
    }


def ablate_models(dataset, *, min_train=80, test_times=25, n_splits=4,
                  embargo_ms=900000, seed=20261111):
    """Evaluate fixed baselines + XGBoost + regularized logistic; no tuning.

    Tests are blocks of UNIQUE UTC signal timestamps. That avoids putting
    correlated simultaneous BTC/ETH/SOL signals in train and test.
    """
    from xgboost import XGBClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline

    if min_train<40 or test_times<10 or n_splits<1 or embargo_ms<0:
        raise ValueError("invalid chronological ML evaluation")
    required={"signal_ts","exit_ts","r_multiple","target_win","instrument"}|set(BASE)
    if not required.issubset(dataset.columns):
        raise ValueError("missing required time-safe ML fields: "+str(sorted(required-set(dataset.columns))))
    d=dataset.copy().sort_values(["signal_ts","instrument"],kind="stable").reset_index(drop=True)
    for field in ("signal_ts","exit_ts","r_multiple","target_win"):
        d[field]=pd.to_numeric(d[field],errors="raise")
        if not np.isfinite(d[field].to_numpy(dtype=float)).all():
            raise ValueError("non-finite ML label/time")
    if (d.exit_ts<d.signal_ts).any() or not d.target_win.isin([0,1]).all():
        raise ValueError("invalid future outcome dates or classes")
    if d.duplicated(subset=["signal_ts","instrument"]).any():
        raise ValueError("ambiguous same-instrument duplicate trade")
    if not set(FEATURE_GROUPS["price_plus_structure_liquidity"]).issubset(d.columns):
        return {
            "status":"missing_predeclared_features",
            "missing":sorted(set(FEATURE_GROUPS["price_plus_structure_liquidity"])-set(d.columns)),
            "trades":len(d),
            "warnings":["Do not silently replace omitted structural context with invented values."]
        }
    for key in FEATURE_GROUPS["price_plus_structure_liquidity"]:
        # This field is strictly 0/1 when present in the exported dataset.
        if key=="structure_break_close_context":
            d[key]=d[key].map({True:1,False:0,1:1,0:0,"True":1,"False":0})
        d[key]=pd.to_numeric(d[key],errors="coerce")
        if np.isinf(d[key].to_numpy(dtype=float)).any():
            raise ValueError("infinite feature: "+key)
    unique_times=np.sort(d.signal_ts.unique())
    positions=list(range(min_train,len(unique_times)-test_times+1,test_times))[-n_splits:]
    if not positions:
        return {"status":"insufficient_data","trades":len(d),"folds":[],
                "required_unique_signals":min_train+test_times}

    folds=[]
    for pos in positions:
        start=int(unique_times[pos])
        after=(int(unique_times[pos+test_times])
               if pos+test_times<len(unique_times) else None)
        test=d[(d.signal_ts>=start)&
               ((d.signal_ts<after) if after is not None else True)]
        train=d[(d.signal_ts<start)&(d.exit_ts<start-embargo_ms)]
        if len(train)<min_train or train.target_win.nunique()<2:
            folds.append({"status":"skipped","test_start_ts":start,
                          "reason":"insufficient purged completed training labels"})
            continue
        y=train.target_win.to_numpy(dtype=int)
        y_test=test.target_win.to_numpy(dtype=int)
        baseline=float(y.mean())
        row={
            "status":"evaluated","train_trades":len(train),"test_trades":len(test),
            "test_start_ts":start,
            "test_end_ts":int(test.signal_ts.max()),
            "last_training_exit_ts":int(train.exit_ts.max()),
            "embargo_ms":embargo_ms,
            "actual_test_mean_net_r":round(float(test.r_multiple.mean()),6),
            "constant_baseline":_metrics(np.full(len(test),baseline),y_test),
            "models":{},
        }
        if row["last_training_exit_ts"]>=start-embargo_ms:
            raise AssertionError("outcome leakage into test fold")
        for group,features in FEATURE_GROUPS.items():
            x_train=train[list(features)]
            x_test=test[list(features)]
            # Medians learned on train only. Missing contexts remain missing
            # until this per-fold training step, never imputed using the future.
            logistic=make_pipeline(
                SimpleImputer(strategy="median",keep_empty_features=True),
                StandardScaler(),
                LogisticRegression(max_iter=1000,random_state=seed))
            xgb=make_pipeline(
                SimpleImputer(strategy="median",keep_empty_features=True),
                XGBClassifier(n_estimators=100,max_depth=2,learning_rate=.05,
                              subsample=1.0,colsample_bytree=1.0,
                              objective="binary:logistic",eval_metric="logloss",
                              random_state=seed,n_jobs=1))
            logistic.fit(x_train,y)
            xgb.fit(x_train,y)
            row["models"][group]={
                "logistic":_metrics(logistic.predict_proba(x_test)[:,1],y_test),
                "xgboost":_metrics(xgb.predict_proba(x_test)[:,1],y_test),
                "feature_count":len(features),
            }
        folds.append(row)
    good=[f for f in folds if f["status"]=="evaluated"]
    if not good:
        return {"status":"insufficient_data","trades":len(d),"folds":folds}
    model_scores={}
    for group in FEATURE_GROUPS:
        model_scores[group]={}
        for algo in ("logistic","xgboost"):
            model_scores[group][algo]={
                metric:round(float(np.mean([
                    f["models"][group][algo][metric] for f in good])),6)
                for metric in ("brier","log_loss")
            }
    baseline_summary={
        metric:round(float(np.mean([f["constant_baseline"][metric]
                                    for f in good])),6)
        for metric in ("brier","log_loss")
    }
    return {
        "status":"exploratory_evaluated",
        "trades":len(d),"unique_signal_times":len(unique_times),
        "completed_folds":len(good),"folds":folds,
        "feature_sets":{k:list(v) for k,v in FEATURE_GROUPS.items()},
        "constant_baseline_mean":baseline_summary,
        "model_means":model_scores,
        "warnings":[
            "Previously inspected historical market window: these are NOT independent holdout results.",
            "Four human-reviewed setups are not used for ML training or outcome tuning.",
            "Only historically filled/closed simulator trades have outcomes: selection bias remains.",
            "All three feature sets use identical purged chronological test blocks, grouped by UTC timestamp.",
            "Training medians are fitted separately inside each fold; never calculated on future test data.",
            "Brier/log-loss calibration is not portfolio return; no model triggers live orders.",
            "Correlated crypto instruments and overlapping trades require a separate risk-aware portfolio simulator.",
            "Market-structure features and the Fibonacci pivot proxy remain unapproved approximations."
        ]
    }
