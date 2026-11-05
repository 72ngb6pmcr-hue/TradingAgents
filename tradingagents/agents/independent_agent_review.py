"""Independent, deterministic second opinion on AI investment proposals.

This is NOT another language model and cannot prove an investment edge.
Three isolated checks critique the AI's proposed action using independent
market data, simple stress assumptions and evidence provenance. The final
gate never turns HOLD into BUY or places any order.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def _number(value: Any) -> Decimal | None:
    try:
        x = Decimal(str(value))
        return x if x.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def independent_review(
    proposal: dict[str, Any],
    market_observation: dict[str, Any] | None,
    *,
    max_daily_volatility_pct: Any = "5",
    stress_price_drop_pct: Any = "10",
) -> dict[str, Any]:
    """Independent critique; fail closed for BUY if evidence is missing.

    The input is a read-only price history observation from daily_market_scan,
    which deliberately excludes the current unfinished daily bar. This
    provides no confirmation of XTB spreads, execution price or news.
    """
    action = str(proposal.get("action") or "").upper()
    ticker = str(proposal.get("ticker") or "").strip().upper()
    status = proposal.get("status")
    checks = []
    issues = []
    maximum_vol = _number(max_daily_volatility_pct)
    stress = _number(stress_price_drop_pct)
    if maximum_vol is None or not (Decimal("0") < maximum_vol < Decimal("100")):
        raise ValueError("Invalid maximum daily volatility")
    if stress is None or not (Decimal("0") < stress < Decimal("100")):
        raise ValueError("Invalid stress price drop")

    if status != "PROPOSED" or action not in ("BUY", "SELL"):
        return {
            "status": "NO_ACTION", "action": "HOLD", "ticker": ticker,
            "issues": [], "checks": [],
            "trade_executed": False,
            "reason": "No valid actionable proposal to review",
        }

    if not ticker:
        issues.append("Missing ticker in AI proposal")

    # Critic 1: independent price-series confirmation.
    obs = market_observation if isinstance(market_observation, dict) else {}
    if not obs or obs.get("ticker", "").upper() != ticker:
        issues.append("Missing independent observation for proposed ticker")
        checks.append({"agent": "TECHNICAL_CRITIC", "result": "UNVERIFIED"})
    elif obs.get("status") != "OBSERVATION":
        issues.append("Independent market evidence not usable")
        checks.append({"agent": "TECHNICAL_CRITIC", "result": "UNVERIFIED"})
    else:
        strength = obs.get("strength_score")
        momentum = _number(obs.get("momentum_20d_pct"))
        if type(strength) is not int or strength not in (0, 1, 2, 3) or momentum is None:
            issues.append("Invalid independent trend or momentum evidence")
            checks.append({"agent": "TECHNICAL_CRITIC", "result": "UNVERIFIED"})
        elif action == "BUY" and (strength < 2 or momentum <= 0):
            issues.append("Bullish AI proposal conflicts with independent trend evidence")
            checks.append({"agent": "TECHNICAL_CRITIC", "result": "CONFLICT"})
        else:
            checks.append({"agent": "TECHNICAL_CRITIC", "result": "CONSISTENT"})

    # Critic 2: volatility and explicit mark-to-market shock.
    vol = _number(obs.get("daily_volatility_20d_pct"))
    if vol is None or vol < 0:
        issues.append("Independent volatility estimate unavailable")
        checks.append({"agent": "RISK_CRITIC", "result": "UNVERIFIED"})
    elif action == "BUY" and vol > maximum_vol:
        issues.append("Daily volatility exceeds configured buy risk limit")
        checks.append({"agent": "RISK_CRITIC", "result": "HIGH_RISK"})
    else:
        checks.append({"agent": "RISK_CRITIC", "result": "WITHIN_LIMIT"})

    gross = _number(proposal.get("price_pln"))
    qty = proposal.get("quantity")
    if gross is None or gross <= 0 or type(qty) is not int or qty <= 0:
        issues.append("Cannot estimate proposed position stress loss")
        estimated_loss = None
    else:
        estimated_loss = str((gross * qty * stress / 100).quantize(Decimal("0.01")))

    # Critic 3: evidence audit. Adjusted daily close is not a live trade quote.
    source = str(proposal.get("quote_source") or "").lower()
    source_valid = bool(source and not any(
        marker in source for marker in ("adjusted daily close", "adjusted close", "indicative", "not a fill")
    ))
    if not source_valid:
        issues.append("Proposed price lacks independent executable quote verification")
    checks.append({"agent": "EVIDENCE_CRITIC", "result": "DOCUMENTED" if source_valid else "UNVERIFIED"})

    if action == "SELL":
        # Risk-reducing exits must remain reviewable despite market-data issues.
        gate = "MANUAL_REVIEW_REQUIRED"
    else:
        gate = "REVIEW" if issues else "MANUAL_REVIEW_REQUIRED"
    return {
        "status": gate, "action": action, "ticker": ticker,
        "issues": issues, "checks": checks,
        "stress_price_drop_pct": str(stress),
        "estimated_position_shock_loss_pln": estimated_loss,
        "trade_executed": False,
        "automatic_execution": False,
        "note": (
            "Independent checks do not establish expected returns. A technical "
            "agreement is not a buy recommendation. Actual XTB quotes, costs and "
            "human authorization are still required."
        ),
    }
