"""Time-safe RFM research with Pandas, NumPy and walk-forward XGBoost.

A SECONDARY classifier of historical executed RFM candidates, not an order
generator. Never train on features from candles after a signal closes.
"""
import numpy as np
import pandas as pd

FEATURES=["side_long","swing_fraction","fvg_in_gold_zone","entry_level",
          "hour_utc","range_pct_12","return_12","volume_ratio_12"]
# Added only when genuinely present for every labeled event; missing POC is NOT False.
OPTIONAL_FEATURES=["liquidity_zone_count","liquidity_bsl_count","liquidity_ssl_count",
                   "liquidity_eqh_pairs","liquidity_eql_pairs","liquidity_structure_zone_count",
                   "structure_break_close_context","poc_in_gold_zone_proxy"]

def prepare_dataset(candles:pd.DataFrame,events:pd.DataFrame,trades:pd.DataFrame)->pd.DataFrame:
    required=[("candles",candles,{"ts","open","high","low","close","volume_contracts"}),
              ("events",events,{"signal_ts","side","zero_price","hundred_price","entry_level","fvg_overlaps_gold_zone"}),
              ("trades",trades,{"signal_ts","exit_ts","r_multiple"})]
    for name,frame,cols in required:
        if not cols.issubset(frame.columns):
            raise ValueError(name+" missing columns "+str(sorted(cols-set(frame.columns))))
    c=candles.copy().sort_values("ts")
    if c.ts.duplicated().any():raise ValueError("duplicate candle timestamp")
    for col in ("open","high","low","close","volume_contracts"):
        c[col]=pd.to_numeric(c[col],errors="raise")
    if not np.isfinite(c[["open","high","low","close","volume_contracts"]].to_numpy()).all():
        raise ValueError("nonfinite OHLCV")
    if (c[["open","high","low","close"]]<=0).any().any():
        raise ValueError("nonpositive prices")
    if "confirmed" in c and not c.confirmed.map(lambda x:x is True or x==1).all():
        raise ValueError("unconfirmed candle")
    c["range_pct_12"]=((c.high-c.low)/c.close).rolling(12,min_periods=12).mean()
    c["return_12"]=c.close/c.close.shift(12)-1
    c["volume_ratio_12"]=c.volume_contracts/c.volume_contracts.shift(1).rolling(12,min_periods=12).mean().replace(0,np.nan)
    e=events.copy()
    t=trades.copy()
    if e.signal_ts.duplicated().any() or t.signal_ts.duplicated().any():
        raise ValueError("ambiguous duplicate signal timestamp")
    df=e.merge(t[["signal_ts","exit_ts","r_multiple"]],on="signal_ts",validate="one_to_one")
    df=df.merge(c[["ts","range_pct_12","return_12","volume_ratio_12"]],
                left_on="signal_ts",right_on="ts",validate="one_to_one")
    if (df.exit_ts<df.signal_ts).any():raise ValueError("exit before signal")
    if not df.side.isin(["long","short"]).all():raise ValueError("invalid side")
    df["side_long"]=(df.side=="long").astype(int)
    df["swing_fraction"]=(pd.to_numeric(df.zero_price)-pd.to_numeric(df.hundred_price)).abs()/pd.to_numeric(df.hundred_price)
    df["fvg_in_gold_zone"]=df.fvg_overlaps_gold_zone.astype(int)
    df["entry_level"]=pd.to_numeric(df.entry_level)
    df["hour_utc"]=pd.to_datetime(df.signal_ts,unit="ms",utc=True).dt.hour
    for col in OPTIONAL_FEATURES:
        if col in df:
            if col in ("poc_in_gold_zone_proxy","structure_break_close_context"):
                df[col]=df[col].map({True:1,False:0,1:1,0:0})
            else:
                df[col]=pd.to_numeric(df[col],errors="coerce")
    df["r_multiple"]=pd.to_numeric(df.r_multiple)
    df=df.replace([np.inf,-np.inf],np.nan).dropna(subset=FEATURES+["r_multiple"])
    df["target_win"]=(df.r_multiple>0).astype(int)
    return df.sort_values("signal_ts").reset_index(drop=True)

def walk_forward(dataset:pd.DataFrame,*,min_train=80,test_size=25,
                 n_splits=4,embargo_ms=0,seed=42)->dict:
    from xgboost import XGBClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    if min_train<30 or test_size<10 or n_splits<1 or embargo_ms<0:
        raise ValueError("invalid evaluation settings")
    d=dataset.sort_values("signal_ts").reset_index(drop=True)
    if len(d)<min_train+test_size:
        return {"status":"insufficient_data","trades":len(d),
                "required_at_least":min_train+test_size,"folds":[]}
    feature_columns=FEATURES+[
        col for col in OPTIONAL_FEATURES
        if col in d.columns and pd.to_numeric(d[col],errors="coerce").notna().all()
    ]
    starts=list(range(min_train,len(d)-test_size+1,test_size))[-n_splits:]
    folds=[]
    for start in starts:
        test=d.iloc[start:start+test_size]
        cutoff=int(test.signal_ts.iloc[0])-embargo_ms
        train=d.iloc[:start]
        train=train[train.exit_ts<cutoff]
        if len(train)<min_train or train.target_win.nunique()<2:
            folds.append({"status":"skipped","test_start_ts":int(test.signal_ts.iloc[0]),
                          "reason":"not enough purged training trades or only one class"})
            continue
        baseline=float(train.target_win.mean())
        model=XGBClassifier(n_estimators=100,max_depth=2,learning_rate=.05,
                            subsample=1.,colsample_bytree=1.,
                            objective="binary:logistic",eval_metric="logloss",
                            random_state=seed,n_jobs=1)
        model.fit(train[feature_columns],train.target_win)
        prob=model.predict_proba(test[feature_columns])[:,1]
        logistic=make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=1000,random_state=seed))
        logistic.fit(train[feature_columns],train.target_win)
        log_prob=logistic.predict_proba(test[feature_columns])[:,1]
        y=test.target_win.to_numpy()
        selected=prob>=0.5  # predeclared threshold; this is a diagnostic, not a portfolio backtest
        r_values=test.r_multiple.to_numpy(dtype=float)
        folds.append({"status":"evaluated","train_trades":len(train),
                      "test_trades":len(test),
                      "test_start_ts":int(test.signal_ts.iloc[0]),
                      "test_end_ts":int(test.signal_ts.iloc[-1]),
                      "xgboost_brier":round(float(np.mean((prob-y)**2)),6),
                      "logistic_brier":round(float(np.mean((log_prob-y)**2)),6),
                      "baseline_brier":round(float(np.mean((baseline-y)**2)),6),
                      "mean_test_r":round(float(test.r_multiple.mean()),5),
                      "selected_by_model":int(selected.sum()),
                      "model_selected_mean_r":round(float(r_values[selected].mean()),5) if selected.any() else None,
                      "model_selected_r_sum":round(float(r_values[selected].sum()),5),
                      "all_test_r_sum":round(float(r_values.sum()),5)})
    good=[f for f in folds if f["status"]=="evaluated"]
    return {"status":"evaluated" if good else "insufficient_data",
            "trades":len(d),"features":feature_columns,"folds":folds,
            "mean_xgboost_brier":round(float(np.mean([f["xgboost_brier"] for f in good])),6) if good else None,
            "mean_baseline_brier":round(float(np.mean([f["baseline_brier"] for f in good])),6) if good else None,
            "mean_logistic_brier":round(float(np.mean([f["logistic_brier"] for f in good])),6) if good else None,
            "warnings":["Only executed closed trades have labels; selection bias remains.",
                        "Logistic regression is a fixed comparator, not tuned or used for live trading.",
                        "This classifier does not place orders or prove strategy profitability.",
                        "Threshold 0.5 is a fixed exploratory selection diagnostic: overlapping signals and risk sizing are not re-simulated.",
                        "An independent untouched final holdout is still required."]}
