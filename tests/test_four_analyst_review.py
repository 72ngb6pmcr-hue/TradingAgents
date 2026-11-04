"""Four-agent report builder tests: no network or LLM requests."""
from tradingagents.agents.four_analyst_review import ANALYSTS, saved_report
from tradingagents.agents.paper_review_policy import evaluate_review_window
from tradingagents.agents.paper_portfolio import PaperPortfolio
from datetime import datetime
from zoneinfo import ZoneInfo


def test_all_four_analysts_selected():
    assert ANALYSTS == ("market", "social", "news", "fundamentals")


def test_saved_report_keeps_preview_fields():
    state = {"market_report": "market", "news_report": "news",
             "sentiment_report": "sentiment", "fundamentals_report": "fund",
             "investment_plan": "plan", "trader_investment_plan": "trade plan",
             "final_trade_decision": "**Rating**: Hold", "final_rating": "Hold"}
    result = saved_report("nvda", "2026-11-03", state, "Hold")
    assert result["state"]["market_report"] == "market"
    assert result["state"]["fundamentals_report"] == "fund"
    assert result["state"]["final_rating"] == "Hold"
    assert result["trade_executed"] is False
    assert result["ticker"] == "NVDA"


def test_saved_report_does_not_expose_unrelated_state():
    result = saved_report("NVDA", "2026-11-03",
                          {"final_rating": "Hold", "secret_api_key": "SENSITIVE"}, "Hold")
    assert "secret_api_key" not in str(result)


def test_manual_exit_review_not_blocked_by_weekly_cap():
    p = PaperPortfolio()
    p.trade(side="BUY", ticker="NVDA", quantity=1, price_pln=100, trade_id="n1", date="2026-11-02")
    p.trade(side="BUY", ticker="AAPL", quantity=1, price_pln=100, trade_id="a1", date="2026-11-03")
    proposal = {"status": "PROPOSED", "action": "SELL", "ticker": "NVDA", "quantity": 1}
    result = evaluate_review_window(proposal, p, now=datetime(2026, 11, 4, 19, tzinfo=ZoneInfo("Europe/Warsaw")))
    assert result["status"] == "READY_FOR_HUMAN_REVIEW"
    assert p.positions["NVDA"].quantity == 1

def test_truncated_report_is_labelled_review_before_saving():
    state = {
        "market_report": "market", "investment_plan": "plan",
        "trader_investment_plan": "trader",
        "final_rating": "Hold",
        "final_trade_decision": "**Rating**: Hold\\nTrailing stop (~69",
    }
    result = saved_report("BDX.WA", "2026-11-03", state, "Hold")
    assert result["quality_audit"]["status"] == "REVIEW"
    assert result["approved_for_paper_planning"] is False


def test_complete_report_marked_pass_by_audit():
    state = {
        "market_report": "market", "investment_plan": "plan",
        "trader_investment_plan": "trader",
        "final_rating": "Hold",
        "final_trade_decision": "**Rating**: Hold\\nNo position change is proposed.",
    }
    result = saved_report("BDX.WA", "2026-11-03", state, "Hold")
    assert result["quality_audit"]["status"] == "PASS"
    assert result["approved_for_paper_planning"] is True
