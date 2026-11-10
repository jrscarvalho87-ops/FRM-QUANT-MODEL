import unittest
from swing_liquidity_context import summarize_liquidity_for_swing


class SwingLiquidityContextTests(unittest.TestCase):
    def zone(self,kind,price,anchor,known,breached=False):
        return {"type":kind,"price":price,"anchor_ts":anchor,
                "known_after_close_ts":known,
                "breached_after_confirmation":breached}

    def check(self,zones):
        return summarize_liquidity_for_swing(
            zones,hundred_price=100,zero_price=120,
            hundred_anchor_ts=10,zero_anchor_ts=20,
            signal_ts=30,interval_ms=1)

    def test_preexisting_and_in_impulse_levels_are_distinguished(self):
        r=self.check([
            self.zone("BSL",110,2,5),
            self.zone("SSL",105,15,18),
            self.zone("EQH",112,15,20,True),
            self.zone("PDL",95,3,4),
        ])
        self.assertEqual(r["all_known_zone_count"],4)
        self.assertEqual(r["in_swing_price_range_count"],3)
        self.assertEqual(r["unbreached_in_swing_count"],2)
        self.assertEqual(r["formed_during_swing_count"],2)
        self.assertEqual(r["known_before_swing_count"],1)
        self.assertEqual(r["unbreached_contextual_count"],2)
        self.assertEqual(r["in_swing_distinct_types"],3)
        self.assertEqual(r["unbreached_contextual_distinct_types"],2)

    def test_liquidity_relevance_not_distance_to_gold_zone_or_tp(self):
        r=self.check([self.zone("BSL",101,3,5)])
        # 101 is far from target (120) and from the 67%-75% entry zone
        # (105-106.6), but it is still in the structural swing.
        self.assertEqual(r["unbreached_contextual_count"],1)

    def test_future_zone_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"future"):
            self.check([self.zone("EQH",110,10,35)])

    def test_fibonacci_anchor_levels_do_not_count_as_independent_liquidity(self):
        # Both pivots are inevitably structural high/low levels, and must
        # not create evidence of extra liquidity by construction.
        r=self.check([
            self.zone("SSL",100,10,14),
            self.zone("BSL",120,20,24),
        ])
        self.assertEqual(r["unbreached_contextual_count"],2)
        self.assertEqual(r["independent_in_swing_count"],0)
        self.assertEqual(r["independent_unbreached_contextual_count"],0)
        self.assertEqual(r["independent_unbreached_contextual_types"],0)

    def test_separate_prior_zone_counts_without_proximity_rule(self):
        r=self.check([
            self.zone("SSL",100,10,14),
            self.zone("BSL",120,20,24),
            self.zone("EQL",101,1,6),
        ])
        self.assertEqual(r["independent_unbreached_contextual_count"],1)
        self.assertEqual(r["independent_unbreached_contextual_types"],1)

    def test_no_threshold_or_filter_is_invented(self):
        r=self.check([])
        self.assertEqual(r["unbreached_contextual_count"],0)
        self.assertEqual(r["in_swing_distinct_types"],0)

if __name__=="__main__":
    unittest.main()
