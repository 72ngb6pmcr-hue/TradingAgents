"""Offline regression tests for point-in-time demand/supply and correlations."""
import math
import unittest
from tradingagents.agents.structural_market import supply_demand_gap, lagged_return_correlations

def obs(day, field, value, published=None):
    return {"date": day, "published_at": published or day + "T12:00:00+00:00",
            "source_url": "https://example.org/data", "unit": "tonnes", field: value}

class StructuralMarketTests(unittest.TestCase):
    def test_gap(self):
        demand = [obs("2026-11-01", "value", 120)]
        supply = [obs("2026-11-01", "value", 90)]
        self.assertEqual(supply_demand_gap(demand, supply, "2026-11-11")[0]["gap_pct_of_demand"], 25)

    def test_no_lookahead_by_publication(self):
        demand = [obs("2026-11-01", "value", 120, "2026-11-12T00:00:00Z")]
        supply = [obs("2026-11-01", "value", 90)]
        self.assertEqual(supply_demand_gap(demand, supply, "2026-11-11"), [])

    def test_unit_mismatch(self):
        demand = [obs("2026-11-01", "value", 120)]
        supply = [dict(obs("2026-11-01", "value", 90), unit="kg")]
        with self.assertRaises(ValueError):
            supply_demand_gap(demand, supply, "2026-11-11")

    def test_insufficient_prices_do_not_invent_correlations(self):
        a = [obs("2026-11-01", "close", 100)]
        self.assertIsNone(lagged_return_correlations(a, a, "2026-11-11")[0]["correlation"])

    def test_constant_prices_no_spurious_correlation(self):
        a = [obs(f"2026-10-{i:02}", "close", 100) for i in range(1, 20)]
        b = [obs(f"2026-10-{i:02}", "close", 200 + i) for i in range(1, 20)]
        self.assertEqual(lagged_return_correlations(a, b, "2026-11-11")[0]["status"], "ZERO_VARIANCE")

    def test_reject_nan(self):
        with self.assertRaises(ValueError):
            supply_demand_gap([obs("2026-11-01", "value", math.nan)],
                              [obs("2026-11-01", "value", 90)], "2026-11-11")

if __name__ == "__main__":
    unittest.main()
