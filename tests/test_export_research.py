"""Offline tests for paginated, gap-intolerant historical retrieval."""
import unittest
from research.export_research import fetch_candles

MS=900000

class FakeResponse:
    def __init__(self,data):self.data=data
    def raise_for_status(self):pass
    def json(self):return self.data

class FakeClient:
    def __init__(self,bars):self.bars=bars;self.calls=0
    def get(self,url,params):
        self.calls+=1
        if url.endswith("/api/okx/history"):
            b=self.bars[-int(params["bars"]):]
            return FakeResponse({"candles":b,"missing_intervals":0,
                "rejected":{"malformed":0},"pages_requested":20,"history_exhausted":False})
        if url.endswith("/api/okx/candles"):
            older=[c for c in self.bars if c["ts"]<int(params["after"])]
            b=older[-100:]
            return FakeResponse({"candles":b,"missing_intervals":0,
                "rejected":{"malformed":0}})
        raise AssertionError("unexpected URL")

class HistoricalPaginationTests(unittest.TestCase):
    def candles(self,n):
        return [{"ts":(i+1)*MS,"open":100+i*.01,"high":101+i*.01,
                 "low":99+i*.01,"close":100+i*.01,
                 "volume_contracts":20,"confirmed":True} for i in range(n)]

    def test_paginates_beyond_2000_and_deduplicates(self):
        client=FakeClient(self.candles(2150))
        rows,meta=fetch_candles(client,"https://example.com","BTC-USDT-SWAP","15m",2100)
        self.assertEqual(len(rows),2100)
        self.assertEqual(len({r["ts"] for r in rows}),2100)
        self.assertFalse(meta["exhausted_before_target"])
        self.assertEqual(rows[0]["ts"],51*MS)
        self.assertGreater(client.calls,1)

    def test_unavailable_history_is_flagged(self):
        client=FakeClient(self.candles(300))
        rows,meta=fetch_candles(client,"https://example.com","BTC-USDT-SWAP","15m",2500)
        self.assertEqual(len(rows),300)
        self.assertTrue(meta["exhausted_before_target"])

    def test_cross_page_gap_rejected(self):
        bars=self.candles(2100)
        bars.pop(40)
        client=FakeClient(bars)
        with self.assertRaisesRegex(ValueError,"gap"):
            fetch_candles(client,"https://example.com","BTC-USDT-SWAP","15m",2100)

    def test_exact_pinned_cutoff_replays_older_window(self):
        bars=self.candles(2600)
        client=FakeClient(bars)
        rows,meta=fetch_candles(
            client,"https://example.com","BTC-USDT-SWAP","15m",1000,
            last_bar_ts=2000*MS)
        self.assertEqual(len(rows),1000)
        self.assertEqual(rows[-1]["ts"],2000*MS)
        self.assertEqual(rows[0]["ts"],1001*MS)
        self.assertEqual(meta["pinned_last_bar_ts"],2000*MS)

    def test_pinned_cutoff_refuses_earlier_or_unavailable_end(self):
        bars=self.candles(2100)
        client=FakeClient(bars)
        with self.assertRaisesRegex(ValueError,"Exact pinned"):
            fetch_candles(client,"https://example.com","BTC-USDT-SWAP","15m",
                          1000,last_bar_ts=3000*MS)

    def test_unconfirmed_candle_rejected(self):
        bars=self.candles(2100)
        bars[-10]["confirmed"]=False
        client=FakeClient(bars)
        with self.assertRaisesRegex(ValueError,"Unconfirmed"):
            fetch_candles(client,"https://example.com","BTC-USDT-SWAP","15m",2100)

if __name__=="__main__":
    unittest.main()
