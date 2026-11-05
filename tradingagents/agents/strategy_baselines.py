"""Strictly retrospective, no-LLM baseline comparison for ONE PLN price series.

No brokerage fills, dividends, taxes or future-known OHLC values. Orders
generated from day t closes are filled at day t+1 adjusted close, as a
hypothetical and intentionally optimistic proxy: a real close may not be
available for execution. For foreign-currency assets, supply externally
converted point-in-time PLN prices; this function cannot do FX conversion.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

CENT = Decimal("0.01")


def _amount(value: Any) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise ValueError("Invalid input amount") from exc
    if not amount.is_finite() or amount <= 0:
        raise ValueError("Price must be finite and positive")
    return amount


def _round(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def compare_baselines(
    prices_pln: list[tuple[str, Any]], *,
    initial_pln: Any = "10000",
    fee_rate: Any = "0.005",
    short_window: int = 20,
    long_window: int = 50,
) -> dict:
    """One-asset MA crossover vs buy-and-hold with identical cost settings.

    Signals use only prior completed daily closes. At most one change per day,
    whole shares, no shorts, no credit. Daily close t produces an execution
    proxy at close t+1. Mark final holdings at last available price. Starting
    at index long_window: both strategies enter only after enough history.
    """
    cash_start = _amount(initial_pln)
    fee = Decimal(str(fee_rate))
    if not fee.is_finite() or not Decimal("0") <= fee < Decimal("0.1"):
        raise ValueError("Invalid fee rate")
    if not (isinstance(short_window, int) and isinstance(long_window, int)
            and 2 <= short_window < long_window):
        raise ValueError("Invalid moving-average windows")
    if len(prices_pln) <= long_window + 2:
        raise ValueError("Insufficient price history")
    dates = [d for d, _ in prices_pln]
    if len(set(dates)) != len(dates) or dates != sorted(dates):
        raise ValueError("Dates must be strictly increasing and unique")
    px = [_round(_amount(price)) for _, price in prices_pln]
    if any(p <= 0 for p in px):
        raise ValueError("Prices round to zero")

    def walk(algorithm: str) -> dict:
        cash = _round(cash_start)
        shares = 0
        paid = Decimal("0.00")
        transactions = 0
        marks = []
        for index in range(long_window, len(px)):
            # Current decision uses bars <= index-1; proxy fill on index close.
            known = px[:index]
            if algorithm == "HOLD":
                enter = True  # buy at first eligible date, then keep exposure
            else:
                avg_short = sum(known[-short_window:]) / short_window
                avg_long = sum(known[-long_window:]) / long_window
                enter = avg_short > avg_long
            price = px[index]
            if enter and shares == 0:
                quantity = int(cash / (price * (1 + fee)))
                if quantity > 0:
                    gross = _round(price * quantity)
                    cost = _round(gross * fee)
                    if gross + cost <= cash:
                        cash -= gross + cost
                        shares += quantity
                        paid += cost
                        transactions += 1
            elif not enter and shares > 0:
                gross = _round(price * shares)
                cost = _round(gross * fee)
                cash += gross - cost
                shares = 0
                paid += cost
                transactions += 1
            marks.append(cash + _round(shares * price))
        peak = cash_start
        drawdown = Decimal("0")
        for value in marks:
            peak = max(peak, value)
            drawdown = max(drawdown, (peak - value) / peak)
        equity = cash + _round(shares * px[-1])
        return {
            "equity_pln": str(_round(equity)),
            "net_pnl_pln": str(_round(equity - cash_start)),
            "return_pct": str(_round((equity / cash_start - 1) * 100)),
            "max_drawdown_pct": str(_round(drawdown * 100)),
            "fees_paid_pln": str(_round(paid)),
            "transactions": transactions,
            "remaining_shares": shares,
        }

    baseline = walk("HOLD")
    moving = walk("MA")
    return {
        "mode": "RETROSPECTIVE_HYPOTHETICAL_NO_LLM",
        "start_date": dates[long_window],
        "end_date": dates[-1],
        "signal_uses_previous_close": True,
        "next_close_proxy_is_executable": False,
        "prices_must_be_point_in_time_pln": True,
        "assumed_fee_rate_each_side": str(fee),
        "cash_only_no_shorting": True,
        "initial_cash_pln": str(_round(cash_start)),
        "buy_and_hold": baseline,
        "moving_average_crossover": moving,
        "difference_vs_buy_hold_pln": str(
            _round(Decimal(moving["equity_pln"]) - Decimal(baseline["equity_pln"]))
        ),
        "limitations": (
            "Exploratory baseline only: historical adjusted close is not a real fill; "
            "no bid-ask spread, slippage, taxes, dividends reconciliation, FX execution, "
            "delistings or survivorship bias corrections. No proof of future returns."
        ),
        "actual_trades_executed": 0,
    }
