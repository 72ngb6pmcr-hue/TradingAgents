"""Causal links are transparent hypotheses; frequencies never backfill future news."""
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tradingagents.agents.causal_event_library import (
    empirical_probability,
    evaluate_event,
    historical_analogues,
    trace_impact,
)

KNOWLEDGE = Path(__file__).resolve().parents[1] / "tradingagents" / "knowledge"


def load(name):
    return json.loads((KNOWLEDGE / name).read_text(encoding="utf-8"))


def test_oil_outage_propagates_both_winners_and_losers():
    graph = load("supply_chain_graph.json")
    paths = trace_impact(graph, changed_node="crude_supply", initial_direction=-1)
    assert any(p["node"] == "oil_price" and p["hypothesized_direction"] == "UP" for p in paths)
    assert any(p["node"] == "oil_equity" and p["hypothesized_direction"] == "UP" for p in paths)
    assert any(p["node"] == "airline_equity" and p["hypothesized_direction"] == "DOWN" for p in paths)
    assert all(p["status"] == "QUALITATIVE_HYPOTHESIS_NOT_CALIBRATED" for p in paths)
    assert all(p["conditions"] for p in paths)


def test_invalid_graph_or_depth_does_not_emit_prediction():
    graph = load("supply_chain_graph.json")
    with pytest.raises(ValueError):
        trace_impact(graph, changed_node="wrong", initial_direction=1)
    with pytest.raises(ValueError):
        trace_impact(graph, changed_node="oil_price", initial_direction=0)
    with pytest.raises(ValueError):
        trace_impact(graph, changed_node="oil_price", initial_direction=1, max_depth=0)


def test_retrospective_history_without_earliest_publication_not_tradeable():
    casebook = load("historical_event_cases.json")
    assert len(casebook["historical_cases"]) >= 3
    assert not historical_analogues(
        casebook, event_type="PHYSICAL_OIL_OUTAGE", as_of="2026-11-12T04:00:00+01:00"
    )


def test_only_published_point_in_time_analogues():
    casebook = {
        "historical_cases": [
            {"id": "one", "event_type": "OIL_DEMAND_SHOCK",
             "first_public_at": "2020-01-01T12:00:00Z"},
            {"id": "future", "event_type": "OIL_DEMAND_SHOCK",
             "first_public_at": "2026-11-13T12:00:00Z"},
        ]
    }
    results = historical_analogues(casebook, event_type="OIL_DEMAND_SHOCK",
                                   as_of="2026-11-12T04:00:00+01:00")
    assert [r["id"] for r in results] == ["one"]


def sample(outcome, i, published="2020-01-01T12:00:00Z",
           settled="2020-01-10T12:00:00Z"):
    return {
        "event_id": str(i), "event_type": "OIL_SUPPLY_RISK_ONLY",
        "instrument": "BRENT", "horizon_days": 5,
        "published_at": published, "outcome_available_at": settled,
        "direction_correct": outcome,
    }


def test_small_sample_cannot_claim_probability():
    r = empirical_probability([sample(True, 1)], event_type="OIL_SUPPLY_RISK_ONLY",
                              instrument="BRENT", horizon_days=5,
                              as_of="2026-11-12T04:00:00Z")
    assert r["probability"] is None
    assert r["status"] == "INSUFFICIENT_VALID_OUTCOMES"


def test_future_settlement_and_duplicate_cannot_inflate_sample():
    items = [sample(True, i) for i in range(19)]
    items.append(sample(True, 19, settled="2026-11-13T12:00:00Z"))
    items.append(sample(True, 5))
    r = empirical_probability(items, event_type="OIL_SUPPLY_RISK_ONLY",
                              instrument="BRENT", horizon_days=5,
                              as_of="2026-11-12T04:00:00Z")
    assert r["probability"] is None
    assert r["n"] <= 19


def test_known_synthetic_20_case_frequency_is_not_forecast():
    items = [sample(i < 12, i) for i in range(20)]
    r = empirical_probability(items, event_type="OIL_SUPPLY_RISK_ONLY",
                              instrument="BRENT", horizon_days=5,
                              as_of="2026-11-12T04:00:00Z")
    assert r["status"] == "UNVALIDATED_HISTORICAL_FREQUENCY"
    assert r["probability"] == 0.6
    low, high = r["confidence_interval_95pct"]
    assert low < 0.6 < high


def test_real_casebook_has_no_fake_forecast():
    r = evaluate_event(
        event_type="PHYSICAL_OIL_OUTAGE", as_of=datetime(2026, 11, 12, tzinfo=UTC).isoformat(),
        changed_node="crude_supply", direction=-1,
        instrument="BRENT",
    )
    assert r["documented_historical_cases"] == 2
    assert r["point_in_time_usable_analogues"] == 0
    assert r["probability_estimate"]["probability"] is None
    assert r["trade_signal"] is None
