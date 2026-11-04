"""Two human review sessions per Polish weekday; never automatic orders."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from tradingagents.agents.paper_portfolio import PaperPortfolio

WARSAW = ZoneInfo("Europe/Warsaw")
REVIEW_HOURS = (10, 19)
WINDOW_MINUTES = 60
MAX_WEEKLY_TRADES = 2
TICKER_COOLDOWN_DAYS = 7


def evaluate_review_window(proposal: dict, portfolio: PaperPortfolio, *, now: datetime | None = None) -> dict:
    """Read-only gate: two windows, <=2 fills in 7 days, one ticker fill in 7 days."""
    instant = now if now is not None else datetime.now(WARSAW)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("An aware datetime is required")
    local = instant.astimezone(WARSAW)
    common = {
        "timezone": "Europe/Warsaw", "review_hours_local": ["10:00", "19:00"],
        "review_window_minutes": WINDOW_MINUTES,
        "timestamp_local": local.isoformat(),
        "automatic_execution": False, "new_funding_required": False,
    }
    if proposal.get("status") != "PROPOSED" or proposal.get("action") not in ("BUY", "SELL"):
        return {**common, "status": "NO_ACTION", "reason": "No actionable proposal"}
    if local.weekday() >= 5 or local.hour not in REVIEW_HOURS:
        return {**common, "status": "WAIT_FOR_SESSION",
                "reason": "Review only weekdays 10:00-11:00 or 19:00-20:00 Europe/Warsaw"}
    ticker = str(proposal.get("ticker") or "").upper()
    if not ticker:
        return {**common, "status": "BLOCKED", "reason": "Missing ticker"}
    cutoff = local.date() - timedelta(days=7)
    recent = []
    for tx in portfolio.transactions:
        try:
            tx_date = datetime.strptime(tx["date"], "%Y-%m-%d").date()
        except (KeyError, TypeError, ValueError):
            return {**common, "status": "BLOCKED", "reason": "Malformed journal date"}
        if tx_date > local.date():
            return {**common, "status": "BLOCKED", "reason": "Future-dated journal transaction"}
        if tx_date > cutoff:
            recent.append(tx)
    if len(recent) >= MAX_WEEKLY_TRADES:
        return {**common, "status": "WAIT_COOLDOWN",
                "reason": "Maximum two simulated trades per rolling seven days"}
    if any(str(tx.get("ticker", "")).upper() == ticker for tx in recent):
        return {**common, "status": "WAIT_COOLDOWN",
                "reason": "Seven-day cooldown between trades in the same ticker"}
    return {**common, "status": "READY_FOR_HUMAN_REVIEW",
            "reason": "Manual review only: no virtual or real fill has been booked"}
