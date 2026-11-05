"""Unattended market scanner is deterministic, research-only and DST aware."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tradingagents.agents.daily_market_scan import allowed_window, scan, score_history

TZ = ZoneInfo("Europe/Warsaw")


def history(now, *, strength=True):
    date = now.date() - timedelta(days=80)
    return [
        {"date": (date + timedelta(days=i)).isoformat(),
         "close": 100 + (i if strength else -0.3 * i),
         "volume": 10000}
        for i in range(79)
    ]


def test_daytime_and_evening_windows():
    assert allowed_window(datetime(2026, 11, 5, 10, tzinfo=TZ))
    assert allowed_window(datetime(2026, 11, 5, 19, tzinfo=TZ))
    assert not allowed_window(datetime(2026, 11, 5, 9, tzinfo=TZ))
    assert not allowed_window(datetime(2026, 11, 7, 10, tzinfo=TZ))


def test_scanner_excludes_current_partial_daily_bar():
    now = datetime(2026, 11, 5, 10, tzinfo=TZ)
    bars = history(now)
    bars.append({"date": "2026-11-05", "close": 900000, "volume": 1})
    score = score_history("BDX.WA", bars, now)
    assert score["status"] == "OBSERVATION"
    assert score["adjusted_close_native"] < 500


def test_positive_trend_observation():
    now = datetime(2026, 11, 5, 10, tzinfo=TZ)
    score = score_history("BDX.WA", history(now), now)
    assert score["status"] == "OBSERVATION"
    assert score["strength_score"] == 3


def test_stale_quotes_do_not_create_observation():
    now = datetime(2026, 11, 20, 10, tzinfo=TZ)
    data = history(datetime(2026, 11, 5, 10, tzinfo=TZ))
    assert score_history("BDX.WA", data, now)["status"] == "STALE"


def test_insufficient_history_fails_closed():
    now = datetime(2026, 11, 5, 10, tzinfo=TZ)
    assert score_history("BDX.WA", history(now)[:12], now)["status"] == "INSUFFICIENT_DATA"


def test_data_error_not_mistaken_for_signal():
    now = datetime(2026, 11, 5, 10, tzinfo=TZ)
    def fetcher(symbol):
        if symbol == "KGH.WA":
            raise RuntimeError("source down")
        return history(now)
    result = scan(now=now, fetcher=fetcher)
    assert result["status"] == "DATA_REVIEW_REQUIRED"
    assert next(c for c in result["candidates"] if c["ticker"] == "KGH.WA")["status"] == "DATA_ERROR"
    assert result["transactions_submitted"] == 0
    assert result["trade_executed"] is False
