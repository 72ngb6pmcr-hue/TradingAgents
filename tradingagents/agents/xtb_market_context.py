"""Markets and trading-session context for human-paced XTB-oriented research.

No XTB account connection, trading API, execution or orders. A research
universe is NOT proof that a symbol is available on a particular XTB account.
Verify the exact XTB STC symbol before any manual trade.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

WARSAW = ZoneInfo("Europe/Warsaw")

# Examples, not recommendations or verified XTB instrument availability.
# Yahoo uses .WA for Warsaw-listed shares, but XTB display names may differ.
SAMPLE_UNIVERSE = {
    "GPW": {
        "BDX.WA": "Budimex",
        "PKO.WA": "PKO Bank Polski",
        "KGH.WA": "KGHM",
        "PKN.WA": "Orlen",
        "DNP.WA": "Dino Polska",
    },
    "US": {"NVDA": "NVIDIA"},
}


@dataclass(frozen=True)
class XtbCosts:
    """Indicative XTB share/ETF pricing for accounts below the turnover threshold.

    0% commission is subject to XTB's 100,000 EUR monthly turnover rule;
    above that threshold, standard rates differ. Conversion may cost 0.5%.
    These amounts exclude spread, slippage and potential other charges.
    """
    stock_commission_rate: Decimal = Decimal("0")
    fx_conversion_rate: Decimal = Decimal("0.005")
    monthly_turnover_limit_eur: Decimal = Decimal("100000")


def market_review_context(symbol: str, *, now: datetime) -> dict:
    """Explain when decisions might be actionable, not place orders.

    GPW is typically open on trading weekdays 09:00-17:00 local;
    exchange closures/holidays are not integrated and must be checked live.
    After 17:00 a new GPW cash-stock order is intended for a *future* session.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Timezone-aware datetime required")
    local = now.astimezone(WARSAW)
    symbol = symbol.strip().upper()
    gpw = symbol.endswith(".WA")
    weekday = local.weekday() < 5
    # Conservative regular trading window; not a broker open/closed quote.
    within_gpw_hours = weekday and 9 <= local.hour < 17
    if gpw:
        guidance = ("Potential GPW trading hours; independently verify exchange "
                    "calendar, broker availability and current quotes") if within_gpw_hours else (
                    "GPW cash session assumed closed: decision is for the next "
                    "eligible session, not an immediate fill")
    else:
        guidance = ("Non-GPW symbol: market venue, trading calendar and "
                    "DST-dependent opening hours require independent verification")
    return {
        "symbol": symbol, "market": "GPW" if gpw else "OTHER",
        "currency_hint": "PLN" if gpw else None,
        "review_local_time": local.isoformat(),
        "gpw_regular_hours_assumed": "09:00-17:00 Europe/Warsaw weekdays",
        "gpw_regular_session_possible": within_gpw_hours if gpw else None,
        "guidance": guidance,
        "broker": "XTB", "execution": "MANUAL_ONLY",
        "availability_verified": False, "order_submitted": False,
    }
