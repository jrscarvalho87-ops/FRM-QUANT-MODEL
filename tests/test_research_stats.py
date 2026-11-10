import unittest
from research_stats import bootstrap_r_multiples


class BootstrapTests(unittest.TestCase):
    def test_small_sample_returns_no_probabilities(self):
        result=bootstrap_r_multiples([{"r_multiple":1}]*9)
        self.assertEqual(result["status"],"insufficient_sample")
        self.assertNotIn("prob_bootstrap_mean_r_below_zero",result)

    def test_seed_reproducibility(self):
        trades=[{"r_multiple":(-1 if i%3==0 else 2)} for i in range(30)]
        a=bootstrap_r_multiples(trades,iterations=200,seed=12)
        b=bootstrap_r_multiples(trades,iterations=200,seed=12)
        self.assertEqual(a,b)
        self.assertEqual(a["observed_trades"],30)

    def test_all_losses_negative_expectancy(self):
        result=bootstrap_r_multiples([{"r_multiple":-1}]*20,iterations=100)
        self.assertEqual(result["prob_bootstrap_mean_r_below_zero"],1.0)
        self.assertEqual(result["mean_r_p95"],-1)

    def test_reject_nonfinite(self):
        with self.assertRaisesRegex(ValueError,"Nonfinite"):
            bootstrap_r_multiples([{"r_multiple":float("nan")}]*20)


if __name__=="__main__":
    unittest.main()
