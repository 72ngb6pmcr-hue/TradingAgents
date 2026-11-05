"""Read-only trading-signal planner for a PLN paper portfolio.

The planner cannot submit orders, modify the ledger, retrieve live quotes, or
convert currencies. A proposed fill requires a human-supplied PLN quote and
explicit execution in the PAPER_ONLY ledger after review.
"""

from __future__ import annotations

from decimal import ROUND_FLOOR, Decimal
from typing import Any

from tradingagents.agents.decision_audit import audit_decision
from tradingagents.agents.paper_portfolio import FEE_RATE, PaperPortfolio, _decimal, _money
from tradingagents.agents.xtb_cost_estimate import estimate_xtb_stock_costs


def plan_paper_signal(
    *,
    state: dict[str, Any],
    portfolio: PaperPortfolio,
    prices_pln: dict[str, Any],
    quote_date: str,
    quote_source: str,
    max_single_position_fraction: Any = "0.20",
    equity_floor_pln: Any = "9000",
    cost_model: str = "legacy",
    listing_currency: str | None = None,
    account_currency: str = "PLN",
    monthly_turnover_after_trade_eur: Any | None = None,
) -> dict[str, Any]:
    """Propose at most one hypothetical action; never execute it.

    BUY targets 10% of equity and OVERWEIGHT 20%, each capped by the
    configured allocation limit. UNDERWEIGHT trims half an existing holding
    (rounded up), SELL exits, HOLD does nothing. These are conservative
    *illustrative rules*, not investment recommendations or optimised sizing.

    All held positions require current PLN marks. If the portfolio has lost
    more than its specified floor, block *new buys*; selling remains possible.
    """
    # XTB estimation requires explicit account/listing currencies and monthly
    # turnover. Missing or unsupported data must never fall back silently to
    # the legacy fee assumption.
    if cost_model not in ("legacy", "xtb_estimate"):
        return {"status": "REVIEW", "action": "HOLD", "reason": "Unknown cost model"}
    fee_rate = FEE_RATE
    cost_label = "LEGACY_0.25_PERCENT"
    if cost_model == "xtb_estimate":
        if not listing_currency or monthly_turnover_after_trade_eur is None:
            return {"status": "REVIEW", "action": "HOLD", "reason": "Missing XTB listing currency or turnover"}
        try:
            estimate = estimate_xtb_stock_costs(
                notional_pln="100.00", listing_currency=listing_currency,
                account_currency=account_currency,
                monthly_turnover_after_trade_eur=monthly_turnover_after_trade_eur,
            )
        except (TypeError, ValueError) as exc:
            return {"status": "REVIEW", "action": "HOLD", "reason": f"Cannot estimate XTB costs: {exc}"}
        fee_rate = (Decimal("0.005") if estimate["listing_currency"] != estimate["account_currency"]
                    else Decimal("0"))
        cost_label = "XTB_ESTIMATE"

    ticker = str(state.get("company_of_interest") or "").strip().upper()
    trade_date = str(state.get("trade_date") or "").strip()
    audit = audit_decision(state, expected_ticker=ticker, expected_date=trade_date)
    if audit["status"] != "PASS" or not ticker or not trade_date:
        return {"status": "REVIEW", "action": "HOLD", "reason": "Failed decision audit", "issues": audit["issues"]}
    if quote_date != trade_date:
        return {"status": "REVIEW", "action": "HOLD", "reason": "Quote date must match analysis date"}
    if not isinstance(quote_source, str) or not quote_source.strip():
        return {"status": "REVIEW", "action": "HOLD", "reason": "Missing quote provenance"}
    if ticker not in prices_pln:
        return {"status": "REVIEW", "action": "HOLD", "reason": "Missing PLN price for instrument"}
    try:
        price = _money(_decimal(prices_pln[ticker], positive=True))
        fraction = _decimal(max_single_position_fraction, positive=True)
        floor = _money(_decimal(equity_floor_pln, positive=True))
        if not Decimal("0") < fraction <= Decimal("1") or price <= 0:
            raise ValueError("Invalid sizing or price")
        valuation = portfolio.valuation(prices_pln)
    except (TypeError, ValueError) as exc:
        return {"status": "REVIEW", "action": "HOLD", "reason": f"Invalid price or portfolio: {exc}"}

    rating = audit["rating"]
    position = portfolio.positions.get(ticker)
    held = position.quantity if position else 0
    equity = Decimal(valuation["equity_pln"])
    existing_value = price * held

    if rating == "Hold":
        return {"status": "HOLD", "action": "HOLD", "ticker": ticker, "reason": "Agent recommends maintaining exposure"}
    if rating in ("Sell", "Underweight"):
        if held == 0:
            return {"status": "HOLD", "action": "HOLD", "ticker": ticker, "reason": "No existing shares to reduce"}
        quantity = held if rating == "Sell" else (held + 1) // 2
        return {
            "status": "PROPOSED", "action": "SELL", "ticker": ticker,
            "quantity": quantity, "price_pln": str(price),
            "quote_date": quote_date, "quote_source": quote_source.strip(),
            "reason": f"Rating {rating}; simulation only, manual approval required",
        }

    if equity <= floor:
        return {"status": "BLOCKED", "action": "HOLD", "ticker": ticker,
                "reason": "Portfolio equity at or below paper-trading risk floor"}

    target_fraction = min(fraction, Decimal("0.10") if rating == "Buy" else Decimal("0.20"))
    max_target_value = _money(equity * target_fraction)
    remaining_target = max(Decimal("0"), max_target_value - existing_value)
    buying_power = min(remaining_target, portfolio.cash_pln)
    # Respect the selected fee model; protect against rounding by checking
    # the computed total rather than relying solely on this initial bound.
    quantity = int((buying_power / (price * (1 + fee_rate))).to_integral_value(rounding=ROUND_FLOOR))
    while quantity > 0:
        gross = _money(price * quantity)
        fee = _money(gross * fee_rate)
        if gross + fee <= portfolio.cash_pln and existing_value + gross <= max_target_value:
            break
        quantity -= 1
    if quantity <= 0:
        return {"status": "HOLD", "action": "HOLD", "ticker": ticker,
                "reason": "Allocation cap or cash does not allow a whole share purchase"}
    return {
        "status": "PROPOSED", "action": "BUY", "ticker": ticker,
        "quantity": quantity, "price_pln": str(price),
        "quote_date": quote_date, "quote_source": quote_source.strip(),
        "cost_model": cost_label, "estimated_fee_rate": str(fee_rate),
        "estimated_fee_pln": str(_money(_money(price * quantity) * fee_rate)),
        "reason": f"Rating {rating}; allocation limit {fraction}; simulation only, manual approval required",
    }
