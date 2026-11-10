"""Human label ingestion tests; no market-return data is required."""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from research.annotation_review import (
    load_manifest, load_labels, summarize_annotations, EXPECTED
)


class HumanAnnotationAuditTests(unittest.TestCase):
    def manifest(self):
        cases=[
            {"case_id":"BTC-900","instrument":"BTC-USDT-SWAP",
             "signal_ts":900,"direction":"long","context_tag":"externo_ambos_lados"},
            {"case_id":"ETH-1800","instrument":"ETH-USDT-SWAP",
             "signal_ts":1800,"direction":"short","context_tag":"nível_independente_no_swing"},
        ]
        return {"kind":"rfm_human_annotation_blinded","cases":cases}

    def save_files(self,tmp,document=None,rows=None):
        p=Path(tmp)
        m=p/"manifest.json"
        c=p/"labels.csv"
        m.write_text(json.dumps(document if document is not None else self.manifest()),
                     encoding="utf-8")
        if rows is None:
            rows=[
                {"case_id":"BTC-900","instrument":"BTC-USDT-SWAP",
                 "signal_ts":"900","direction":"long","fib_ok":"sim",
                 "liquidity_relevant":"incerto","fvg_ok":"sim","accept_setup":"não",
                 "notes":""},
                {"case_id":"ETH-1800","instrument":"ETH-USDT-SWAP",
                 "signal_ts":"1800","direction":"short","fib_ok":"não",
                 "liquidity_relevant":"sim","fvg_ok":"sim","accept_setup":"incerto",
                 "notes":"Wrong impulse"},
            ]
        with c.open("w",encoding="utf-8-sig",newline="") as stream:
            writer=csv.DictWriter(stream,fieldnames=list(EXPECTED))
            writer.writeheader()
            writer.writerows(rows)
        return m,c,rows

    def test_complete_valid_label_summary(self):
        with tempfile.TemporaryDirectory() as folder:
            mp,cp,_=self.save_files(folder)
            m=load_manifest(mp)
            labels=load_labels(cp,m)
            result=summarize_annotations(m,labels)
            self.assertEqual(result["fully_answered_cases"],2)
            self.assertEqual(result["judgments"]["fib_ok"]["não"],1)
            self.assertEqual(result["judgments"]["accept_setup"]["incerto"],1)
            self.assertEqual(result["by_instrument"]["BTC-USDT-SWAP"]["human_decision_no"],1)
            self.assertEqual(result["possible_annotation_inconsistencies"],[])
            self.assertNotIn("r_multiple",json.dumps(result))

    def test_reject_unknown_id_and_future_pnl(self):
        with tempfile.TemporaryDirectory() as folder:
            doc=self.manifest()
            doc["cases"][0]["r_multiple"]=3
            mp,cp,_=self.save_files(folder,document=doc)
            with self.assertRaisesRegex(ValueError,"future"):
                load_manifest(mp)
        with tempfile.TemporaryDirectory() as folder:
            mp,cp,rows=self.save_files(folder)
            rows[0]["case_id"]="BTC-fake"
            _,cp,_=self.save_files(folder,rows=rows)
            with self.assertRaisesRegex(ValueError,"unknown"):
                load_labels(cp,load_manifest(mp))

    def test_reject_duplicate_and_missing_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            mp,cp,rows=self.save_files(folder)
            _,cp,_=self.save_files(folder,rows=[rows[0],rows[0]])
            with self.assertRaisesRegex(ValueError,"duplicate"):
                load_labels(cp,load_manifest(mp))
            _,cp,_=self.save_files(folder,rows=[rows[0]])
            with self.assertRaisesRegex(ValueError,"missing"):
                load_labels(cp,load_manifest(mp))

    def test_reject_illegal_label_and_mismatched_side(self):
        with tempfile.TemporaryDirectory() as folder:
            mp,cp,rows=self.save_files(folder)
            rows[0]["accept_setup"]="lucro"
            _,cp,_=self.save_files(folder,rows=rows)
            with self.assertRaisesRegex(ValueError,"unsupported"):
                load_labels(cp,load_manifest(mp))
        with tempfile.TemporaryDirectory() as folder:
            mp,cp,rows=self.save_files(folder)
            rows[0]["direction"]="short"
            _,cp,_=self.save_files(folder,rows=rows)
            with self.assertRaisesRegex(ValueError,"mismatch"):
                load_labels(cp,load_manifest(mp))

    def test_inconsistent_human_acceptance_is_flagged_not_erased(self):
        with tempfile.TemporaryDirectory() as folder:
            mp,cp,rows=self.save_files(folder)
            rows[0]["accept_setup"]="sim"
            rows[0]["fvg_ok"]="não"
            _,cp,_=self.save_files(folder,rows=rows)
            report=summarize_annotations(load_manifest(mp),
                load_labels(cp,load_manifest(mp)))
            self.assertEqual(report["possible_annotation_inconsistencies"],["BTC-900"])


if __name__=="__main__":
    unittest.main()
