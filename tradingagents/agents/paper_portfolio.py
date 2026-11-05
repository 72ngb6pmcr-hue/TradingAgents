"""Offline, PLN-denominated paper-trading ledger.

No broker, network connection, trade execution API, leverage or short selling.
All fills require a user-supplied PLN price; FX conversions happen upstream.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

CENT = Decimal("0.01")
FEE_RATE = Decimal("0.0025")


def _decimal(value: Any, *, positive: bool = False) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("Boolean is not an amount")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Invalid monetary amount") from exc
    if not number.is_finite() or (positive and number <= 0):
        raise ValueError("Amount must be finite" + (" and positive" if positive else ""))
    return number


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _shares(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("Quantity must be a positive integer number of shares")
    return value


@dataclass
class Position:
    quantity: int = 0
    cost_basis_pln: Decimal = Decimal("0.00")


@dataclass
class PaperPortfolio:
    initial_cash_pln: Decimal = Decimal("10000.00")
    cash_pln: Decimal = field(init=False)
    positions: dict[str, Position] = field(default_factory=dict)
    transactions: list[dict[str, Any]] = field(default_factory=list)
    realized_pnl_pln: Decimal = Decimal("0.00")

    def __post_init__(self) -> None:
        self.initial_cash_pln = _money(_decimal(self.initial_cash_pln, positive=True))
        self.cash_pln = self.initial_cash_pln

    def trade(self, *, side: str, ticker: str, quantity: int,
              price_pln: Any, trade_id: str, date: str,
              fee_rate: Any | None = None) -> dict[str, Any]:
        """Record one simulated fill at a specified PLN price.

        trade_id prevents repeated execution. Legacy fee is 0.25% of gross.
        An explicit fee_rate overrides this for a broker-cost estimate; the
        override is persisted in the journal and checked when replaying.
        Shares must be whole, no credit or shorts.
        """
        side = side.upper()
        ticker = ticker.strip().upper() if isinstance(ticker, str) else ""
        if side not in {"BUY", "SELL"}:
            raise ValueError("Side must be BUY or SELL")
        if not ticker or not ticker.replace(".", "").replace("-", "").isalnum():
            raise ValueError("Invalid ticker")
        quantity = _shares(quantity)
        price = _money(_decimal(price_pln, positive=True))
        if price <= 0:
            raise ValueError("Price rounds to zero")
        if not isinstance(trade_id, str) or not trade_id.strip():
            raise ValueError("Non-empty trade_id is required")
        if not isinstance(date, str) or not date.strip():
            raise ValueError("Non-empty trade date is required")
        if any(tx["trade_id"] == trade_id for tx in self.transactions):
            raise ValueError("Duplicate trade_id")

        gross = _money(price * quantity)
        rate = FEE_RATE if fee_rate is None else _decimal(fee_rate)
        if not Decimal("0") <= rate < Decimal("1"):
            raise ValueError("Invalid fee rate")
        fee = _money(gross * rate)
        position = self.positions.get(ticker)
        pnl = Decimal("0.00")

        if side == "BUY":
            total = gross + fee
            if total > self.cash_pln:
                raise ValueError("Insufficient virtual cash")
            if position is None:
                position = Position()
                self.positions[ticker] = position
            position.quantity += quantity
            position.cost_basis_pln += total
            self.cash_pln -= total
        else:
            if position is None or position.quantity < quantity:
                raise ValueError("Cannot sell more shares than held")
            # Average-cost basis; sell all remaining shares to avoid residual
            # rounding drift from proportional cost allocations.
            if quantity == position.quantity:
                released_cost = position.cost_basis_pln
            else:
                released_cost = _money(position.cost_basis_pln * quantity / position.quantity)
            proceeds = gross - fee
            pnl = proceeds - released_cost
            position.quantity -= quantity
            position.cost_basis_pln -= released_cost
            if position.quantity == 0:
                del self.positions[ticker]
            self.realized_pnl_pln += pnl
            self.cash_pln += proceeds

        record = {
            "trade_id": trade_id, "date": date, "side": side, "ticker": ticker,
            "quantity": quantity, "price_pln": str(price),
            "gross_pln": str(gross), "fee_pln": str(fee),
            "realized_pnl_pln": str(pnl),
        }
        if fee_rate is not None:
            record["fee_rate"] = str(rate)
        self.transactions.append(record)
        return record

    def valuation(self, prices_pln: dict[str, Any]) -> dict[str, Any]:
        """Mark positions to supplied PLN prices; never silently assume quotes."""
        market_value = Decimal("0.00")
        holdings: dict[str, Any] = {}
        for ticker, position in sorted(self.positions.items()):
            if ticker not in prices_pln:
                raise ValueError(f"Missing mark-to-market price for {ticker}")
            price = _money(_decimal(prices_pln[ticker], positive=True))
            value = _money(price * position.quantity)
            market_value += value
            holdings[ticker] = {
                "quantity": position.quantity,
                "cost_basis_pln": str(position.cost_basis_pln),
                "market_value_pln": str(value),
                "unrealized_pnl_pln": str(value - position.cost_basis_pln),
            }
        equity = self.cash_pln + market_value
        return {
            "currency": "PLN",
            "cash_pln": str(self.cash_pln),
            "market_value_pln": str(market_value),
            "equity_pln": str(equity),
            "total_pnl_pln": str(equity - self.initial_cash_pln),
            "realized_pnl_pln": str(self.realized_pnl_pln),
            "holdings": holdings,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1, "mode": "PAPER_ONLY", "currency": "PLN",
            "initial_cash_pln": str(self.initial_cash_pln),
            "cash_pln": str(self.cash_pln),
            "realized_pnl_pln": str(self.realized_pnl_pln),
            "positions": {
                ticker: {"quantity": p.quantity, "cost_basis_pln": str(p.cost_basis_pln)}
                for ticker, p in self.positions.items()
            },
            "transactions": self.transactions,
        }

    def save(self, filename: str | Path) -> None:
        """Persist ledger via atomic rename, avoiding partial JSON writes."""
        path = Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        try:
            with temporary.open("w", encoding="utf-8") as file:
                json.dump(self.to_dict(), file, ensure_ascii=False, indent=2)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    @classmethod
    def load(cls, filename: str | Path) -> PaperPortfolio:
        data = json.loads(Path(filename).read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or data.get("mode") != "PAPER_ONLY" or data.get("currency") != "PLN":
            raise ValueError("Unexpected portfolio file format")
        portfolio = cls(initial_cash_pln=_decimal(data["initial_cash_pln"], positive=True))
        # Replay journal: do not trust serialized cash, quantities or profit.
        for tx in data["transactions"]:
            record = portfolio.trade(
                side=tx["side"], ticker=tx["ticker"], quantity=tx["quantity"],
                price_pln=tx["price_pln"], trade_id=tx["trade_id"], date=tx["date"],
                fee_rate=tx.get("fee_rate"),
            )
            if record != tx:
                raise ValueError("Inconsistent transaction journal")
        if portfolio.to_dict() != data:
            raise ValueError("Portfolio totals do not match transaction journal")
        return portfolio
