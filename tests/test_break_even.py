import unittest
from execution import simulate

class BreakEvenTests(unittest.TestCase):
    def bars(self,values):
        return [{"ts":i*900000,"open":o,"high":h,"low":l,"close":c,
                 "confirmed":True} for i,(o,h,l,c) in enumerate(values)]

    def signal(self,side="long"):
        if side=="long":
            return [{"signal_ts":0,"side":"long","entry":100,"stop":95,"take":115,
                     "expiry_bars":2}]
        return [{"signal_ts":0,"side":"short","entry":100,"stop":105,"take":85,
                 "expiry_bars":2}]

    def run_sim(self,bars,side="long",**kw):
        return simulate(self.bars(bars),self.signal(side),fee_bps=0,
                        slippage_bps=0,max_exposure=5,**kw)

    def test_long_arms_at_one_r_and_stops_at_entry_on_later_bar(self):
        bars=[(110,111,109,110),(101,106,99,105),
              (105,106,101,105),(101,102,99,100)]
        r=self.run_sim(bars)
        self.assertEqual(r["summary"]["closed_trades"],1)
        self.assertEqual(r["trades"][0]["exit_reason"],"break_even_stop")
        self.assertEqual(r["trades"][0]["pnl"],0)
        self.assertTrue(r["trades"][0]["be_activated"])

    def test_short_arms_and_stops_at_entry(self):
        bars=[(90,91,89,90),(99,101,94,95),
              (95,99,94,96),(99,101,98,100)]
        r=self.run_sim(bars,"short")
        self.assertEqual(r["trades"][0]["exit_reason"],"break_even_stop")
        self.assertEqual(r["trades"][0]["pnl"],0)

    def test_same_bar_reversal_cannot_retroactively_use_be(self):
        bars=[(110,111,109,110),(100,106,94,100)]
        r=self.run_sim(bars)
        self.assertEqual(r["trades"][0]["exit_reason"],"stop_loss")
        self.assertFalse(r["trades"][0]["be_activated"])

    def test_fees_mean_be_can_be_net_negative(self):
        bars=[(110,111,109,110),(101,106,99,105),
              (105,106,101,105),(101,102,99,100)]
        r=simulate(self.bars(bars),self.signal(),fee_bps=5,
                   slippage_bps=0,max_exposure=5)
        self.assertEqual(r["trades"][0]["exit_reason"],"break_even_stop")
        self.assertLess(r["trades"][0]["pnl"],0)

    def test_be_can_be_disabled_for_control_comparison(self):
        bars=[(110,111,109,110),(101,106,99,105),
              (105,106,101,105),(101,102,99,100),
              (100,115,99,114)]
        r=self.run_sim(bars,move_stop_to_be_at_r=None)
        self.assertEqual(r["trades"][0]["exit_reason"],"take_profit")
        self.assertFalse(r["trades"][0]["be_activated"])

if __name__=="__main__":
    unittest.main()
