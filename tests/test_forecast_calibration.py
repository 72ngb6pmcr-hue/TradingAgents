import unittest
from tradingagents.agents.forecast_calibration import evaluate

def forecast(p=0.75):
    return {"id":"f1","issued_at":"2026-11-01T10:00:00Z",
            "resolves_at":"2026-11-05T10:00:00Z",
            "event":"Price of X exceeds fixed threshold at deadline",
            "probability":p,"evidence":[{"url":"https://example.org/source",
            "published_at":"2026-10-31T10:00:00Z"}]}

def outcome(value=True):
    return {"forecast_id":"f1","occurred":value,
            "verified_at":"2026-11-05T12:00:00Z",
            "source_url":"https://example.org/settlement"}

class ForecastCalibrationTests(unittest.TestCase):
    def test_no_forecasts_no_score(self):
        r=evaluate([],[],"2026-11-11T00:00:00Z")
        self.assertIsNone(r["brier_score"])
        self.assertEqual(r["status"],"EXPERIMENTAL_UNCALIBRATED")
    def test_resolved_brier(self):
        r=evaluate([forecast()],[outcome()],"2026-11-11T00:00:00Z")
        self.assertEqual(r["brier_score"],0.0625)
        self.assertTrue(r["scored"][0]["priority"])
    def test_pending_not_scored(self):
        r=evaluate([forecast()],[outcome()],"2026-11-04T00:00:00Z")
        self.assertEqual(r["resolved_count"],0)
    def test_future_evidence_rejected(self):
        f=forecast()
        f["evidence"][0]["published_at"]="2026-11-02T00:00:00Z"
        with self.assertRaises(ValueError):
            evaluate([f],[],"2026-11-11T00:00:00Z")
    def test_invalid_probability(self):
        with self.assertRaises(ValueError):
            evaluate([forecast(1.1)],[],"2026-11-11T00:00:00Z")
    def test_no_future_settlement(self):
        r=evaluate([forecast()],[outcome()],"2026-11-05T11:00:00Z")
        self.assertEqual(r["resolved_count"],0)

if __name__=="__main__":
    unittest.main()
