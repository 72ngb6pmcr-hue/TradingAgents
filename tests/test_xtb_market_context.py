"""Market configuration tests with no broker or live data dependency."""
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from tradingagents.agents.xtb_market_context import (
    SAMPLE_UNIVERSE, XtbCosts, market_review_context,
)

WARSAW = ZoneInfo("Europe/Warsaw")


def test_polish_watchlist_has_yahoo_warsaw_suffix():
    assert "BDX.WA" in SAMPLE_UNIVERSE["GPW"]
    assert all(ticker.endswith(".WA") for ticker in SAMPLE_UNIVERSE["GPW"])


def test_international_equity_remains_available_for_research():
    assert "NVDA" in SAMPLE_UNIVERSE["US"]


def test_xtb_cost_parameters_do_not_inherit_flat_simulated_fee():
    fees = XtbCosts()
    assert fees.stock_commission_rate == Decimal("0")
    assert fees.fx_conversion_rate == Decimal("0.005")


def test_morning_review_gpw_possible():
    value = market_review_context("PKO.WA", now=datetime(2026, 11, 4, 10, tzinfo=WARSAW))
    assert value["gpw_regular_session_possible"] is True
    assert value["currency_hint"] == "PLN"
    assert value["execution"] == "MANUAL_ONLY"


def test_evening_review_is_next_gpw_session():
    value = market_review_context("PKO.WA", now=datetime(2026, 11, 4, 19, tzinfo=WARSAW))
    assert value["gpw_regular_session_possible"] is False
    assert "next" in value["guidance"]
    assert value["order_submitted"] is False


def test_us_market_not_assumed_same_opening_hours():
    value = market_review_context("NVDA", now=datetime(2026, 11, 4, 19, tzinfo=WARSAW))
    assert value["gpw_regular_session_possible"] is None
    assert value["availability_verified"] is False


def test_no_weekend_gpw_trading():
    value = market_review_context("KGH.WA", now=datetime(2026, 11, 7, 10, tzinfo=WARSAW))
    assert value["gpw_regular_session_possible"] is False
