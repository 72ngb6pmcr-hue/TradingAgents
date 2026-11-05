"""No live orders: deterministic 100k paper game fills with source provenance."""
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from tradingagents.agents.paper_game_runner import run_game
from tradingagents.agents.paper_portfolio import PaperPortfolio

WARSAW = ZoneInfo("Europe/Warsaw")
THURSDAY = datetime(2026, 11, 5, 19, 45, tzinfo=WARSAW)


def strategy():
    return {
        "mode": "PAPER_ONLY",
        "schema_version": 1, "initial_cash_pln": "100000.00",
        "event_reserve_pln": "20000.00",
        "max_position_weight": 0.35,
        "fill_method": "SAME_DAY_UNADJUSTED_CLOSE_EOD_PROXY_NOT_EXECUTABLE",
        "one_time_initial_targets": [
            {"ticker": "VWCE.DE", "ccy": "EUR", "target_pln": "35000.00",
             "market": "XETRA", "role": "Global"},
            {"ticker": "ETFBW20TR.WA", "ccy": "PLN", "target_pln": "10000.00",
             "market": "GPW", "role": "Poland"},
        ],
    }


def quote(ticker, day):
    return {
        "symbol": ticker, "date": day.isoformat(), "close_native": "100.00",
        "volume": "3000", "source": "SYNTHETIC_TEST_ONLY", "executable": False,
    }


def fx(ccy, day):
    return {
        "ccy": ccy, "date": day.isoformat(),
        "pln_per_unit": "4.50" if ccy == "EUR" else "1",
        "source": "SYNTHETIC_TEST_ONLY",
    }


def test_initial_paper_fills_are_replayable_and_idempotent():
    portfolio = PaperPortfolio(initial_cash_pln=Decimal("100000"))
    first = run_game(portfolio, strategy(), now=THURSDAY, close_loader=quote, fx_loader=fx)
    assert first["status"] == "EOD_PAPER_RECONCILED"
    assert first["trade_executed"] is False
    assert first["simulated_fills"] == 2
    assert all(tx["broker_order_sent"] is False for tx in first["fills"])
    assert portfolio.cash_pln >= Decimal("20000")
    assert portfolio.cash_pln < Decimal("100000")
    assert all(tx["fee_pln"] != "0.00" for tx in portfolio.transactions)
    assert Decimal(portfolio.valuation({"VWCE.DE": "450", "ETFBW20TR.WA": "100"})["total_pnl_pln"]) < 0
    second = run_game(portfolio, strategy(), now=THURSDAY, close_loader=quote, fx_loader=fx)
    assert second["simulated_fills"] == 0
    assert len(portfolio.transactions) == 2


def test_missing_price_never_creates_fill():
    portfolio = PaperPortfolio(initial_cash_pln=Decimal("100000"))

    def broken(*_):
        raise ConnectionError("no public price")

    result = run_game(portfolio, strategy(), now=THURSDAY, close_loader=broken, fx_loader=fx)
    assert result["status"] == "PARTIAL_DATA"
    assert portfolio.cash_pln == Decimal("100000")
    assert portfolio.transactions == []
    assert all(x["status"] == "PENDING_MISSING_OR_INVALID_DATA" for x in result["errors"])


def test_no_backdating_fills_before_decision_time():
    portfolio = PaperPortfolio(initial_cash_pln=Decimal("100000"))
    result = run_game(portfolio, strategy(), now=datetime(2026, 11, 5, 17, 30, tzinfo=WARSAW),
                      close_loader=quote, fx_loader=fx)
    assert result["status"] == "WAIT_FOR_COMPLETED_SESSION"
    assert portfolio.transactions == []


def test_reject_fx_wrong_date():
    portfolio = PaperPortfolio(initial_cash_pln=Decimal("100000"))

    def stale(ccy, day):
        return {"ccy": ccy, "date": "2026-11-04", "pln_per_unit": "4.5"}

    result = run_game(portfolio, strategy(), now=THURSDAY, close_loader=quote, fx_loader=stale)
    assert result["simulated_fills"] == 0
    assert portfolio.cash_pln == Decimal("100000")


def test_no_qty_if_price_too_large():
    portfolio = PaperPortfolio(initial_cash_pln=Decimal("100000"))

    def expensive(ticker, day):
        return {**quote(ticker, day), "close_native": "40000"}

    result = run_game(portfolio, strategy(), now=THURSDAY, close_loader=expensive, fx_loader=fx)
    assert result["simulated_fills"] == 0
    assert portfolio.cash_pln == Decimal("100000")
