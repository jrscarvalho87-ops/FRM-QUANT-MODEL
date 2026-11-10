"""Validate HUMAN RFM setup annotations before quantitative model training.

Accepts the 36-case blinded review tool's CSV and a frozen manifest. Refuses
unknown cases, duplicated labels, invalid judgments and mismatched metadata.
Does NOT look at future trade outcomes or calculate profitability.

Run:
  python -m research.annotation_review --manifest review_manifest.json \
      --labels RFM_Quant_Labels_36_Casos.csv --output annotation_report.json
"""
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

JUDGMENTS=("fib_ok","liquidity_relevant","fvg_ok","accept_setup")
ALLOWED={"","sim","não","incerto"}
IDENTITY=("case_id","instrument","signal_ts","direction")
EXPECTED=set(IDENTITY+JUDGMENTS+("notes",))


def load_manifest(path):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("kind")!="rfm_human_annotation_blinded":
        raise ValueError("not a RFM outcome-blinded review manifest")
    cases=data.get("cases")
    if not isinstance(cases,list) or not cases:
        raise ValueError("missing review cases")
    result={}
    for case in cases:
        if not isinstance(case,dict) or any(not case.get(k) for k in IDENTITY):
            raise ValueError("case missing identity")
        ident=str(case["case_id"])
        if ident in result:
            raise ValueError("duplicate manifest case")
        if any(k in case for k in ("pnl","r_multiple","exit_ts","exit_reason",
                                    "trade_outcome","future_candles")):
            raise ValueError("future trading outcomes must not appear in blinded manifest")
        result[ident]=case
    return result


def load_labels(path,manifest):
    with Path(path).open("r",encoding="utf-8-sig",newline="") as stream:
        reader=csv.DictReader(stream)
        if not reader.fieldnames or set(reader.fieldnames)!=EXPECTED:
            raise ValueError("unexpected annotation CSV columns")
        values={}
        for line in reader:
            ident=line.get("case_id","")
            if not ident or ident not in manifest:
                raise ValueError("label refers to unknown or missing review case")
            if ident in values:
                raise ValueError("duplicate annotation case")
            reference=manifest[ident]
            for field in IDENTITY:
                if str(line.get(field,""))!=str(reference[field]):
                    raise ValueError("annotation identity mismatch: "+field)
            for key in JUDGMENTS:
                if line.get(key,"") not in ALLOWED:
                    raise ValueError("unsupported human judgment in "+key)
            values[ident]={k:line.get(k,"") for k in JUDGMENTS+("notes",)}
        if set(values)!=set(manifest):
            raise ValueError("missing annotation case row; do not silently change denominator")
    return values


def _group_summary(records,field):
    groups=defaultdict(list)
    for case,label in records:
        groups[str(case.get(field,"desconhecido"))].append(label["accept_setup"])
    result={}
    for key,decisions in sorted(groups.items()):
        explicit=[d for d in decisions if d in ("sim","não")]
        result[key]={
            "selected_by_blinded_sampling":len(decisions),
            "human_decision_yes":sum(d=="sim" for d in explicit),
            "human_decision_no":sum(d=="não" for d in explicit),
            "human_decision_uncertain":sum(d=="incerto" for d in decisions),
            "human_decision_missing":sum(not d for d in decisions),
            "human_acceptance_rate_pct_among_explicit":
                round(100*sum(d=="sim" for d in explicit)/len(explicit),2)
                if explicit else None,
        }
    return result


def summarize_annotations(manifest,labels):
    if set(labels)!=set(manifest):
        raise ValueError("review labels do not match the manifest")
    records=[(case,labels[case_id]) for case_id,case in manifest.items()]
    summaries={}
    for field in JUDGMENTS:
        raw=Counter(v[field] for _,v in records)
        summaries[field]={
            "sim":raw["sim"],"não":raw["não"],
            "incerto":raw["incerto"],"sem_resposta":raw[""]
        }
    complete=sum(all(label[k] in ("sim","não","incerto")
                     for k in JUDGMENTS) for _,label in records)
    contradictory=[case["case_id"] for case,label in records
                   if label["accept_setup"]=="sim" and (
                       label["fib_ok"]=="não" or label["fvg_ok"]=="não" or
                       label["liquidity_relevant"]=="não")]
    return {
        "status":"human_annotations_descriptive_only",
        "reviewed_cases":len(records),
        "fully_answered_cases":complete,
        "fully_answered_pct":round(100*complete/len(records),2),
        "judgments":summaries,
        "by_instrument":_group_summary(records,"instrument"),
        "by_structural_stratum":_group_summary(records,"context_tag"),
        "possible_annotation_inconsistencies":contradictory,
        "warning":[
            "Blinded sample deliberately oversampled unusual liquidity configurations; acceptance rates are NOT population prevalence.",
            "A human decision to accept a setup is NOT a trading return or proven predictive edge.",
            "Do not fit or test a trade-selection model using these labels on a previously examined historical period and claim an untouched holdout.",
            "Blinded labels are relevant to refining objective swing/liquidity definitions, without using trade PnL for tuning.",
            "Only historical/paper-trading research; no live orders."
        ]
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--manifest",required=True)
    parser.add_argument("--labels",required=True)
    parser.add_argument("--output")
    args=parser.parse_args()
    manifest=load_manifest(args.manifest)
    annotations=load_labels(args.labels,manifest)
    report=summarize_annotations(manifest,annotations)
    rendered=json.dumps(report,ensure_ascii=False,indent=2)
    if args.output:
        Path(args.output).write_text(rendered,encoding="utf-8")
    print(rendered)


if __name__=="__main__":
    main()
