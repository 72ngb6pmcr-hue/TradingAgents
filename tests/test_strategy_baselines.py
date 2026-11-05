"""Baseline comparisons use only known past prices, with no broker or AI."""
from decimal import Decimal

import pytest

from tradingagents.agents.strategy_baselines import compare_baselines


def prices(n=90, rising=True):
    return [
        (f"2026-01-{i+1:03d}", 100 + (i * 2 if rising else -i * 0.3))
        for i in range(n)
    ]


def test_rising_history_enters_and_reports_both_benchmarks():
    result = compare_baselines(prices())
    assert result["mode"] == "RETROSPECTIVE_HYPOTHETICAL_NO_LLM"
    assert result["actual_trades_executed"] == 0
    assert result["buy_and_hold"]["transactions"] == 1
    assert result["moving_average_crossover"]["transactions"] == 1


def test_flat_history_holds_cash_under_crossover():
    flat = [(d, 100) for d, _ in prices()]
    result = compare_baselines(flat)
    assert result["moving_average_crossover"]["transactions"] == 0
    assert result["moving_average_crossover"]["equity_pln"] == "10000.00"


def test_buy_and_hold_pays_fee_and_does_not_overdraw():
    result = compare_baselines(prices(), fee_rate="0.005")
    assert Decimal(result["buy_and_hold"]["fees_paid_pln"]) > 0
    assert result["buy_and_hold"]["remaining_shares"] > 0


def test_future_price_cannot_affect_prior_trade_count():
    original = prices()
    changed = original[:-1] + [(original[-1][0], 999999)]
    before = compare_baselines(original)
    after = compare_baselines(changed)
    assert before["buy_and_hold"]["transactions"] == after["buy_and_hold"]["transactions"]


def test_insufficient_history_rejected():
    with pytest.raises(ValueError, match="Insufficient"):
        compare_baselines(prices(30))


def test_duplicate_dates_rejected():
    p = prices()
    p[3] = p[2]
    with pytest.raises(ValueError, match="Dates"):
        compare_baselines(p)


def test_invalid_fee_rejected():
    with pytest.raises(ValueError, match="fee"):
        compare_baselines(prices(), fee_rate="-0.1")


def test_no_trades_guarantee():
    result = compare_baselines(prices())
    assert result["actual_trades_executed"] == 0
    assert result["next_close_proxy_is_executable"] is False
