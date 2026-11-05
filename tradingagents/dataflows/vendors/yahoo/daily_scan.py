"""Yahoo daily close retrieval for the read-only scheduled market scanner."""

from __future__ import annotations

import yfinance as yf


def fetch_daily_bars(symbol: str) -> list[dict]:
    """Download adjusted daily closes; failures propagate to scanner's DATA_ERROR."""
    history = yf.Ticker(symbol).history(period="8mo", interval="1d", auto_adjust=True)
    return [
        {
            "date": index.date().isoformat(),
            "close": float(row["Close"]),
            "volume": float(row["Volume"]),
        }
        for index, row in history.iterrows()
    ]
