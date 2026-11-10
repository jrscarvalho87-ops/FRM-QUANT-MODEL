import unittest

from research.robustness import block_bootstrap_r


class BlockBootstrapTests(unittest.TestCase):
    def trades(self,rs):
        return [{"r_multiple":r} for r in rs]

    def test_small_sample_refused(self):
        report=block_bootstrap_r(self.trades([3,-1,0]*9))
        self.assertEqual(report["status"],"insufficient_data")
        self.assertNotIn("compounded_return_pct_p50",report)

    def test_reproducibility_and_ordered_quantiles(self):
        trades=self.trades([3,-1,-.03,1.2,0,2,-1]*10)
        a=block_bootstrap_r(trades,iterations=200,seed=42)
        b=block_bootstrap_r(trades,iterations=200,seed=42)
        self.assertEqual(a,b)
        self.assertEqual(a["status"],"exploratory_moving_block_bootstrap")
        self.assertLessEqual(a["mean_r_p05"],a["mean_r_p50"])
        self.assertLessEqual(a["mean_r_p50"],a["mean_r_p95"])
        self.assertGreaterEqual(a["max_closed_trade_drawdown_pct_p95"],0)

    def test_all_losers_yield_negative_compounded_returns(self):
        report=block_bootstrap_r(self.trades([-1]*40),iterations=100)
        self.assertLess(report["compounded_return_pct_p95"],0)
        self.assertAlmostEqual(report["mean_r_p50"],-1)

    def test_nonfinite_and_excess_risk_rejected(self):
        with self.assertRaisesRegex(ValueError,"non-finite"):
            block_bootstrap_r(self.trades([float("nan")]*40))
        with self.assertRaisesRegex(ValueError,"too negative"):
            block_bootstrap_r(self.trades([-200]*40))

if __name__=="__main__":
    unittest.main()
