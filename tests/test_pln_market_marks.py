"""Deterministic PLN quote checks; fake data frames, no network calls."""

from datetime import date, timedelta

import pandas as pd
import pytest

from tradingagents.agents.pln_market_marks import verified_pln_mark, verified_pln_marks

DATE = (date.today() - timedelta(days=1)).isoformat()
PRIOR = (date.today() - timedelta(days=2)).isoformat()
OLD = (date.today() - timedelta(days=10)).isoformat()


def loader(symbol, as_of):
    rows = {
        "NVDA": [(DATE, 206.69)],
        "USDPLN=X": [(PRIOR, 3.99)],
        "EURPLN=X": [(DATE, 4.20)],
        "PLNETF": [(DATE, 100.33)],
        "STALE": [(OLD, 100)],
        "LATER": [(DATE, 200)],
    }
    return pd.DataFrame(rows.get(symbol, []), columns=["Date", "Close"])


def test_usd_conversion_precise():
    result = verified_pln_mark("NVDA", DATE, "USD", loader=loader)
    assert result["price_pln"] == "824.69"
    assert result["fx_symbol"] == "USDPLN=X"
    assert result["fx_date"] == PRIOR
    assert result["execution_eligible"] is False


def test_eur_conversion():
    result = verified_pln_mark("NVDA", DATE, "EUR", loader=loader)
    assert result["price_pln"] == "868.10"


def test_pln_no_fx_needed():
    result = verified_pln_mark("PLNETF", DATE, "PLN", loader=loader)
    assert result["price_pln"] == "100.33"
    assert result["fx_symbol"] is None


def test_unsupported_currency_fails():
    with pytest.raises(ValueError, match="Unsupported"):
        verified_pln_mark("NVDA", DATE, "JPY", loader=loader)


def test_stock_without_exact_date_fails():
    with pytest.raises(ValueError, match="No completed bar"):
        verified_pln_mark("STALE", DATE, "PLN", loader=loader)


def test_no_forward_lookahead():
    with pytest.raises(ValueError, match="not in the future"):
        verified_pln_mark("NVDA", (date.today() + timedelta(days=1)).isoformat(), "USD", loader=loader)


def test_missing_fx_fails():
    def no_fx(symbol, as_of):
        if symbol == "USDPLN=X":
            return pd.DataFrame(columns=["Date", "Close"])
        return loader(symbol, as_of)
    with pytest.raises(ValueError, match="Missing"):
        verified_pln_mark("NVDA", DATE, "USD", loader=no_fx)


def test_stale_fx_fails():
    def old_fx(symbol, as_of):
        if symbol == "USDPLN=X":
            return pd.DataFrame({"Date": [OLD], "Close": [4.00]})
        return loader(symbol, as_of)
    with pytest.raises(ValueError, match="stale"):
        verified_pln_mark("NVDA", DATE, "USD", loader=old_fx)


def test_all_marks_complete():
    result = verified_pln_marks({"NVDA": "USD", "PLNETF": "PLN"}, DATE, loader=loader)
    assert set(result["prices_pln"]) == {"NVDA", "PLNETF"}


def test_partial_mark_failure_fails_whole_request():
    with pytest.raises(ValueError):
        verified_pln_marks({"NVDA": "USD", "MISSING": "PLN"}, DATE, loader=loader)
