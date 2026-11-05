"""Deterministic end-of-day PLN marks for a simulation portfolio.

Uses the existing verified Yahoo OHLCV pipeline; no language model or broker.
The source uses adjusted closes, so these marks are *indicative valuations*,
not executable fill quotes. A fill should be approved separately.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd

from tradingagents.agents.paper_portfolio import _decimal, _money
from tradingagents.dataflows.vendors.yahoo.snapshot import _verified_rows

FX_SYMBOLS = {"USD": "USDPLN=X", "EUR": "EURPLN=X"}
MAX_FX_AGE_DAYS = 3


def _last_close(loader: Callable[[str, str], pd.DataFrame], ticker: str,
                as_of_date: str) -> tuple[date, Decimal]:
    frame = loader(ticker, as_of_date)
    if frame is None or frame.empty or "Date" not in frame or "Close" not in frame:
        raise ValueError(f"Missing dated close for {ticker}")
    rows = frame.copy()
    rows["Date"] = pd.to_datetime(rows["Date"], errors="coerce")
    rows = rows.dropna(subset=["Date"]).sort_values("Date")
    requested = pd.Timestamp(as_of_date)
    rows = rows[rows["Date"] <= requested]
    if rows.empty:
        raise ValueError(f"No close on or before {as_of_date} for {ticker}")
    last = rows.iloc[-1]
    value = _decimal(last["Close"], positive=True)
    return last["Date"].date(), value


def verified_pln_mark(
    ticker: str,
    as_of_date: str,
    quote_currency: str,
    *,
    loader: Callable[[str, str], pd.DataFrame] | None = None,
) -> dict[str, Any]:
    """Return a sourced, non-executable PLN mark with no future information.

    Fails closed when the stock/ETF has no bar on the requested date.
    Currency must be independently supplied and verified for the instrument.
    FX may use a preceding business day (at most three calendar days old).
    """
    if not isinstance(ticker, str) or not ticker.strip():
        raise ValueError("Ticker is required")
    try:
        requested = date.fromisoformat(as_of_date)
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid YYYY-MM-DD analysis date") from exc
    if requested.isoformat() != as_of_date or requested > date.today():
        raise ValueError("Analysis date must be canonical and not in the future")

    currency = str(quote_currency).strip().upper()
    if currency not in ("PLN", *FX_SYMBOLS):
        raise ValueError(f"Unsupported quote currency: {currency}")
    reader = loader if loader is not None else _verified_rows
    asset_date, raw_close = _last_close(reader, ticker, as_of_date)
    if asset_date != requested:
        raise ValueError(f"No completed bar for {ticker} exactly on {as_of_date}")

    fx_symbol = None
    fx_date = None
    fx_rate = Decimal("1")
    if currency != "PLN":
        fx_symbol = FX_SYMBOLS[currency]
        fx_date, fx_rate = _last_close(reader, fx_symbol, as_of_date)
        age = (requested - fx_date).days
        if age < 0 or age > MAX_FX_AGE_DAYS:
            raise ValueError(f"FX rate for {fx_symbol} is stale ({age} days)")

    mark = _money(raw_close * fx_rate)
    if mark <= 0:
        raise ValueError("Converted mark rounds to zero")
    return {
        "ticker": ticker.upper(),
        "analysis_date": as_of_date,
        "market_bar_date": asset_date.isoformat(),
        "quote_currency": currency,
        "close_native": str(raw_close),
        "fx_symbol": fx_symbol,
        "fx_date": fx_date.isoformat() if fx_date else None,
        "fx_rate_pln": str(fx_rate),
        "price_pln": str(mark),
        "market_source": "Yahoo Finance via TradingAgents verified OHLCV",
        "price_type": "adjusted_daily_close",
        "execution_eligible": False,
        "warning": "Valuation only; adjusted historical close is not an executable fill quote.",
    }


def verified_pln_marks(
    instruments: dict[str, str], as_of_date: str,
    *, loader: Callable[[str, str], pd.DataFrame] | None = None,
) -> dict[str, Any]:
    """Retrieve all required marks or fail rather than omit unpriced holdings."""
    if not instruments:
        raise ValueError("No instruments provided")
    detailed = {
        ticker.upper(): verified_pln_mark(ticker, as_of_date, currency, loader=loader)
        for ticker, currency in instruments.items()
    }
    return {
        "as_of_date": as_of_date,
        "prices_pln": {ticker: record["price_pln"] for ticker, record in detailed.items()},
        "records": detailed,
    }
