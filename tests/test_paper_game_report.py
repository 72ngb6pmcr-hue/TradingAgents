"""Offline checks for receipt-backed reporting; no prices or network."""
import json
from decimal import Decimal

import pytest

from tradingagents.agents.paper_game_report import build_report
from tradingagents.agents.paper_portfolio import PaperPortfolio


def setup_game(tmp_path):
    (tmp_path / "strategy.json").write_text(json.dumps({
        "mode": "PAPER_ONLY", "season": "2026-11-05-paper-game-100k"
    }))
    portfolio = PaperPortfolio(initial_cash_pln=Decimal("100000"))
    portfolio.save(tmp_path / "portfolio.json")
    return portfolio


def test_cash_only_is_not_invented_performance(tmp_path):
    setup_game(tmp_path)
    report = build_report(tmp_path)
    assert report["cash_pln"] == "100000.00"
    assert report["confirmed_paper_transactions"] == 0
    assert report["equity_pln"] is None
    assert report["day_change_pln"] is None


def test_rejects_unreceipted_trade(tmp_path):
    portfolio = setup_game(tmp_path)
    portfolio.trade(side="BUY", ticker="VWCE.DE", quantity=1,
                    price_pln="500", trade_id="one", date="2026-11-06")
    portfolio.save(tmp_path / "portfolio.json")
    with pytest.raises(ValueError, match="do not match"):
        build_report(tmp_path)


def test_dated_valuation_with_verified_provenance(tmp_path):
    portfolio = setup_game(tmp_path)
    tx = portfolio.trade(side="BUY", ticker="VWCE.DE", quantity=1,
                         price_pln="500", trade_id="one", date="2026-11-06")
    portfolio.save(tmp_path / "portfolio.json")
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    (receipts / "2026-11-06.json").write_text(json.dumps({
        "session_date": "2026-11-06",
        "fills": [{"status": "PAPER_FILL_EOD_PROXY_NOT_EXECUTABLE",
                   **tx, "broker_order_sent": False,
                   "quote_and_fx": {
                       "quote": {"date": "2026-11-06", "executable": False,
                                 "source": "SYNTHETIC_TEST_ONLY"},
                       "fx": {"date": "2026-11-06",
                              "source": "SYNTHETIC_TEST_ONLY"}}}],
        "valuation": portfolio.valuation({"VWCE.DE": "500"})
    }))
    report = build_report(tmp_path)
    assert report["confirmed_paper_transactions"] == 1
    assert report["total_pnl_pln"] == "-1.25"
    assert report["day_change_pln"] is None
