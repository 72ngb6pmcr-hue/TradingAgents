"""Deterministic one-time paper-game entries; never sends a brokerage order.

Same-day unadjusted closing marks are *hypothetical* fills. A trader could not
guarantee the closing price after observing it. We explicitly charge 0.25% per
side and persist every modelled fill, its source and FX reference.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import ROUND_FLOOR, Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from tradingagents.agents.paper_portfolio import PaperPortfolio

WARSAW = ZoneInfo("Europe/Warsaw")
FEE = Decimal("0.0025")
START_DAY = "2026-11-05"
CLOSE_HOUR = 19


def paper_session_allowed(now: datetime) -> bool:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Timezone-aware timestamp required")
    local = now.astimezone(WARSAW)
    return (local.weekday() < 5 and local.hour >= CLOSE_HOUR
            and local.date().isoformat() >= START_DAY)


def run_game(
    portfolio: PaperPortfolio,
    strategy: dict[str, Any],
    *,
    now: datetime,
    close_loader=None,
    fx_loader=None,
) -> dict:
    """One session's conditional EOD proxy fills, missing prices => no fill."""
    if not paper_session_allowed(now):
        return {"status": "WAIT_FOR_COMPLETED_SESSION", "fills": [],
                "errors": [], "trade_executed": False}
    if close_loader is None:
        from tradingagents.dataflows.vendors.yahoo.raw_eod import finished_raw_close

        close_loader = finished_raw_close
    if fx_loader is None:
        from tradingagents.dataflows.vendors.nbp.fx import official_nbp_mid

        fx_loader = official_nbp_mid
    if (strategy.get("mode") != "PAPER_ONLY"
            or strategy.get("schema_version") != 1
            or Decimal(str(strategy["initial_cash_pln"])) != portfolio.initial_cash_pln):
        raise ValueError("Strategy/portfolio mismatch")
    if strategy.get("fill_method") != "SAME_DAY_UNADJUSTED_CLOSE_EOD_PROXY_NOT_EXECUTABLE":
        raise ValueError("Unknown execution price model")

    day = now.astimezone(WARSAW).date()
    if day.isoformat() < strategy.get("first_eligible_fill_date", START_DAY):
        return {"status": "WAIT_FOR_FIRST_ELIGIBLE_SESSION", "fills": [],
                "errors": [], "trade_executed": False}
    reserve = Decimal(str(strategy.get("min_initial_cash_reserve_pln", strategy.get("event_reserve_pln", "0"))))
    errors: list[dict] = []
    receipts: list[dict] = []
    prices: dict[str, str] = {}
    quote_cache: dict[str, dict] = {}
    fx_cache: dict[str, dict] = {}

    for target in strategy["one_time_initial_targets"]:
        ticker = target["ticker"]
        ccy = target["ccy"]
        trade_id = "initial-20261105-" + ticker
        try:
            quote = close_loader(ticker, day)
            if quote.get("date") != day.isoformat() or quote.get("executable") is not False:
                raise ValueError("Undated or improperly labelled raw close")
            if Decimal(str(quote.get("volume", "0"))) <= 0:
                raise ValueError("Empty market volume")
            if quote.get("symbol") != ticker:
                raise ValueError("Symbol mismatch")
            fx = fx_cache.get(ccy)
            if fx is None:
                fx = fx_loader(ccy, day)
                fx_cache[ccy] = fx
            if fx.get("date") != day.isoformat() or fx.get("ccy") != ccy:
                raise ValueError("Foreign exchange date or currency mismatch")
            price_native = Decimal(str(quote["close_native"]))
            rate = Decimal(str(fx["pln_per_unit"]))
            if not all(x.is_finite() and x > 0 for x in (price_native, rate)):
                raise ValueError("Invalid instrument price or FX rate")
            # Single PLN cent precision is the ledger's explicit approximation.
            price_pln = (price_native * rate).quantize(Decimal("0.01"))
            if price_pln <= 0:
                raise ValueError("Price too small")
            quote_cache[ticker] = {
                "quote": quote, "fx": fx, "reference_price_pln": str(price_pln),
            }
            prices[ticker] = str(price_pln)
            if any(tx["trade_id"] == trade_id for tx in portfolio.transactions):
                continue
            budget = Decimal(str(target["target_pln"]))
            max_weight = Decimal(str(strategy["max_position_weight"]))
            if budget > portfolio.initial_cash_pln * max_weight:
                raise ValueError("Instrument exceeds weight limit")
            # Preserve reserve even if earlier trades were skipped/partially filled.
            budget = min(budget, portfolio.cash_pln - reserve)
            if budget <= 0:
                continue
            qty = int((budget / (price_pln * (1 + FEE))).to_integral_value(rounding=ROUND_FLOOR))
            if qty < 1:
                errors.append({"ticker": ticker, "status": "PENDING",
                               "reason": "Target does not cover 1 unit plus fee"})
                continue
            tx = portfolio.trade(
                side="BUY", ticker=ticker, quantity=qty, price_pln=str(price_pln),
                trade_id=trade_id, date=day.isoformat(), fee_rate=str(FEE),
            )
            receipts.append({
                "status": "PAPER_FILL_EOD_PROXY_NOT_EXECUTABLE", **tx,
                "instrument": target["role"], "market": target["market"],
                "instrument_currency": ccy, "quote_and_fx": quote_cache[ticker],
                "time_model": "Decision made before market close; close known only afterwards.",
                "broker_order_sent": False,
            })
        except (ValueError, KeyError, TypeError, ArithmeticError, ConnectionError,
                TimeoutError, OSError) as exc:
            errors.append({
                "ticker": ticker, "status": "PENDING_MISSING_OR_INVALID_DATA",
                "error_type": type(exc).__name__, "reason": str(exc)[:160],
            })

    valuation: dict | None = None
    try:
        # Never value a held instrument using an earlier day or missing quote.
        marks = {ticker: prices[ticker] for ticker in portfolio.positions}
        valuation = portfolio.valuation(marks)
    except (ValueError, KeyError):
        errors.append({"status": "VALUATION_INCOMPLETE",
                       "reason": "One or more holdings lack same-date market marks"})
    return {
        "status": ("PARTIAL_DATA" if errors else "EOD_PAPER_RECONCILED"),
        "mode": "PAPER_ONLY", "trade_executed": False,
        "simulated_fills": len(receipts), "fills": receipts,
        "errors": errors, "valuation": valuation,
        "session_date": day.isoformat(),
        "processed_at_warsaw": now.astimezone(WARSAW).isoformat(),
        "cost_model": "0.25% on each simulated trade leg (broker FX spread not separately modeled)",
        "warning": "EOD close proxy may be unachievable in real markets; no real orders.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Paper-only 100k portfolio reconciliation")
    parser.add_argument("--root", type=Path, default=Path("paper-game"))
    parser.add_argument("--enforce-window", action="store_true")
    args = parser.parse_args(argv)
    now = datetime.now(WARSAW)
    if args.enforce_window and not paper_session_allowed(now):
        print("SKIP: not a weekday completed-session paper window")
        return 0
    strategy = json.loads((args.root / "strategy.json").read_text(encoding="utf-8"))
    portfolio = PaperPortfolio.load(args.root / "portfolio.json")
    result = run_game(portfolio, strategy, now=now)
    # The quote receipts are persisted independently, one file per session.
    if result.get("status") not in {"WAIT_FOR_COMPLETED_SESSION", "WAIT_FOR_FIRST_ELIGIBLE_SESSION"}:
        args.root.joinpath("receipts").mkdir(parents=True, exist_ok=True)
        receipt = args.root / "receipts" / (result["session_date"] + ".json")
        if receipt.exists():
            # Preserve original fill evidence on manual retries or partial data.
            previous = json.loads(receipt.read_text(encoding="utf-8"))
            seen = {row["trade_id"] for row in previous.get("fills", [])}
            combined = previous.get("fills", []) + [
                row for row in result["fills"] if row["trade_id"] not in seen
            ]
            result["fills"] = combined
            result["simulated_fills"] = len(combined)
        receipt.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        portfolio.save(args.root / "portfolio.json")
    print(json.dumps({
        "status": result["status"], "paper_fills": result.get("simulated_fills", 0),
        "pending_errors": len(result.get("errors", [])),
        "real_orders": 0,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
