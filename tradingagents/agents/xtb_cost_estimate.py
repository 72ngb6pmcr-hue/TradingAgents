"""XTB-like *indicative* costs, separate from the legacy 0.25% paper ledger.

No brokerage connection. Actual XTB rates depend on product/account and
turnover. Only REAL stocks/ETFs, not CFDs. The per-month 100,000 EUR turnover
threshold must be supplied externally; this estimator fails closed when it is
exceeded, rather than inventing a rate for that tier.

For non-PLN account/listing currency, FX conversion is estimated at 0.5%.
Spread, price slippage, exchange charges and taxes are excluded.
"""
from __future__ import annotations

from decimal import Decimal

from tradingagents.agents.paper_portfolio import _decimal, _money

BASE_FX_RATE = Decimal("0.005")
ZERO_COMMISSION_MONTHLY_LIMIT_EUR = Decimal("100000")


def estimate_xtb_stock_costs(
    *,
    notional_pln: object,
    listing_currency: str,
    account_currency: str = "PLN",
    monthly_turnover_after_trade_eur: object,
    fx_rate: object = BASE_FX_RATE,
) -> dict:
    """Return a conservative cost estimate in PLN, *not* an actual execution fill.

    Distinguish an account already denominated in the stock's currency from
    one that would incur currency conversion. Turnover is for the whole month,
    provided by the caller; never guessed from the current portfolio alone.
    """
    gross = _money(_decimal(notional_pln, positive=True))
    if gross <= 0:
        raise ValueError("Notional rounds to zero")
    listing = str(listing_currency).strip().upper()
    account = str(account_currency).strip().upper()
    if listing not in ("PLN", "EUR", "USD") or account not in ("PLN", "EUR", "USD"):
        raise ValueError("Only PLN/EUR/USD account and listing currencies supported")
    turnover = _decimal(monthly_turnover_after_trade_eur)
    if turnover < 0:
        raise ValueError("Monthly turnover must not be negative")
    if turnover > ZERO_COMMISSION_MONTHLY_LIMIT_EUR:
        raise ValueError("Above zero-commission turnover band: fee schedule needs verification")
    conversion_rate = _decimal(fx_rate)
    if not Decimal("0") <= conversion_rate < Decimal("1"):
        raise ValueError("Invalid FX fee rate")

    conversion_fee = (_money(gross * conversion_rate) if account != listing
                      else Decimal("0.00"))
    return {
        "model": "XTB_STOCK_ETF_ESTIMATE",
        "notional_pln": str(gross),
        "listing_currency": listing,
        "account_currency": account,
        "monthly_turnover_after_trade_eur": str(turnover),
        "stock_commission_pln": "0.00",
        "fx_conversion_fee_pln": str(conversion_fee),
        "estimated_fees_pln": str(conversion_fee),
        "estimated_buy_cash_required_pln": str(gross + conversion_fee),
        "estimated_sell_cash_proceeds_pln": str(gross - conversion_fee),
        "spread_and_slippage_included": False,
        "broker_quote_verified": False,
        "warning": (
            "Illustrative XTB real-stock/ETF pricing only; conditions, actual "
            "FX conversion, thresholds, execution prices and other costs "
            "must be verified in the account."
        ),
    }
