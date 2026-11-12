"""Full-sample summaries of all registered hourly correlation investigations.

No backtest trades or predictive probabilities. Counts failures and unstable
findings as evidence, not just attractive significant correlations.
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from tradingagents.agents.hourly_causal_experiment import END, START


def summarize(root: Path, *, now: datetime) -> dict:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Aware timestamp required")
    rows = []
    for path in sorted(root.glob("iteration-??.json")):
        r = json.loads(path.read_text(encoding="utf-8"))
        if r.get("iteration") != int(path.stem.removeprefix("iteration-")):
            raise ValueError(f"Wrong iteration identity for {path.name}")
        if not 0 <= r["iteration"] < 72:
            raise ValueError("Experiment output exceeds 72-hour window")
        rows.append(r)
    if len({r["iteration"] for r in rows}) != len(rows):
        raise ValueError("Duplicate hourly results")
    valid = [r for r in rows
             if r.get("status") == "EXPLORATORY_RESULT"
             and isinstance(r.get("sample"), dict)
             and r["sample"].get("correlation") is not None]
    stable = [r for r in valid if r["sample"].get("same_sign_halves_with_abs_at_least_0_1")]
    by_instrument = {}
    for row in valid:
        key = row["predeclared_test"]["equity"]
        by_instrument.setdefault(key, {"tests": 0, "stable_halves": 0, "positive": 0,
                                       "negative": 0})
        v = by_instrument[key]
        v["tests"] += 1
        v["stable_halves"] += int(row["sample"]["same_sign_halves_with_abs_at_least_0_1"])
        v["positive"] += int(row["sample"]["correlation"] > 0)
        v["negative"] += int(row["sample"]["correlation"] < 0)
    result = {
        "status": "FINAL_WINDOW_ENDED" if now.astimezone(UTC) >= END else "INTERIM",
        "observed_at_utc": now.astimezone(UTC).isoformat(),
        "planned_start_utc": START.isoformat(), "planned_end_utc": END.isoformat(),
        "possible_hourly_slots": 72,
        "recorded_hourly_slots": len(rows),
        "missing_iteration_indices": sorted(set(range(72)) - {r["iteration"] for r in rows}),
        "valid_correlation_tests": len(valid),
        "missing_or_invalid_data_runs": len(rows) - len(valid),
        "within_sample_consistent_sign_tests": len(stable),
        "by_instrument": by_instrument,
        "probability_of_market_move": None,
        "causal_effect_verified": False,
        "out_of_sample_prediction_validated": False,
        "trade_signal": None,
        "comparison_to_no_news_model": "NOT_ESTABLISHED",
        "warning": (
            "Ex post daily-price correlations, overlapping windows and 72 repeated tests "
            "are not 72 independent historic events; sign stability is not forecast skill. "
            "No unverified success percentages or investment recommendations."
        ),
    }
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("research-data/causal-72h"))
    args = parser.parse_args(argv)
    args.root.mkdir(parents=True, exist_ok=True)
    summary = summarize(args.root, now=datetime.now(UTC))
    (args.root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": summary["status"], "observations": summary["recorded_hourly_slots"],
                      "valid": summary["valid_correlation_tests"]}))


if __name__ == "__main__":
    main()
