"""Calibration and forecast ledger: research only, never generates trades."""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_ANALYSIS_THRESHOLD = 0.70


def _time(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp must include timezone")
    return result.astimezone(timezone.utc)


def validate_forecast(item: dict) -> dict:
    """A forecast is immutable after issuance; evidence must predate issuance."""
    required = ("id", "issued_at", "resolves_at", "event", "probability", "evidence")
    if any(key not in item for key in required):
        raise ValueError("Forecast requires " + ", ".join(required))
    issued, resolves = _time(item["issued_at"]), _time(item["resolves_at"])
    if resolves <= issued:
        raise ValueError("Resolution must be after issuance")
    p = item["probability"]
    if isinstance(p, bool) or not isinstance(p, (float, int)) or not math.isfinite(p) or not 0 <= p <= 1:
        raise ValueError("Probability must be finite between zero and one")
    if not isinstance(item["event"], str) or not item["event"].strip():
        raise ValueError("Event must be measurable and nonempty")
    if not isinstance(item["evidence"], list) or not item["evidence"]:
        raise ValueError("Evidence list required")
    for evidence in item["evidence"]:
        if not evidence.get("url", "").startswith("https://"):
            raise ValueError("HTTPS evidence source required")
        if _time(evidence["published_at"]) > issued:
            raise ValueError("Future evidence leaks into forecast")
    return item


def evaluate(forecasts: list[dict], outcomes: list[dict], as_of: str,
             threshold: float = DEFAULT_ANALYSIS_THRESHOLD) -> dict:
    """Only resolved, evidenced binary outcomes count toward calibration."""
    cutoff = _time(as_of)
    if not 0 < threshold < 1:
        raise ValueError("Invalid analysis threshold")
    ids = set()
    for forecast in forecasts:
        validate_forecast(forecast)
        if forecast["id"] in ids:
            raise ValueError("Duplicate forecast id")
        ids.add(forecast["id"])
    resolved = {}
    for outcome in outcomes:
        key = outcome["forecast_id"]
        if key in resolved or key not in ids:
            raise ValueError("Duplicate or unknown outcome")
        if type(outcome["occurred"]) is not bool:
            raise ValueError("Outcome must be a boolean")
        if not outcome.get("source_url", "").startswith("https://"):
            raise ValueError("Outcome evidence required")
        resolved[key] = outcome
    scored = []
    pending = []
    for f in forecasts:
        if _time(f["issued_at"]) > cutoff:
            continue
        outcome = resolved.get(f["id"])
        if _time(f["resolves_at"]) > cutoff or not outcome or _time(outcome["verified_at"]) > cutoff:
            pending.append(f["id"])
            continue
        if _time(outcome["verified_at"]) < _time(f["resolves_at"]):
            raise ValueError("Outcome verification predates resolution")
        y = int(outcome["occurred"])
        scored.append({"id": f["id"], "probability": f["probability"], "outcome": y,
                       "brier": round((f["probability"] - y) ** 2, 6),
                       "priority": f["probability"] >= threshold})
    bins = []
    for lower in (0, 0.2, 0.4, 0.6, 0.8):
        group = [x for x in scored if lower <= x["probability"] < lower + 0.2 or
                 (lower == 0.8 and x["probability"] == 1)]
        bins.append({"range": [lower, round(lower + 0.2, 2)], "count": len(group),
                     "mean_forecast": round(sum(x["probability"] for x in group) / len(group), 4) if group else None,
                     "observed_frequency": round(sum(x["outcome"] for x in group) / len(group), 4) if group else None})
    return {"mode": "RESEARCH_ONLY_NO_ORDERS", "threshold": threshold,
            "status": "EXPERIMENTAL_UNCALIBRATED" if len(scored) < 100 else "CALIBRATION_REVIEW_REQUIRED",
            "resolved_count": len(scored), "pending_ids": pending,
            "brier_score": round(sum(x["brier"] for x in scored) / len(scored), 6) if scored else None,
            "calibration_bins": bins, "scored": scored,
            "warning": "70% is an analysis filter, not a validated probability or order instruction"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forecasts", type=Path)
    parser.add_argument("--outcomes", type=Path)
    parser.add_argument("--as-of", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument("--output", type=Path, default=Path("scan-output/forecast_calibration.json"))
    args = parser.parse_args()
    forecasts = json.loads(args.forecasts.read_text(encoding="utf-8")) if args.forecasts else []
    outcomes = json.loads(args.outcomes.read_text(encoding="utf-8")) if args.outcomes else []
    result = evaluate(forecasts, outcomes, args.as_of)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Scored: {result['resolved_count']}; status: {result['status']}; no orders")


if __name__ == "__main__":
    main()
