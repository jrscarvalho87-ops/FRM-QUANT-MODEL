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
        self.assertIn("Executar backtest",response.text)
        self.assertIn("Ordens simuladas",response.text)
        self.assertIn("Input",response.text)
        self.assertIn("Modelo",response.text)

    def test_poc_lab_is_html(self):
        response=self.client.get("/poc")
        self.assertEqual(response.status_code,200)
        self.assertIn("text/html",response.headers.get("content-type",""))
        self.assertIn("Volume Profile",response.text)
        self.assertIn("Fibonacci",response.text)

    def test_poc_rejects_unconfirmed_latest_candle(self):
        bars=[{"ts":900000,"low":"100","high":"110","volume_contracts":"10","confirmed":True},
              {"ts":1800000,"low":"100","high":"111","volume_contracts":"10","confirmed":False}]
        response=self.client.post("/api/research/poc",json={
            "candles":bars,"anchor_ts":900000,"asof_ts":1800000,"bar":"15m"})
        self.assertEqual(response.status_code,400)

    def test_poc_rejects_invalid_timeframe(self):
        response=self.client.post("/api/research/poc",json={
            "candles":[],"anchor_ts":900000,"asof_ts":900000,"bar":"5X"})
        self.assertEqual(response.status_code,400)

    def test_automatic_candidate_backtest_empty_sample(self):
        response=self.client.post("/api/research/candidate-backtest",json={
            "candles":[],"bar":"15m","candidate_settings":{},
            "execution_settings":{}})
        self.assertEqual(response.status_code,200,response.text)
        data=response.json()
        self.assertEqual(data["candidate_model"]["signal_count"],0)
        self.assertEqual(data["execution"]["summary"]["closed_trades"],0)
        self.assertEqual(data["bootstrap"]["status"],"insufficient_sample")

    def test_automatic_candidate_backtest_rejects_unconfirmed(self):
        bars=[{"ts":900000,"open":"100","high":"101","low":"99",
               "close":"100","confirmed":False}]
        response=self.client.post("/api/research/candidate-backtest",json={
            "candles":bars,"bar":"15m"})
        self.assertEqual(response.status_code,400)

    def test_automatic_candidate_backtest_rejects_unapproved_setting(self):
        response=self.client.post("/api/research/candidate-backtest",json={
            "candles":[],"candidate_settings":{"secret_leverage":100}})
        self.assertEqual(response.status_code,400)

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


    def test_poc_endpoint_ignores_future_candle(self):
        bars=[
            {"ts":900000,"open":"100","high":"110","low":"100","close":"105","volume_contracts":"100","confirmed":True},
            {"ts":1800000,"open":"100","high":"110","low":"100","close":"105","volume_contracts":"100","confirmed":True},
            {"ts":2700000,"open":"140","high":"150","low":"140","close":"145","volume_contracts":"100000","confirmed":True},
        ]
        response=self.client.post("/api/research/poc",json={
            "candles":bars,"anchor_ts":900000,"asof_ts":1800000,
            "bar":"15m","bins":8,"zero_price":110,"hundred_price":100,"side":"long"})
        self.assertEqual(response.status_code,200,response.text)
        report=response.json()
        self.assertLess(report["poc_price_approx"],110)
        self.assertEqual(report["future_bars_ignored"],1)
        self.assertIs(report["is_true_traded_volume_poc"],False)

    def test_poc_endpoint_rejects_bad_anchor(self):
        bars=[{"ts":900000,"low":"100","high":"110","volume_contracts":"10","confirmed":True}]
        response=self.client.post("/api/research/poc",json={
            "candles":bars,"anchor_ts":1800000,"asof_ts":2700000})
        self.assertEqual(response.status_code,400)

    def test_invalid_instrument_rejected_before_api_call(self):
        response=self.client.get("/api/okx/history?inst_id=BTC-FAKE")
        self.assertEqual(response.status_code,400)


if __name__=="__main__":
    unittest.main()
