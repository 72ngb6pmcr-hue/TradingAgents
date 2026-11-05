"""Independent agent critique never turns uncertainty into a trade."""
from tradingagents.agents.independent_agent_review import independent_review


def proposal(side="BUY"):
    return {
        "ticker": "BDX.WA", "action": side, "status": "PROPOSED",
        "quantity": 2, "price_pln": "700.00",
        "quote_source": "Independent verified executable manual hypothetical fill",
    }


def observation(score=3, momentum="4", vol="2"):
    return {
        "ticker": "BDX.WA", "status": "OBSERVATION", "strength_score": score,
        "momentum_20d_pct": momentum, "daily_volatility_20d_pct": vol,
    }


def test_independent_agreement_is_not_automatic_execution():
    result = independent_review(proposal(), observation())
    assert result["status"] == "MANUAL_REVIEW_REQUIRED"
    assert result["trade_executed"] is False
    assert result["estimated_position_shock_loss_pln"] == "140.00"


def test_bearish_market_blocks_buy_for_manual_reevaluation():
    result = independent_review(proposal(), observation(score=0, momentum="-3"))
    assert result["status"] == "REVIEW"
    assert any("conflicts" in x for x in result["issues"])


def test_volatile_instrument_blocks_new_buy():
    result = independent_review(proposal(), observation(vol="6"))
    assert result["status"] == "REVIEW"


def test_missing_market_evidence_fails_closed_for_buy():
    result = independent_review(proposal(), None)
    assert result["status"] == "REVIEW"


def test_historical_adjusted_close_is_not_executable_quote():
    p = proposal()
    p["quote_source"] = "Yahoo Finance adjusted daily close (indicative, not a fill quote)"
    result = independent_review(p, observation())
    assert result["status"] == "REVIEW"
    assert any("executable" in x for x in result["issues"])


def test_sell_remains_available_for_manual_risk_reduction():
    result = independent_review(proposal("SELL"), None)
    assert result["status"] == "MANUAL_REVIEW_REQUIRED"
    assert result["trade_executed"] is False


def test_invalid_inputs_fail_closed():
    p = proposal()
    p["quantity"] = 0.5
    result = independent_review(p, observation())
    assert result["status"] == "REVIEW"
    assert result["estimated_position_shock_loss_pln"] is None


def test_hold_does_not_become_a_buy():
    p = proposal()
    p["action"] = "HOLD"
    assert independent_review(p, observation())["action"] == "HOLD"


def test_wrong_ticker_is_not_accepted():
    o = observation()
    o["ticker"] = "NVDA"
    assert independent_review(proposal(), o)["status"] == "REVIEW"
