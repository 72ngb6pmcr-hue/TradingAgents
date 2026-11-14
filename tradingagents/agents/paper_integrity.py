"""Fail-closed paper ledger integrity preflight. Never repairs historical records."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def audit(root: Path) -> dict:
    portfolio = json.loads((root / "portfolio.json").read_text(encoding="utf-8"))
    strategy = json.loads((root / "strategy.json").read_text(encoding="utf-8"))
    if portfolio.get("mode") != "PAPER_ONLY" or strategy.get("mode") != "PAPER_ONLY":
        raise ValueError("Not a paper-only ledger")
    if strategy.get("season") != "2026-11-05-paper-game-100k":
        raise ValueError("Wrong season")
    transactions = portfolio.get("transactions", [])
    ids = [row["trade_id"] for row in transactions]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate ledger trade IDs")
    missing = []
    invalid = []
    for tx in transactions:
        path = root / "receipts" / (tx["date"] + ".json")
        if not path.is_file():
            missing.append({"trade_id": tx["trade_id"], "receipt": str(path)})
            continue
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
            fills = [row for row in receipt.get("fills", []) if row.get("trade_id") == tx["trade_id"]]
            if receipt.get("session_date") != tx["date"] or len(fills) != 1:
                invalid.append({"trade_id": tx["trade_id"], "reason": "missing or duplicate fill"})
                continue
            fill = fills[0]
            evidence = fill.get("quote_and_fx") or {}
            quote, fx = evidence.get("quote") or {}, evidence.get("fx") or {}
            if (fill.get("status") != "PAPER_FILL_EOD_PROXY_NOT_EXECUTABLE"
                or fill.get("broker_order_sent") is not False
                or quote.get("date") != tx["date"]
                or fx.get("date") != tx["date"]
                or quote.get("executable") is not False
                or not str(quote.get("source", "")).startswith("https://")
                or not str(fx.get("source", "")).startswith("https://")
                or any(fill.get(k) != v for k, v in tx.items())):
                invalid.append({"trade_id": tx["trade_id"], "reason": "provenance or ledger mismatch"})
        except (OSError, ValueError, TypeError, KeyError):
            invalid.append({"trade_id": tx["trade_id"], "reason": "unreadable receipt"})
    status = "PASS" if not missing and not invalid else "BLOCKED_LEDGER_INCONSISTENCY"
    return {"status": status, "mode": "PAPER_ONLY", "ledger_transactions": len(ids),
            "missing_receipts": missing, "invalid_receipts": invalid,
            "new_orders_allowed": status == "PASS",
            "real_orders": 0,
            "warning": "Preflight checks recorded provenance structure; does not independently verify external quotes or FX."}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("paper-game"))
    parser.add_argument("--output", type=Path, default=Path("scan-output/paper_integrity.json"))
    args = parser.parse_args()
    result = audit(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
