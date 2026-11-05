"""XTB-mode paper ledger: monetary accounting and replay only."""
from decimal import Decimal

import pytest

from tradingagents.agents.paper_portfolio import PaperPortfolio
from tradingagents.agents.xtb_paper_ledger import record_xtb_paper_trade


def xtb(portfolio, **kwargs):
    return record_xtb_paper_trade(
        portfolio, side="BUY", ticker="BDX.WA", quantity=1,
        price_pln="734.60", trade_id="buy", date="2026-11-05",
        listing_currency="PLN", account_currency="PLN",
        monthly_turnover_after_trade_eur="2000", **kwargs,
    )


def test_polish_share_has_no_base_commission():
    p = PaperPortfolio()
    result = xtb(p)
    assert result["fee_pln"] == "0.00"
    assert p.cash_pln == Decimal("9265.40")
    assert result["broker_order_sent"] is False


def test_foreign_equity_fx_cost():
    p = PaperPortfolio()
    result = record_xtb_paper_trade(
        p, side="BUY", ticker="NVDA", quantity=2, price_pln="500",
        trade_id="buy", date="2026-11-05",
        listing_currency="USD", account_currency="PLN",
        monthly_turnover_after_trade_eur="2000",
    )
    assert result["fee_pln"] == "5.00"
    assert p.cash_pln == Decimal("8995.00")


def test_xtb_buy_sell_round_trip_survives_journal_replay(tmp_path):
    p = PaperPortfolio()
    xtb(p)
    record_xtb_paper_trade(
        p, side="SELL", ticker="BDX.WA", quantity=1,
        price_pln="750", trade_id="sell", date="2026-11-06",
        listing_currency="PLN", account_currency="PLN",
        monthly_turnover_after_trade_eur="2300",
    )
    path = tmp_path / "portfolio.json"
    p.save(path)
    assert PaperPortfolio.load(path).to_dict() == p.to_dict()
    assert p.realized_pnl_pln == Decimal("15.40")


def test_unverified_turnover_band_cannot_modify_ledger():
    p = PaperPortfolio()
    with pytest.raises(ValueError, match="Above zero-commission"):
        record_xtb_paper_trade(
            p, side="BUY", ticker="BDX.WA", quantity=1,
            price_pln="734.60", trade_id="buy", date="2026-11-05",
            listing_currency="PLN", monthly_turnover_after_trade_eur="100001",
        )
    assert p.transactions == []


def test_negative_fee_override_cannot_modify_ledger():
    p = PaperPortfolio()
    with pytest.raises(ValueError, match="Invalid fee"):
        p.trade(side="BUY", ticker="X", quantity=1, price_pln="100",
                trade_id="1", date="2026-11-05", fee_rate="-0.01")
    assert not p.transactions


def test_tampered_xtb_fee_rate_fails_journal_replay(tmp_path):
    import json
    p = PaperPortfolio()
    xtb(p)
    path = tmp_path / "portfolio.json"
    p.save(path)
    data = json.loads(path.read_text())
    data["transactions"][0]["fee_rate"] = "0.005"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        PaperPortfolio.load(path)
