import unittest
from universe import catalog_status, screen_window


class UniverseTests(unittest.TestCase):
    def test_contract_classification_never_substitutes_tickers(self):
        raw=[
            {"instId":"BTC-USDT-SWAP","state":"live"},
            {"instId":"GRAM-USDT-SWAP","state":"suspend"},
            {"instId":"GRASS-USDT-SWAP","state":"live"},
            {"instId":"ETH-USDC-SWAP","state":"live"},
        ]
        items=catalog_status(raw,["BTC","GRAM","ETH"])
        self.assertEqual(items[0]["usdt_swap"],"BTC-USDT-SWAP")
        self.assertIsNone(items[1]["usdt_swap"])
        self.assertEqual(items[1]["status"],"not_in_public_usdt_usdc_swap_catalog")
        self.assertEqual(items[2]["usdc_swap"],"ETH-USDC-SWAP")

    def test_long_window_screen_passes_clean_data_only(self):
        rows=[
            {"ts":i*14_400_000,"open":"100","high":"101","low":"99",
             "close":"100","volume_contracts":"5","confirmed":True}
            for i in range(1,651)
        ]
        h={"candles":rows,"bar":"4H","coverage_days":round((rows[-1]["ts"]-rows[0]["ts"])/86_400_000,2),
           "missing_intervals":0,"gap_fraction":0.0,
           "rejected":{"malformed":0,"duplicate":0,"unconfirmed":0}}
        result=screen_window(h,minimum_days=90)
        self.assertEqual(result["status"],"window_quality_pass")
        self.assertFalse(result["spread_checked"])

    def test_short_window_rejected_even_if_no_bad_candles(self):
        h={"candles":[{"ts":900000,"open":"100","high":"101","low":"99",
                        "close":"100","volume_contracts":"5"}],
           "bar":"15m","coverage_days":0,"missing_intervals":0,
           "gap_fraction":0,
           "rejected":{"malformed":0,"duplicate":0,"unconfirmed":0}}
        self.assertIn("insufficient_lookback_days",screen_window(h)["flags"])

    def test_zero_volume_flags_market(self):
        rows=[{"ts":i*14_400_000,"open":"100","high":"101","low":"99",
               "close":"100","volume_contracts":"0"} for i in range(1,651)]
        h={"candles":rows,"bar":"4H","coverage_days":108.17,
           "missing_intervals":0,"gap_fraction":0,
           "rejected":{"malformed":0,"duplicate":0,"unconfirmed":0}}
        self.assertIn("zero_volume_candles",screen_window(h)["flags"])


if __name__=="__main__":
    unittest.main()
