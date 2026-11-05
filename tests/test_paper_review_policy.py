"""Human paced policy: deterministic fixed-clock tests."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from tradingagents.agents.paper_portfolio import PaperPortfolio
from tradingagents.agents.paper_review_policy import evaluate_review_window

TZ = ZoneInfo("Europe/Warsaw")
BUY = {"status": "PROPOSED", "action": "BUY", "ticker": "NVDA", "quantity": 1}


def check(hour, *, day=4, proposal=None, portfolio=None):
    return evaluate_review_window(proposal or BUY, portfolio or PaperPortfolio(),
                                  now=datetime(2026, 11, day, hour, tzinfo=TZ))


def test_morning_is_review_only():
    r = check(10)
    assert r["status"] == "READY_FOR_HUMAN_REVIEW"
    assert not r["automatic_execution"]


def test_evening_available():
    assert check(19)["status"] == "READY_FOR_HUMAN_REVIEW"


def test_midday_not_available():
    assert check(15)["status"] == "WAIT_FOR_SESSION"


def test_weekend_not_available():
    assert check(10, day=7)["status"] == "WAIT_FOR_SESSION"


def test_no_action_is_not_a_trade():
    assert check(10, proposal={"status": "HOLD", "action": "HOLD"})["status"] == "NO_ACTION"


def test_cooldown_for_same_ticker():
    p = PaperPortfolio()
    p.trade(side="BUY", ticker="NVDA", quantity=1, price_pln=100, trade_id="a", date="2026-11-02")
    assert check(10, portfolio=p)["status"] == "WAIT_COOLDOWN"


def test_weekly_trade_cap():
    p = PaperPortfolio()
    p.trade(side="BUY", ticker="AAPL", quantity=1, price_pln=100, trade_id="a", date="2026-11-02")
    p.trade(side="BUY", ticker="MSFT", quantity=1, price_pln=100, trade_id="b", date="2026-11-03")
    assert check(19, portfolio=p)["status"] == "WAIT_COOLDOWN"


def test_old_transaction_not_blocking():
    p = PaperPortfolio()
    p.trade(side="BUY", ticker="NVDA", quantity=1, price_pln=100, trade_id="a", date="2026-10-20")
    assert check(10, portfolio=p)["status"] == "READY_FOR_HUMAN_REVIEW"


def test_gate_is_read_only():
    p = PaperPortfolio()
    check(10, portfolio=p)
    assert not p.transactions and str(p.cash_pln) == "10000.00"


def test_naive_datetime_rejected():
    with pytest.raises(ValueError, match="aware"):
        evaluate_review_window(BUY, PaperPortfolio(), now=datetime(2026, 11, 4, 10))
