"""Deterministic, offline regression checks for scenario graph."""
import unittest
from tradingagents.agents.supply_chain_forecast import SECTORS, analyze

class SupplyChainForecastTests(unittest.TestCase):
    def test_ten_sectors_no_fabricated_signals(self):
        result = analyze([])
        self.assertEqual(len(SECTORS), 10)
        self.assertEqual(result["observations_count"], 0)
        self.assertEqual(result["scenarios"], [])
        self.assertEqual(result["mode"], "RESEARCH_ONLY_NO_ORDERS")

    def test_observation_requires_provenance(self):
        with self.assertRaises(ValueError):
            analyze([{"node": "copper", "direction": "decrease"}])

    def test_direction_not_stock_prediction(self):
        obs = dict(node="copper", date="2026-11-11T10:00:00Z",
                   source_url="https://example.org/disclosure", metric="production",
                   unit="tonnes", value=90, baseline=100, direction="decrease")
        report = analyze([obs])
        self.assertIn("power_grids", report["scenarios"][0]["potential_downstream"])
        self.assertIsNone(report["scenarios"][0]["price_prediction"])
        self.assertIsNone(report["scenarios"][0]["equity_signal"])

    def test_reject_unknown_node(self):
        obs = dict(node="unknown", date="2026-11-11", source_url="https://example.org",
                   metric="output", unit="t", value=1, baseline=2, direction="decrease")
        with self.assertRaises(ValueError):
            analyze([obs])

if __name__ == "__main__":
    unittest.main()
