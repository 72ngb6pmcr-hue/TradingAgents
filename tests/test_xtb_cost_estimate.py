"""XTB indicative fees, never broker access or fills."""
import pytest

from tradingagents.agents.xtb_cost_estimate import estimate_xtb_stock_costs


def estimate(**kwargs):
    return estimate_xtb_stock_costs(
        notional_pln="1000", listing_currency="PLN",
        account_currency="PLN", monthly_turnover_after_trade_eur="500",
        **kwargs,
    )


def test_pln_stock_on_pln_account_zero_base_fee():
    d = estimate()
    assert d["estimated_fees_pln"] == "0.00"
    assert d["estimated_buy_cash_required_pln"] == "1000.00"


def test_fx_fee_for_usd_stock_on_pln_account():
    d = estimate_xtb_stock_costs(
        notional_pln="1000", listing_currency="USD",
        account_currency="PLN", monthly_turnover_after_trade_eur="500")
    assert d["estimated_fees_pln"] == "5.00"
    assert d["estimated_buy_cash_required_pln"] == "1005.00"
    assert d["estimated_sell_cash_proceeds_pln"] == "995.00"


def test_foreign_currency_account_no_currency_conversion():
    d = estimate_xtb_stock_costs(
        notional_pln="1000", listing_currency="USD",
        account_currency="USD", monthly_turnover_after_trade_eur="500")
    assert d["estimated_fees_pln"] == "0.00"


def test_turnover_limit_without_verified_tier_fails_closed():
    with pytest.raises(ValueError, match="Above zero-commission"):
        estimate_xtb_stock_costs(
            notional_pln="1000", listing_currency="PLN",
            monthly_turnover_after_trade_eur="100001")


def test_bad_turnover_rejected():
    with pytest.raises(ValueError):
        estimate_xtb_stock_costs(
            notional_pln="1000", listing_currency="PLN",
            monthly_turnover_after_trade_eur="-1")


def test_estimate_is_not_an_execution_price():
    d = estimate()
    assert d["broker_quote_verified"] is False
    assert d["spread_and_slippage_included"] is False
