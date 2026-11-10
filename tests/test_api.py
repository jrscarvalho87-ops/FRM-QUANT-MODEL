"""HTTP smoke tests without requesting live OKX data."""
import unittest
from fastapi.testclient import TestClient
from app import app


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client=TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def test_root_is_html_dashboard(self):
        response=self.client.get("/")
        self.assertEqual(response.status_code,200)
        self.assertIn("text/html",response.headers.get("content-type",""))
        self.assertIn("RFM Quant",response.text)

    def test_watchlist_has_requested_gram(self):
        result=self.client.get("/api/watchlist").json()
        self.assertEqual(result["count"],31)
        self.assertIn("GRAM",result["symbols"])

    def test_fibonacci_arithmetic_is_not_mislabeled(self):
        result=self.client.get("/api/research/fibonacci-rr-check").json()
        self.assertAlmostEqual(result["examples"][0]["rr"],3.0,places=4)

    def test_simulation_http_endpoint(self):
        bars=[
            {"ts":900000,"open":"100","high":"101","low":"99","close":"100","confirmed":True},
            {"ts":1800000,"open":"100","high":"112","low":"99","close":"100","confirmed":True},
        ]
        signal={"signal_ts":900000,"side":"long","entry":100,"stop":95,"take":110}
        response=self.client.post("/api/research/simulate",json={"candles":bars,"signals":[signal]})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()["summary"]["closed_trades"],1)

    def test_invalid_instrument_rejected_before_api_call(self):
        response=self.client.get("/api/okx/history?inst_id=BTC-FAKE")
        self.assertEqual(response.status_code,400)


if __name__=="__main__":
    unittest.main()
