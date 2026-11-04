"""Deterministic paper-portfolio tests; no API calls or real orders."""

from decimal import Decimal

import pytest

from tradingagents.agents.paper_portfolio import PaperPortfolio


def test_starts_with_ten_thousand_zloty():
    ledger = PaperPortfolio()
    assert ledger.valuation({})["equity_pln"] == "10000.00"


def test_buy_charges_fee_and_updates_cash():
    p = PaperPortfolio()
    tx = p.trade(side="BUY", ticker="NVDA", quantity=2, price_pln="100",
                 trade_id="buy-1", date="2026-11-04")
    assert tx["fee_pln"] == "0.50"
    assert p.cash_pln == Decimal("9799.50")
    assert p.valuation({"NVDA": "110"})["total_pnl_pln"] == "19.50"


def test_sell_tracks_realized_profit_and_fees():
    p = PaperPortfolio()
    p.trade(side="BUY", ticker="NVDA", quantity=2, price_pln="100",
            trade_id="1", date="2026-11-04")
    tx = p.trade(side="SELL", ticker="NVDA", quantity=1, price_pln="120",
                 trade_id="2", date="2026-11-05")
    assert tx["fee_pln"] == "0.30"
    assert tx["realized_pnl_pln"] == "19.45"
    assert p.positions["NVDA"].quantity == 1


def test_prevents_insufficient_cash():
    p = PaperPortfolio()
    with pytest.raises(ValueError, match="Insufficient"):
        p.trade(side="BUY", ticker="NVDA", quantity=101, price_pln="100",
                trade_id="1", date="2026-11-04")
    assert p.cash_pln == Decimal("10000.00")


def test_prevents_naked_shorts():
    p = PaperPortfolio()
    with pytest.raises(ValueError, match="Cannot sell"):
        p.trade(side="SELL", ticker="NVDA", quantity=1, price_pln="100",
                trade_id="1", date="2026-11-04")


def test_duplicate_trade_id_does_not_execute_twice():
    p = PaperPortfolio()
    p.trade(side="BUY", ticker="NVDA", quantity=1, price_pln="100",
            trade_id="1", date="2026-11-04")
    with pytest.raises(ValueError, match="Duplicate"):
        p.trade(side="BUY", ticker="NVDA", quantity=1, price_pln="100",
                trade_id="1", date="2026-11-04")
    assert len(p.transactions) == 1


def test_round_trip_journal(tmp_path):
    p = PaperPortfolio()
    p.trade(side="BUY", ticker="NVDA", quantity=2, price_pln="100",
            trade_id="1", date="2026-11-04")
    p.trade(side="SELL", ticker="NVDA", quantity=1, price_pln="120",
            trade_id="2", date="2026-11-05")
    path = tmp_path / "portfolio.json"
    p.save(path)
    restored = PaperPortfolio.load(path)
    assert restored.to_dict() == p.to_dict()


def test_tampered_journal_is_rejected(tmp_path):
    import json
    p = PaperPortfolio()
    p.trade(side="BUY", ticker="NVDA", quantity=1, price_pln="100",
            trade_id="1", date="2026-11-04")
    path = tmp_path / "ledger.json"
    p.save(path)
    data = json.loads(path.read_text())
    data["cash_pln"] = "10000.00"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="totals"):
        PaperPortfolio.load(path)


def test_rejects_fractional_shares_and_invalid_prices():
    p = PaperPortfolio()
    with pytest.raises(ValueError, match="positive integer"):
        p.trade(side="BUY", ticker="NVDA", quantity=0.5, price_pln="100",
                trade_id="1", date="2026-11-04")
    with pytest.raises(ValueError):
        p.trade(side="BUY", ticker="NVDA", quantity=1, price_pln="NaN",
                trade_id="2", date="2026-11-04")


def test_mark_to_market_requires_prices():
    p = PaperPortfolio()
    p.trade(side="BUY", ticker="NVDA", quantity=1, price_pln="100",
            trade_id="1", date="2026-11-04")
    with pytest.raises(ValueError, match="Missing"):
        p.valuation({})
