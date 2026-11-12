"""Explainable historical analogue matching and conditional chain propagation.

The graph is a *hypothesis*, not a learned causal model. Empirical frequencies
need many dated independent and fully settled examples; unknown is not zero.
No orders, predictions, broker calls or external LLM are made here.
"""
from __future__ import annotations

import json
import math
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

KNOWLEDGE = Path(__file__).resolve().parents[1] / "knowledge"
MIN_EMPIRICAL_CASES = 20


def _parse_timestamp(text: str) -> datetime:
    when = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if when.tzinfo is None or when.utcoffset() is None:
        raise ValueError("Timestamp must contain timezone")
    return when


def trace_impact(graph: dict, *, changed_node: str, initial_direction: int,
                 max_depth: int = 5) -> list[dict[str, Any]]:
    """Propagate signs, keeping conflicting paths and explicit assumptions.

    Each step is a *possible* transmission, not a guarantee. Cycles are
    suppressed within paths; distinct paths to the same node are preserved.
    """
    nodes = {item["id"] for item in graph["nodes"]}
    if changed_node not in nodes or initial_direction not in (-1, 1):
        raise ValueError("Unknown node or invalid direction")
    if not 1 <= max_depth <= 8:
        raise ValueError("Invalid path-depth limit")
    adjacency: dict[str, list[dict]] = {}
    for edge in graph["edges"]:
        if edge["from"] not in nodes or edge["to"] not in nodes:
            raise ValueError("Invalid graph edge")
        if edge["sign"] not in (-1, 1):
            raise ValueError("Edge direction must be -1 or +1")
        adjacency.setdefault(edge["from"], []).append(edge)
    queue = deque([(changed_node, initial_direction, (changed_node,), ())])
    hits = []
    while queue:
        source, direction, path, assumptions = queue.popleft()
        if len(path) > max_depth:
            continue
        for edge in adjacency.get(source, []):
            target = edge["to"]
            if target in path:
                continue
            new_direction = direction * edge["sign"]
            next_path = (*path, target)
            next_assumptions = (*assumptions, *edge.get("conditions", []))
            hits.append({
                "node": target, "hypothesized_direction": "UP" if new_direction > 0 else "DOWN",
                "path": list(next_path), "conditions": list(next_assumptions),
                "status": "QUALITATIVE_HYPOTHESIS_NOT_CALIBRATED",
            })
            if len(next_path) < max_depth:
                queue.append((target, new_direction, next_path, next_assumptions))
    return hits


def historical_analogues(casebook: dict, *, event_type: str, as_of: str) -> list[dict]:
    """Never expose retrospective source knowledge before its publication date.

    Cases without independently verified earliest public time are useful as
    documented history, but explicitly excluded from point-in-time analogues.
    """
    point = _parse_timestamp(as_of)
    choices = []
    for case in casebook["historical_cases"]:
        if case["event_type"] != event_type:
            continue
        first_public_at = case.get("first_public_at")
        if first_public_at is None:
            continue
        if _parse_timestamp(first_public_at) <= point:
            choices.append(case)
    return choices


def empirical_probability(outcomes: list[dict], *, event_type: str,
                          instrument: str, horizon_days: int,
                          as_of: str, min_cases: int = MIN_EMPIRICAL_CASES) -> dict:
    """Only use settled, previously available *independent* cases.

    outcome rows must have:
      event_id, event_type, instrument, horizon_days,
      published_at, outcome_available_at, direction_correct.
    Missing evidence, mixed instruments and forward-known labels are excluded.
    Wilson 95% interval quantifies sampling uncertainty, not model calibration.
    """
    cutoff = _parse_timestamp(as_of)
    eligible: dict[str, bool | None] = {}
    for row in outcomes:
        if (row.get("event_type") != event_type
                or row.get("instrument") != instrument
                or row.get("horizon_days") != horizon_days):
            continue
        if type(row.get("direction_correct")) is not bool:
            continue
        event_id = row.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            continue
        published = row.get("published_at")
        settled = row.get("outcome_available_at")
        if not isinstance(published, str) or not isinstance(settled, str):
            continue
        try:
            entry_time, settle_time = _parse_timestamp(published), _parse_timestamp(settled)
        except ValueError:
            continue
        if entry_time >= settle_time or settle_time > cutoff:
            continue
        if event_id in eligible:
            # A repeated event cannot contribute independent evidence.
            eligible[event_id] = None
            continue
        eligible[event_id] = row["direction_correct"]
    observations = [v for v in eligible.values() if type(v) is bool]
    n = len(observations)
    if n < min_cases:
        return {"status": "INSUFFICIENT_VALID_OUTCOMES", "n": n,
                "required": min_cases, "probability": None,
                "confidence_interval_95pct": None,
                "warning": "No numeric forecast: sample too small or unpublished."}
    successes = sum(observations)
    estimated = successes / n
    z = 1.96
    factor = 1 + z * z / n
    center = (estimated + z * z / (2 * n)) / factor
    radius = (z * math.sqrt(estimated * (1 - estimated) / n + z * z / (4 * n * n))) / factor
    return {
        "status": "UNVALIDATED_HISTORICAL_FREQUENCY",
        "n": n, "hits": successes,
        "probability": round(estimated, 4),
        "confidence_interval_95pct": [round(center - radius, 4), round(center + radius, 4)],
        "warning": "Observed success frequency is not validated out-of-sample prediction; selection bias possible.",
    }


def evaluate_event(*, event_type: str, as_of: str, changed_node: str,
                   direction: int, outcomes: list[dict] | None = None,
                   instrument: str | None = None, horizon_days: int = 5,
                   casebook: dict | None = None, graph: dict | None = None) -> dict:
    if casebook is None:
        casebook = json.loads((KNOWLEDGE / "historical_event_cases.json").read_text(encoding="utf-8"))
    if graph is None:
        graph = json.loads((KNOWLEDGE / "supply_chain_graph.json").read_text(encoding="utf-8"))
    if event_type not in {x["id"] for x in casebook["event_types"]}:
        raise ValueError("Unknown event type")
    analogues = historical_analogues(casebook, event_type=event_type, as_of=as_of)
    impact = trace_impact(graph, changed_node=changed_node, initial_direction=direction)
    empirical = (empirical_probability(outcomes or [], event_type=event_type, instrument=instrument,
                                       horizon_days=horizon_days, as_of=as_of)
                 if instrument else None)
    return {
        "event_type": event_type, "as_of": as_of,
        "status": "RESEARCH_ONLY_NO_TRADES",
        "documented_historical_cases": sum(
            case["event_type"] == event_type for case in casebook["historical_cases"]
        ),
        "point_in_time_usable_analogues": len(analogues),
        "possible_paths": impact,
        "probability_estimate": empirical,
        "trade_signal": None,
        "warning": ("Ex-post cases with unknown publication time are excluded from "
                    "trade-time evaluation. Economic edges are hypotheses. "
                    "No causal certainty, security mapping or live-price validation."),
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Research-only event transmission explorer")
    parser.add_argument("--event-type", default="PHYSICAL_OIL_OUTAGE")
    parser.add_argument("--changed-node", default="crude_supply")
    parser.add_argument("--direction", type=int, choices=[-1, 1], default=-1)
    parser.add_argument("--as-of", required=True,
                        help="ISO 8601 aware timestamp: 2026-11-12T04:00:00+01:00")
    args = parser.parse_args()
    print(json.dumps(evaluate_event(
        event_type=args.event_type, as_of=args.as_of,
        changed_node=args.changed_node, direction=args.direction,
    ), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
