"""Read-only end-to-end preview; fake Yahoo data to avoid network and LLM."""

import json
from datetime import date, timedelta

import pandas as pd
import pytest

from tradingagents.agents.paper_portfolio import PaperPortfolio
from tradingagents.agents.paper_preview import preview_report

DATE = (date.today() - timedelta(days=1)).isoformat()


def loader(ticker, date_string):
    values = {
        "NVDA": 206.69,
        "USDPLN=X": 4.00,
        "AAPL": 220.00,
    }
    return pd.DataFrame(
        {"Date": [DATE], "Close": [values[ticker]]}
    ) if ticker in values else pd.DataFrame(columns=["Date", "Close"])


def report(rating="Underweight"):
    state = {
        "company_of_interest": "NVDA",
        "trade_date": DATE,
        "final_rating": rating,
        "final_trade_decision": f"**Rating**: {rating}",
        "market_report": "Market data",
        "investment_plan": "Research debate",
        "trader_investment_plan": "Transaction proposal",
    }
    return {"ticker": "NVDA", "analysis_date": DATE, "state": state}


def test_underweight_with_empty_account_does_not_short_or_execute():
    portfolio = PaperPortfolio()
    result = preview_report(report(), portfolio, {"NVDA": "USD"}, mark_loader=loader)
    assert result["mode"] == "PAPER_PREVIEW_ONLY"
    assert result["proposal"]["action"] == "HOLD"
    assert result["trade_executed"] is False
    assert portfolio.cash_pln == portfolio.initial_cash_pln
    assert portfolio.transactions == []


def test_overweight_shows_buy_but_does_not_record_fill():
    portfolio = PaperPortfolio()
    result = preview_report(report("Overweight"), portfolio, {"NVDA": "USD"}, mark_loader=loader)
    assert result["proposal"]["action"] == "BUY"
    assert result["proposal"]["quantity"] > 0
    assert result["market_marks"]["NVDA"]["price_pln"] == "826.76"
    assert portfolio.transactions == []


def test_ticker_mismatch_rejected():
    r = report()
    r["ticker"] = "AAPL"
    with pytest.raises(ValueError, match="disagrees"):
        preview_report(r, PaperPortfolio(), {"NVDA": "USD"}, mark_loader=loader)


def test_missing_holding_currency_rejected():
    portfolio = PaperPortfolio()
    portfolio.trade(side="BUY", ticker="AAPL", quantity=1, price_pln="100",
                    trade_id="demo-1", date=DATE)
    with pytest.raises(ValueError, match="Explicit quote currencies"):
        preview_report(report(), portfolio, {"NVDA": "USD"}, mark_loader=loader)


def test_missing_quote_prevents_preview():
    def no_price(ticker, when):
        if ticker == "NVDA":
            return pd.DataFrame(columns=["Date", "Close"])
        return loader(ticker, when)
    with pytest.raises(ValueError, match="Missing dated close"):
        preview_report(report(), PaperPortfolio(), {"NVDA": "USD"}, mark_loader=no_price)


def test_all_holdings_are_valued():
    portfolio = PaperPortfolio()
    portfolio.trade(side="BUY", ticker="AAPL", quantity=1, price_pln="100",
                    trade_id="demo-1", date=DATE)
    result = preview_report(report(), portfolio, {"NVDA": "USD", "AAPL": "USD"}, mark_loader=loader)
    assert result["portfolio"]["holdings"]["AAPL"]["market_value_pln"] == "880.00"


def test_conflicting_rating_causes_review():
    r = report("Overweight")
    r["state"]["final_trade_decision"] = "**Rating**: Underweight"
    result = preview_report(r, PaperPortfolio(), {"NVDA": "USD"}, mark_loader=loader)
    assert result["proposal"]["status"] == "REVIEW"
    assert result["proposal"]["action"] == "HOLD"
