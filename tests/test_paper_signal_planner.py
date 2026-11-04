"""Safe paper-trading signal planner tests; never connect to a broker."""

from tradingagents.agents.paper_portfolio import PaperPortfolio
from tradingagents.agents.paper_signal_planner import plan_paper_signal


def _state(rating="Buy"):
    return {
        "company_of_interest": "NVDA",
        "trade_date": "2026-11-03",
        "final_rating": rating,
        "final_trade_decision": f"**Rating**: {rating}",
        "market_report": "Technical analysis available",
        "investment_plan": "Debate complete",
        "trader_investment_plan": "Proposal complete",
    }


def _plan(portfolio, rating="Buy", **changes):
    kwargs = {
        "state": _state(rating),
        "portfolio": portfolio,
        "prices_pln": {"NVDA": "100"},
        "quote_date": "2026-11-03",
        "quote_source": "test-fixture",
    }
    kwargs.update(changes)
    return plan_paper_signal(**kwargs)


def test_buy_is_only_proposal_not_execution():
    p = PaperPortfolio()
    result = _plan(p)
    assert result["status"] == "PROPOSED"
    assert result["action"] == "BUY"
    assert result["quantity"] == 9
    assert p.cash_pln == p.initial_cash_pln
    assert p.transactions == []


def test_overweight_capped_at_twenty_percent():
    p = PaperPortfolio()
    result = _plan(p, rating="Overweight")
    assert result["quantity"] == 19
    assert result["action"] == "BUY"


def test_existing_holding_cannot_be_overallocated():
    p = PaperPortfolio()
    p.trade(side="BUY", ticker="NVDA", quantity=18, price_pln="100",
            trade_id="b1", date="2026-11-03")
    result = _plan(p, rating="Overweight")
    assert result["quantity"] <= 2


def test_underweight_with_no_holding_does_not_short():
    result = _plan(PaperPortfolio(), rating="Underweight")
    assert result["action"] == "HOLD"


def test_underweight_halves_existing_holding():
    p = PaperPortfolio()
    p.trade(side="BUY", ticker="NVDA", quantity=5, price_pln="100",
            trade_id="b1", date="2026-11-03")
    result = _plan(p, rating="Underweight")
    assert (result["action"], result["quantity"]) == ("SELL", 3)


def test_equity_floor_blocks_new_buys():
    p = PaperPortfolio()
    p.trade(side="BUY", ticker="NVDA", quantity=10, price_pln="100",
            trade_id="b1", date="2026-11-03")
    result = _plan(p, rating="Buy", prices_pln={"NVDA": "0.10"})
    # With another mark for the same ticker, cash 8997.50 + position 1.00 <= 9000.
    assert result["status"] == "BLOCKED"


def test_stale_quotes_need_review():
    result = _plan(PaperPortfolio(), quote_date="2026-11-02")
    assert result["status"] == "REVIEW"


def test_missing_quote_provenance_needs_review():
    result = _plan(PaperPortfolio(), quote_source="")
    assert result["status"] == "REVIEW"


def test_ambiguous_final_rating_needs_review():
    state = _state()
    state["final_trade_decision"] = "**Rating**: Sell"
    result = _plan(PaperPortfolio(), state=state)
    assert result["status"] == "REVIEW"


def test_missing_mark_to_market_for_other_holding_needs_review():
    p = PaperPortfolio()
    p.trade(side="BUY", ticker="AAPL", quantity=2, price_pln="100",
            trade_id="b1", date="2026-11-03")
    assert _plan(p)["status"] == "REVIEW"


def test_never_uses_actual_broker():
    p = PaperPortfolio()
    _plan(p)
    assert not p.transactions
