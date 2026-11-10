import copy
import unittest

from swing_geometry import audit_swing_geometry


class SwingGeometryTests(unittest.TestCase):
    def bars(self):
        return [
            {"ts":1000,"high":10,"low":5,"confirmed":True},
            {"ts":2000,"high":14,"low":9,"confirmed":True},
            {"ts":3000,"high":20,"low":13,"confirmed":True},
            {"ts":4000,"high":18,"low":14,"confirmed":True},
        ]

    def test_valid_long_extrema_not_outside_swings(self):
        b=self.bars()
        r=audit_swing_geometry(
            b,hundred_index=0,zero_index=2,asof_index=3,side="long")
        self.assertTrue(r["anchors_valid"])
        self.assertEqual(r["swing_duration_bars"],2)
        self.assertEqual(r["confirmation_lag_bars"],1)

    def test_invalid_zero_pivot_if_older_high_was_higher(self):
        b=self.bars()
        b[1]["high"]=22
        r=audit_swing_geometry(
            b,hundred_index=0,zero_index=2,asof_index=3,side="long")
        self.assertFalse(r["target_extreme_valid"])
        self.assertTrue(r["stop_extreme_valid"])
        self.assertFalse(r["anchors_valid"])

    def test_invalid_hundred_pivot_if_intervening_low_broke_it(self):
        b=self.bars()
        b[1]["low"]=4
        r=audit_swing_geometry(
            b,hundred_index=0,zero_index=2,asof_index=3,side="long")
        self.assertFalse(r["stop_extreme_valid"])

    def test_short_mirrors_long(self):
        b=self.bars()
        for row in b:
            h,l=row["high"],row["low"]
            row["high"]=30-l
            row["low"]=30-h
        r=audit_swing_geometry(
            b,hundred_index=0,zero_index=2,asof_index=3,side="short")
        self.assertTrue(r["anchors_valid"])
        b[1]["low"]=1
        bad=audit_swing_geometry(
            b,hundred_index=0,zero_index=2,asof_index=3,side="short")
        self.assertFalse(bad["target_extreme_valid"])

    def test_future_changes_do_not_affect_existing_audit(self):
        b=self.bars()
        before=audit_swing_geometry(
            b,hundred_index=0,zero_index=2,asof_index=3,side="long")
        future=copy.deepcopy(b)
        future.extend([{"ts":5000,"high":1e9,"low":0.1,"confirmed":False}])
        after=audit_swing_geometry(
            future,hundred_index=0,zero_index=2,asof_index=3,side="long")
        self.assertEqual(before,after)

    def test_reject_invalid_order_and_unconfirmed_past(self):
        b=self.bars()
        with self.assertRaisesRegex(ValueError,"invalid"):
            audit_swing_geometry(
                b,hundred_index=2,zero_index=0,asof_index=3,side="long")
        b[1]["confirmed"]=False
        with self.assertRaisesRegex(ValueError,"unconfirmed"):
            audit_swing_geometry(
                b,hundred_index=0,zero_index=2,asof_index=3,side="long")


if __name__=="__main__":
    unittest.main()
