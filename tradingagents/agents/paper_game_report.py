"""Read-only, auditable paper portfolio report. No market access or broker calls."""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from tradingagents.agents.paper_portfolio import PaperPortfolio


def build_report(root: Path) -> dict:
    portfolio = PaperPortfolio.load(root / "portfolio.json")
    strategy = json.loads((root / "strategy.json").read_text(encoding="utf-8"))
    if strategy.get("mode") != "PAPER_ONLY" or strategy.get("season") != "2026-11-05-paper-game-100k":
        raise ValueError("Unexpected paper game season")
    receipt_dir = root / "receipts"
    receipts = []
    for path in sorted(receipt_dir.glob("????-??-??.json")) if receipt_dir.exists() else []:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("session_date") != path.stem or date.fromisoformat(path.stem) < date(2026, 11, 5):
            raise ValueError(f"Invalid receipt date: {path}")
        receipts.append(data)
    recorded_ids = {tx["trade_id"] for tx in portfolio.transactions}
    evidenced_ids = set()
    for receipt in receipts:
        for fill in receipt.get("fills", []):
            if fill.get("status") != "PAPER_FILL_EOD_PROXY_NOT_EXECUTABLE":
                raise ValueError("Unexpected fill type")
            evidence = fill.get("quote_and_fx", {})
            quote, fx = evidence.get("quote", {}), evidence.get("fx", {})
            if (quote.get("date") != receipt["session_date"]
                or fx.get("date") != receipt["session_date"]
                or quote.get("executable") is not False
                or not quote.get("source") or not fx.get("source")
                or fill.get("broker_order_sent") is not False):
                raise ValueError("Fill lacks dated price/FX provenance")
            evidenced_ids.add(fill["trade_id"])
    if recorded_ids != evidenced_ids:
        raise ValueError("Ledger transactions do not match dated fill receipts")

    valuations = [(r["session_date"], r["valuation"]) for r in receipts
                  if isinstance(r.get("valuation"), dict) and
                  r["valuation"].get("equity_pln") is not None]
    latest = valuations[-1] if valuations else None
    previous = valuations[-2] if len(valuations) > 1 else None
    result = {
        "season": strategy["season"], "mode": "PAPER_ONLY",
        "cash_pln": str(portfolio.cash_pln),
        "confirmed_paper_transactions": len(portfolio.transactions),
        "real_orders": 0,
        "valuation_status": "VERIFIED_EOD_PROXY" if latest else "UNAVAILABLE",
        "latest_session": latest[0] if latest else None,
        "equity_pln": latest[1]["equity_pln"] if latest else None,
        "total_pnl_pln": latest[1]["total_pnl_pln"] if latest else None,
        "holdings": latest[1].get("holdings") if latest else None,
        "day_change_pln": (str(Decimal(latest[1]["equity_pln"]) -
                               Decimal(previous[1]["equity_pln"]))
                           if latest and previous else None),
        "benchmark": "UNAVAILABLE_UNLESS_COMPLETED_VERIFIED_TEST",
        "warning": "EOD proxy only; not executable prices or real transactions",
    }
    return result


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("paper-game"))
    args = parser.parse_args()
    report = build_report(args.root)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
