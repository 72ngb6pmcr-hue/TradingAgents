"""Yahoo read-only daily market history for event studies; never a fill price."""
from __future__ import annotations

import yfinance as yf


def yahoo_daily(symbol: str) -> dict[str, float]:
    """Return dated adjusted closes; upstream failures propagate to research."""
    bars = yf.Ticker(symbol).history(period="10y", interval="1d", auto_adjust=True)
    if bars.empty:
        raise ValueError("Empty Yahoo historical response")
    return {index.date().isoformat(): float(row["Close"]) for index, row in bars.iterrows()}
