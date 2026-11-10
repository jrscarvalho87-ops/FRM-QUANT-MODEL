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

    def test_wrong_direction_rejected(self):
        with self.assertRaises(ValueError):
            levels(100,90,"short")
        with self.assertRaises(ValueError):
            levels(90,100,"long")


if __name__=="__main__":
    unittest.main()
