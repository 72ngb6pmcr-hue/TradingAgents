"""Unadjusted exchange daily closes used only as disclosed paper-fill proxies."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import yfinance as yf


def finished_raw_close(symbol: str, trade_day: date) -> dict:
    """Require a positive-volume daily bar for exactly the requested day.

    Call this only after the listing's exchange has closed for that day.
    It is not an executable quote or an official exchange settlement.
    """
    if not isinstance(trade_day, date):
        raise ValueError("trade_day must be a date")
    data = yf.Ticker(symbol).history(
        start=trade_day.isoformat(),
        end=date.fromordinal(trade_day.toordinal() + 1).isoformat(),
        interval="1d",
        auto_adjust=False,
        actions=False,
    )
    matches = [
        row for index, row in data.iterrows()
        if index.date() == trade_day
    ]
    if len(matches) != 1:
        raise ValueError("No unique same-date completed market bar")
    row = matches[0]
    close = Decimal(str(row["Close"]))
    volume = Decimal(str(row["Volume"]))
    if not close.is_finite() or close <= 0 or not volume.is_finite() or volume <= 0:
        raise ValueError("Invalid close or missing market volume")
    return {
        "symbol": symbol, "date": trade_day.isoformat(),
        "close_native": str(close),
        "volume": str(volume),
        "source": "Yahoo Finance unadjusted daily Close (hypothetical paper proxy)",
        "executable": False,
    }
