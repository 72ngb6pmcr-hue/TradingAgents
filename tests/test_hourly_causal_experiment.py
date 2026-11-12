"""Offline checks for the bounded 72-hour correlation study."""
from datetime import UTC, datetime, timedelta

import pytest

from tradingagents.agents.hourly_causal_experiment import (
    END,
    START,
    corr,
    event_returns,
    lagged_relationship,
    phase,
    run_hour,
)


def test_72_hour_window():
    assert phase(START - timedelta(seconds=1))[0] == "WAIT"
    assert phase(START) == ("ACTIVE", 0)
    assert phase(START + timedelta(hours=71))[0] == "ACTIVE"
    assert phase(END) == ("DONE", None)
    with pytest.raises(ValueError):
        phase(datetime(2026, 11, 12))


def test_lagged_correlation_recovers_known_direction():
    from datetime import date
    origin = date(2023, 1, 1).toordinal()
    d = [(date.fromordinal(origin + i)).isoformat() for i in range(210)]
    brent = {day: 100.0 for day in d}
    equity = {day: 100.0 for day in d}
    for i in range(1, 210):
        # deterministic, with nonconstant sign returns
        x = 0.003 if i % 3 == 0 else (-0.002 if i % 3 == 1 else 0.005)
        brent[d[i]] = brent[d[i - 1]] * (1 + x)
        equity[d[i]] = equity[d[i - 1]] * (1 + (0.01 if i == 1 else (
            0.003 if (i - 1) % 3 == 0 else (-0.002 if (i - 1) % 3 == 1 else 0.005))))
    r = lagged_relationship(brent, equity, lag=1, lookback=190)
    assert r["observations"] >= 180
    assert r["correlation"] > 0.98
    assert r["same_sign_halves_with_abs_at_least_0_1"] is True
    assert r["finding_status"] == "EXPLORATORY_CORRELATION_NOT_CAUSATION"


def test_flat_prices_refuse_correlation():
    from datetime import date
    d = [date.fromordinal(date(2023, 1, 1).toordinal() + i).isoformat()
         for i in range(180)]
    prices = {day: 12.0 for day in d}
    r = lagged_relationship(prices, prices, lag=0, lookback=140)
    assert r["correlation"] is None
    assert corr([1.0], [2.0]) is None


def test_event_study_uses_only_prices_after_event():
    r = event_returns({
        "2020-01-01": 100, "2020-01-03": 110,
        "2020-01-04": 121, "2020-01-05": 133.1,
    }, event_date="2020-01-02", horizons=(1, 2, 5))
    assert r["first_close_at_or_after_event"] == "2020-01-03"
    assert r["returns_by_horizon"]["1"] == 10.0
    assert r["returns_by_horizon"]["2"] == 21.0
    assert r["returns_by_horizon"]["5"] is None


def test_source_failure_is_visible_not_zero_impact():
    def loader(symbol):
        if symbol == "BZ=F":
            raise ValueError("vendor throttled")
        return {f"2025-01-{i:02d}": 1.0 for i in range(1, 29)}
    r = run_hour(now=START, loader=loader, casebook={"historical_cases": []})
    assert r["status"] == "DATA_MISSING"
    assert r["probability"] is None
    assert r["trades"] == 0
    assert r["hypotheses_tested"] == 0


def test_no_future_price_or_fake_probability():
    from datetime import date
    day0 = date(2017, 1, 1).toordinal()

    def loader(symbol):
        return {date.fromordinal(day0 + i).isoformat(): (
            100 + 0.04 * i + (0.5 if (i % 4) == 0 else 0.0)
        ) for i in range(2000)}
    r = run_hour(now=START + timedelta(hours=11), loader=loader,
                 casebook={"historical_cases": [{"event_date": "2019-09-14"}]})
    assert r["status"] == "EXPLORATORY_RESULT"
    assert r["sample"]["observations"] > 40
    assert r["probability"] is None
    assert r["predictions_issued"] == 0
    assert len(r["event_studies"]) == 1
