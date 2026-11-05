"""Deterministic, read-only checks for TradingAgents' saved decisions.

An audit flags contradictions; it never creates orders or silently changes a
Portfolio Manager rating. Missing evidence must be reviewed by a human.
"""

from __future__ import annotations

import re
from typing import Any

from tradingagents.agents.rating import RATING_REVIEW, RATINGS_5_TIER, parse_rating


def _rating(state: dict[str, Any]) -> str:
    explicit = state.get("final_rating")
    return str(explicit) if explicit else parse_rating(
        str(state.get("final_trade_decision") or "")
    )


def audit_decision(state: dict[str, Any], *, expected_ticker: str | None = None,
                   expected_date: str | None = None) -> dict[str, Any]:
    """Check one run for absent/contradictory ratings and missing analysis.

    Returns a descriptive status, never a buy/sell instruction. "REVIEW" means
    the decision should not be fed to a paper-trading executor unchanged.
    """
    issues: list[str] = []
    rating = _rating(state)
    decision_text = str(state.get("final_trade_decision") or "")
    parsed = parse_rating(decision_text)

    if rating not in RATINGS_5_TIER:
        issues.append("Missing or invalid final rating")
    if parsed == RATING_REVIEW:
        issues.append("Final decision text has no unambiguous rating")
    elif rating != parsed:
        issues.append(f"Rating disagrees with decision text: {rating} vs {parsed}")

    if not decision_text.strip():
        issues.append("Missing final decision")
    else:
        # A failed structured-output call can fall back to partially generated
        # free text. An explicit rating at the start is NOT evidence that the
        # narrative completed. Fail closed on recognizable truncation.
        stripped = decision_text.rstrip()
        if (
            stripped.count("(") > stripped.count(")")
            or stripped.count("[") > stripped.count("]")
            or re.search(r"(?:~|≈|\$)\s*\d+(?:[.,]\d*)?$", stripped)
            or re.search(r"(?:\b(?:and|or|the|to|if|with|at|below|above|on|for)|[,;:–—-])$", stripped, re.IGNORECASE)
        ):
            issues.append("Final decision appears truncated or incomplete")
    for field in ("market_report", "investment_plan", "trader_investment_plan"):
        if not str(state.get(field) or "").strip():
            issues.append(f"Missing report: {field}")

    if expected_ticker and str(state.get("company_of_interest") or "").upper() != expected_ticker.upper():
        issues.append("Ticker does not match the requested instrument")
    if expected_date and str(state.get("trade_date") or "") != expected_date:
        issues.append("Analysis date does not match the requested date")

    return {
        "status": "REVIEW" if issues else "PASS",
        "rating": rating,
        "issues": issues,
        "note": "This is a structural audit, not independent validation of market facts.",
    }


def audit_repeated_runs(states: list[dict[str, Any]]) -> dict[str, Any]:
    """Identify conflicting ratings on repeated runs of the same ticker/date.

    Runs with missing identity or date cannot be compared safely.
    """
    groups: dict[tuple[str, str], set[str]] = {}
    for state in states:
        ticker = str(state.get("company_of_interest") or "").strip().upper()
        trade_date = str(state.get("trade_date") or "").strip()
        if not ticker or not trade_date:
            continue
        groups.setdefault((ticker, trade_date), set()).add(_rating(state))

    conflicts = [
        {"ticker": ticker, "trade_date": date, "ratings": sorted(ratings)}
        for (ticker, date), ratings in sorted(groups.items())
        if len(ratings) > 1
    ]
    return {"status": "REVIEW" if conflicts else "PASS", "conflicts": conflicts}
