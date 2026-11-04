"""Tests for deterministic paper-trading decision audits (no LLM calls)."""

from tradingagents.agents.decision_audit import audit_decision, audit_repeated_runs


def _state(rating="Hold", ticker="NVDA", date="2026-11-03"):
    return {
        "company_of_interest": ticker,
        "trade_date": date,
        "final_rating": rating,
        "final_trade_decision": f"**Rating**: {rating}\n\n**Investment Thesis**: test",
        "market_report": "Prices and volume reviewed",
        "investment_plan": "Research manager recommendation",
        "trader_investment_plan": "No order",
    }


def test_valid_state_passes():
    result = audit_decision(_state(), expected_ticker="NVDA", expected_date="2026-11-03")
    assert result["status"] == "PASS"


def test_rating_mismatch_is_review():
    state = _state("Overweight")
    state["final_trade_decision"] = "**Rating**: Underweight"
    result = audit_decision(state)
    assert result["status"] == "REVIEW"
    assert any("disagrees" in x for x in result["issues"])


def test_missing_market_report_is_review():
    state = _state()
    state["market_report"] = ""
    assert audit_decision(state)["status"] == "REVIEW"


def test_opposite_repeated_ratings_are_flagged():
    result = audit_repeated_runs([_state("Overweight"), _state("Underweight")])
    assert result["status"] == "REVIEW"
    assert result["conflicts"][0]["ratings"] == ["Overweight", "Underweight"]


def test_different_dates_are_not_compared():
    result = audit_repeated_runs([_state("Overweight"), _state("Underweight", date="2026-11-02")])
    assert result["status"] == "PASS"


def test_missing_ticker_does_not_false_match():
    state = _state()
    state["company_of_interest"] = ""
    assert audit_decision(state, expected_ticker="NVDA")["status"] == "REVIEW"
