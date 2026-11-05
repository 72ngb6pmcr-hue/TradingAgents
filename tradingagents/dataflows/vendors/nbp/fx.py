"""Historical official NBP daily mid-market FX for PLN paper valuations."""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from urllib.request import Request, urlopen


def official_nbp_mid(ccy: str, trade_day: date) -> dict:
    """Do not roll currencies across dates or infer actual broker FX spreads."""
    if ccy == "PLN":
        return {"ccy": "PLN", "date": trade_day.isoformat(), "pln_per_unit": "1",
                "source": "Domestic PLN"}
    if ccy not in {"EUR", "USD"}:
        raise ValueError("Unsupported currency")
    url = (
        "https://api.nbp.pl/api/exchangerates/rates/a/"
        + ccy.lower() + "/" + trade_day.isoformat() + "/?format=json"
    )
    with urlopen(Request(url, headers={"User-Agent": "TradingAgents-research/1.0"}),
                 timeout=15) as response:
        content = json.load(response)
    rates = content.get("rates")
    if not isinstance(rates, list) or len(rates) != 1:
        raise ValueError("NBP rate not available for trade date")
    rate = rates[0]
    if rate.get("effectiveDate") != trade_day.isoformat():
        raise ValueError("NBP date mismatch")
    mid = Decimal(str(rate["mid"]))
    if not mid.is_finite() or mid <= 0:
        raise ValueError("Invalid NBP rate")
    return {
        "ccy": ccy, "date": trade_day.isoformat(), "pln_per_unit": str(mid),
        "source": url,
        "note": "Published NBP reference mid-market; not a broker executable FX quote",
    }
