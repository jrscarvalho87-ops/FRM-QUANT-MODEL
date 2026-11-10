"""Execution invariants: close-only signals, conservative fills and no fake RFM results."""
import unittest
from execution import simulate


def bar(i, o=100, h=101, l=99, c=100):
    return {"ts": 900000*(i+1), "open":str(o), "high":str(h),
            "low":str(l), "close":str(c), "confirmed":True}


def signal(i=0, side="long", entry=100, stop=95, take=110, ttl=3):
    return {"signal_ts":900000*(i+1), "side":side, "entry":entry,
            "stop":stop, "take":take, "expiry_bars":ttl}


class ExecutionTests(unittest.TestCase):
    def test_signal_cannot_fill_in_its_own_candle(self):
        result = simulate([bar(0,l=90),bar(1,l=101,h=103)], [signal()])
        self.assertEqual(result["summary"]["closed_trades"],0)
        self.assertEqual(result["summary"]["skipped"]["entry_not_filled"],1)

    def test_stop_wins_ambiguous_candle(self):
        candles = [bar(0),bar(1,h=112,l=94)]
        result = simulate(candles,[signal()],max_hold_bars=1)
        self.assertEqual(result["summary"]["closed_trades"],1)
        self.assertEqual(result["trades"][0]["exit_reason"],"stop_loss")
        self.assertLess(result["trades"][0]["pnl"],0)

    def test_profitable_trade_net_of_costs(self):
        candles = [bar(0),bar(1,h=111,l=99)]
        result = simulate(candles,[signal()],max_hold_bars=1)
        self.assertEqual(result["trades"][0]["exit_reason"],"take_profit")
        self.assertGreater(result["trades"][0]["pnl"],0)
        self.assertLess(result["trades"][0]["pnl"],200)

    def test_reject_planned_rr_below_two(self):
        result=simulate([bar(0),bar(1)], [signal(entry=75,stop=0.1,take=100)])
        self.assertEqual(result["summary"]["closed_trades"],0)
        self.assertEqual(result["summary"]["skipped"]["rr_below_minimum"],1)

    def test_bar_gap_does_not_create_fake_fill(self):
        bars=[bar(0),bar(1),bar(3)]
        result=simulate(bars,[signal(entry=98,stop=95,take=104,ttl=3)])
        self.assertEqual(result["summary"]["closed_trades"],0)
        self.assertEqual(result["summary"]["skipped"]["data_gap"],1)

    def test_exposure_capped(self):
        result=simulate([bar(0),bar(1,h=120,l=99)],
                        [signal(entry=100,stop=99,take=110)],max_hold_bars=1)
        self.assertLessEqual(result["trades"][0]["quantity"]*result["trades"][0]["entry_price"],10001)

    def test_no_open_trade_reported_as_win(self):
        bars=[bar(0),bar(1,h=101,l=99)]
        result=simulate(bars,[signal()],max_hold_bars=96)
        self.assertEqual(result["summary"]["closed_trades"],0)
        self.assertEqual(result["summary"]["skipped"]["open_at_sample_end"],1)

    def test_short_stop_first(self):
        bars=[bar(0),bar(1,h=106,l=89)]
        result=simulate(bars,[signal(side="short",entry=100,stop=105,take=90)],max_hold_bars=1)
        self.assertEqual(result["trades"][0]["exit_reason"],"stop_loss")

    def test_equity_with_no_signals(self):
        result=simulate([bar(0)],[])
        self.assertIsNone(result["summary"]["win_rate_pct"])
        self.assertEqual(result["summary"]["ending_equity"],10000)

    def test_unconfirmed_rejected(self):
        bad=bar(0)
        bad["confirmed"]=False
        with self.assertRaises(ValueError):
            simulate([bad],[])


if __name__=="__main__":
    unittest.main()
