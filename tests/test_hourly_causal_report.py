"""Report all hourly investigations, including unavailable historical data."""
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tradingagents.agents.hourly_causal_report import summarize


def test_summary_exposes_skipped_hours_and_missing_data(tmp_path: Path):
    root = tmp_path / "research"
    root.mkdir()
    first = {
        "iteration": 0, "status": "EXPLORATORY_RESULT",
        "predeclared_test": {"equity": "XLE"},
        "sample": {"correlation": 0.3, "same_sign_halves_with_abs_at_least_0_1": True},
    }
    other = {
        "iteration": 2, "status": "DATA_MISSING",
        "sample": None,
        "errors": {"BZ=F": {"error_type": "TimeoutError"}},
    }
    for i, row in [(0, first), (2, other)]:
        (root / f"iteration-{i:02d}.json").write_text(json.dumps(row), encoding="utf-8")
    report = summarize(root, now=datetime(2026, 11, 15, 5, tzinfo=UTC))
    assert report["status"] == "FINAL_WINDOW_ENDED"
    assert report["recorded_hourly_slots"] == 2
    assert report["valid_correlation_tests"] == 1
    assert report["missing_or_invalid_data_runs"] == 1
    assert report["within_sample_consistent_sign_tests"] == 1
    assert report["probability_of_market_move"] is None
    assert report["out_of_sample_prediction_validated"] is False
    assert report["by_instrument"]["XLE"]["tests"] == 1
    assert len(report["missing_iteration_indices"]) == 70
    assert 1 in report["missing_iteration_indices"]


def test_tampered_iteration_file_is_rejected(tmp_path: Path):
    root = tmp_path / "research"
    root.mkdir()
    (root / "iteration-02.json").write_text(json.dumps({
        "iteration": 8, "status": "EXPLORATORY_RESULT"
    }), encoding="utf-8")
    with pytest.raises(ValueError):
        summarize(root, now=datetime(2026, 11, 12, 5, tzinfo=UTC))


def test_empty_summary_is_not_presented_as_a_result(tmp_path: Path):
    result = summarize(tmp_path, now=datetime(2026, 11, 12, 4, tzinfo=UTC))
    assert result["recorded_hourly_slots"] == 0
    assert result["valid_correlation_tests"] == 0
    assert result["status"] == "INTERIM"
    assert result["causal_effect_verified"] is False
