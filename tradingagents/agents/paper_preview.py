"""Read-only preview of an AI recommendation against the PLN paper portfolio.

Input is a saved TradingAgents JSON report. Quotes are fetched through the
verified dated Yahoo OHLCV reader and converted into PLN for *valuation*.
Adjusted daily closes are not trade execution prices; this tool never books
fills or sends orders to an exchange/broker.

Example:
    python -m tradingagents.agents.paper_preview \
      --report raporty/NVDA_20261104_213342.json --currency USD
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from tradingagents.agents.paper_portfolio import PaperPortfolio
from tradingagents.agents.paper_review_policy import evaluate_review_window
from tradingagents.agents.paper_signal_planner import plan_paper_signal
from tradingagents.agents.pln_market_marks import verified_pln_marks


def preview_report(
    report: dict[str, Any],
    portfolio: PaperPortfolio,
    currency_by_ticker: dict[str, str],
    *,
    mark_loader: Callable[..., Any] | None = None,
    cost_model: str = "legacy",
    account_currency: str = "PLN",
    monthly_turnover_after_trade_eur: Any | None = None,
) -> dict[str, Any]:
    """Construct a purely informational paper-trading decision preview."""
    state = report.get("state")
    if not isinstance(state, dict):
        raise ValueError("Report must contain a 'state' object")
    ticker = str(state.get("company_of_interest") or "").strip().upper()
    date = str(state.get("trade_date") or "").strip()

    if not ticker or not date:
        raise ValueError("Report state is missing ticker or analysis date")
    if report.get("ticker") and str(report["ticker"]).upper() != ticker:
        raise ValueError("Report ticker disagrees with state ticker")
    if report.get("analysis_date") and str(report["analysis_date"]) != date:
        raise ValueError("Report date disagrees with state date")

    currencies = {str(k).strip().upper(): str(v).strip().upper()
                  for k, v in currency_by_ticker.items()}
    required = {ticker, *portfolio.positions}
    missing = required - currencies.keys()
    if missing:
        raise ValueError("Explicit quote currencies required for: " + ", ".join(sorted(missing)))

    marks = verified_pln_marks(
        {symbol: currencies[symbol] for symbol in sorted(required)},
        date, loader=mark_loader,
    )
    # Verified adjusted closes are appropriate for a provisional valuation,
    # but are never an execution quote. Planner outputs remain hypothetical.
    proposal = plan_paper_signal(
        state=state, portfolio=portfolio,
        prices_pln=marks["prices_pln"],
        quote_date=date,
        quote_source="Yahoo Finance adjusted daily close (indicative, not a fill quote)",
        cost_model=cost_model,
        listing_currency=currencies[ticker],
        account_currency=account_currency,
        monthly_turnover_after_trade_eur=monthly_turnover_after_trade_eur,
    )
    valuation = portfolio.valuation(marks["prices_pln"])
    return {
        "mode": "PAPER_PREVIEW_ONLY",
        "ticker": ticker, "analysis_date": date,
        "agent_rating": str(state.get("final_rating") or report.get("decision") or ""),
        "proposal": proposal,
        "human_review": evaluate_review_window(proposal, portfolio),
        "portfolio": valuation,
        "market_marks": marks["records"],
        "trade_executed": False,
        "warning": (
            "No simulated or real trade was executed. Converted adjusted closes "
            "are valuation marks, not tradeable execution prices. Currency mapping "
            "must be checked independently against each instrument's listing."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preview TradingAgents report against PLN paper portfolio")
    parser.add_argument("--report", type=Path, required=True, help="Saved TradingAgents JSON containing a state object")
    parser.add_argument("--currency", required=True, choices=("PLN", "USD", "EUR"),
                        help="Confirmed listing currency of the report's instrument")
    parser.add_argument("--ledger", type=Path,
                        help="Optional existing PAPER_ONLY ledger JSON. If omitted, use fresh 10,000 PLN cash")
    parser.add_argument("--holding-currency", action="append", default=[], metavar="TICKER:CCY",
                        help="Currency for each existing held ticker, e.g. AAPL:USD")
    parser.add_argument("--cost-model", choices=("legacy", "xtb_estimate"), default="legacy",
                        help="Fee sizing: legacy 0.25%% or indicative XTB real-stock/ETF terms")
    parser.add_argument("--account-currency", choices=("PLN", "EUR", "USD"), default="PLN")
    parser.add_argument("--monthly-turnover-after-trade-eur", default=None,
                        help="User-verified EUR monthly turnover including proposed trade")
    args = parser.parse_args(argv)

    report = json.loads(args.report.read_text(encoding="utf-8"))
    portfolio = PaperPortfolio.load(args.ledger) if args.ledger else PaperPortfolio()
    state = report.get("state") or {}
    ticker = str(state.get("company_of_interest") or "").upper()
    currencies = {ticker: args.currency}
    for item in args.holding_currency:
        if ":" not in item:
            parser.error("--holding-currency requires TICKER:PLN, TICKER:USD or TICKER:EUR")
        symbol, code = item.split(":", 1)
        if not symbol.strip() or code.upper() not in ("PLN", "USD", "EUR"):
            parser.error("Holding currency must be PLN, USD or EUR")
        currencies[symbol.strip().upper()] = code.upper()
    result = preview_report(
        report, portfolio, currencies,
        cost_model=args.cost_model,
        account_currency=args.account_currency,
        monthly_turnover_after_trade_eur=args.monthly_turnover_after_trade_eur,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
