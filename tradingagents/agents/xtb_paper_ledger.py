"""Record a manually reviewed, simulated XTB-style equity fill.

The caller supplies the hypothetical PLN fill price, currencies and
verified expected turnover band. There is no connection to XTB, no quote
retrieval and no real trade. For the legacy 0.25% simulated fee path,
use PaperPortfolio.trade without this adapter.
"""
from __future__ import annotations

from decimal import Decimal

from tradingagents.agents.paper_portfolio import PaperPortfolio
from tradingagents.agents.xtb_cost_estimate import estimate_xtb_stock_costs


def record_xtb_paper_trade(
    portfolio: PaperPortfolio,
    *,
    side: str,
    ticker: str,
    quantity: int,
    price_pln: object,
    trade_id: str,
    date: str,
    listing_currency: str,
    account_currency: str = "PLN",
    monthly_turnover_after_trade_eur: object,
) -> dict:
    """Write only to local virtual ledger after human approval of a paper fill.

    The XTB estimator fails closed on invalid currency, turnover and cost
    assumptions. 0.5% conversion applies to the supplied PLN gross if the
    account and listing currencies differ. Spread, slippage and taxes excluded.
    """
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("Quantity must be a positive integer")
    from tradingagents.agents.paper_portfolio import _decimal, _money
    gross = _money(_money(_decimal(price_pln, positive=True)) * quantity)
    estimate = estimate_xtb_stock_costs(
        notional_pln=gross,
        listing_currency=listing_currency,
        account_currency=account_currency,
        monthly_turnover_after_trade_eur=monthly_turnover_after_trade_eur,
    )
    rate = Decimal("0.005") if estimate["listing_currency"] != estimate["account_currency"] else Decimal("0")
    trade = portfolio.trade(
        side=side, ticker=ticker, quantity=quantity,
        price_pln=price_pln, trade_id=trade_id, date=date, fee_rate=rate,
    )
    # The ledger rounds the fee to pennies, just as the estimator does.
    if trade["fee_pln"] != estimate["estimated_fees_pln"]:
        raise AssertionError("Fee mismatch between XTB estimate and ledger")
    return {
        **trade,
        "cost_model": "XTB_ESTIMATE",
        "execution": "SIMULATED_PAPER_ONLY",
        "broker_order_sent": False,
        "cost_warning": estimate["warning"],
    }
