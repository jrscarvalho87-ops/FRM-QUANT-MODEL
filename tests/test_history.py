import asyncio
import unittest
from history import fetch_history


def candle(i, confirmed="1"):
    return [str(i*900000),"100","101","99","100","5","5","500",confirmed]


class HistoryTests(unittest.TestCase):
    def run_fetch(self, newest=250, requested=150, page_size=100, gap=None):
        calls=[]
        async def fake(_path,params):
            calls.append(dict(params))
            upper=int(params["after"])//900000-1 if "after" in params else newest
            indexes=[x for x in range(upper,0,-1) if x != gap][:int(params["limit"])]
            return [candle(x) for x in indexes]
        return asyncio.run(fetch_history(fake,"BTC-USDT-SWAP","15m",requested,page_size)), calls

    def test_multiple_pages_chronological(self):
        result,calls=self.run_fetch()
        self.assertEqual(result["returned_bars"],150)
        self.assertEqual(len(calls),2)
        self.assertEqual(result["first_ts"],101*900000)
        self.assertEqual(result["last_ts"],250*900000)
        self.assertEqual(result["missing_intervals"],0)

    def test_missing_interval_is_reported(self):
        result,_=self.run_fetch(gap=150)
        self.assertGreater(result["missing_intervals"],0)
        self.assertNotEqual(result["gap_fraction"],0)

    def test_empty_history(self):
        async def empty(_path,_params):
            return []
        result=asyncio.run(fetch_history(empty,"GRAM-USDT-SWAP","4H",100))
        self.assertEqual(result["returned_bars"],0)
        self.assertTrue(result["history_exhausted"])

    def test_reject_invalid_requested_size(self):
        async def fake(_path,_params):
            return []
        with self.assertRaises(ValueError):
            asyncio.run(fetch_history(fake,"BTC-USDT-SWAP","15m",2001))

    def test_no_forward_fill(self):
        result,_=self.run_fetch(gap=248)
        self.assertEqual(len(result["candles"]),150)
        self.assertNotIn(248*900000,[r["ts"] for r in result["candles"]])


if __name__=="__main__":
    unittest.main()
