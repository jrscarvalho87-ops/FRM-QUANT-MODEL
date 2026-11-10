import unittest

from research.audit_geometry_snapshot import old_anchor_audit


class ArchiveGeometryAuditTests(unittest.TestCase):
    def bars(self):
        return [
            {"ts":900000,"high":10,"low":5,"confirmed":True},
            {"ts":1800000,"high":14,"low":9,"confirmed":True},
            {"ts":2700000,"high":20,"low":13,"confirmed":True},
            {"ts":3600000,"high":18,"low":14,"confirmed":True},
        ]

    def event(self):
        return {"signal_ts":3600000,"side":"long",
                "anchor_100_ts":900000,"anchor_0_ts":2700000}

    def test_archive_auditor_finds_bad_zero_anchor(self):
        b=self.bars()
        e=self.event()
        self.assertTrue(old_anchor_audit(b,[e])[0]["anchors_valid"])
        b[1]["high"]=21
        result=old_anchor_audit(b,[e])[0]
        self.assertFalse(result["anchors_valid"])
        self.assertTrue(result["stop_extreme_valid"])
        self.assertFalse(result["target_extreme_valid"])

    def test_event_referencing_missing_candle_rejected(self):
        e=self.event()
        e["anchor_0_ts"]=12345
        with self.assertRaisesRegex(ValueError,"missing"):
            old_anchor_audit(self.bars(),[e])

if __name__=="__main__":
    unittest.main()
