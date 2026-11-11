import unittest
from fibonacci import levels


class FibonacciTests(unittest.TestCase):
    def test_long_0_above_100(self):
        r=levels(82212.9,81141.4,"long")
        self.assertAlmostEqual(r["level_67"],81495.0,places=1)
        self.assertAlmostEqual(r["level_75"],81409.275,places=2)
        self.assertAlmostEqual(r["rr_at_75"],3.0)

    def test_short_100_above_0(self):
        r=levels(82685.2,83640.8,"short")
        self.assertAlmostEqual(r["level_67"],83325.452,places=2)
        self.assertAlmostEqual(r["level_75"],83401.9,places=1)
        self.assertAlmostEqual(r["rr_at_67"],67/33)

    def test_user_drawing_order_uses_wick_extremes_not_chronological_order(self):
        up=levels(120,100,"long")
        self.assertEqual(up["drawing_start_extreme"],"high")
        self.assertEqual(up["drawing_end_extreme"],"low")
        self.assertEqual(up["drawing_start_price"],120)
        self.assertEqual(up["drawing_end_price"],100)
        down=levels(100,120,"short")
        self.assertEqual(down["drawing_start_extreme"],"low")
        self.assertEqual(down["drawing_end_extreme"],"high")
        self.assertEqual(down["drawing_start_price"],100)
        self.assertEqual(down["drawing_end_price"],120)
        self.assertEqual(up["anchor_source"],"high_low_wicks_not_candle_bodies")

    def test_wrong_direction_rejected(self):
        with self.assertRaises(ValueError):
            levels(100,90,"short")
        with self.assertRaises(ValueError):
            levels(90,100,"long")


if __name__=="__main__":
    unittest.main()
