"""Deterministic GPW/US end-of-day watchlist scan. Research only.

Designed for scheduled GitHub Actions with no API key, broker access or LLM
expense. It generates candidate *observations*, not buy/sell orders. Signals
are descriptive and NOT evidence of a profitable strategy.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

WARSAW = ZoneInfo("Europe/Warsaw")
WATCHLIST = {
    "BDX.WA": ("Budimex", "GPW", "PLN"),
    "PKO.WA": ("PKO Bank Polski", "GPW", "PLN"),
    "KGH.WA": ("KGHM", "GPW", "PLN"),
    "PKN.WA": ("Orlen", "GPW", "PLN"),
    "DNP.WA": ("Dino Polska", "GPW", "PLN"),
    "NVDA": ("NVIDIA", "US", "USD"),
}


def allowed_window(now: datetime) -> bool:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Timestamp must be timezone-aware")
    local = now.astimezone(WARSAW)
    return local.weekday() < 5 and local.hour in (10, 19)


def score_history(symbol: str, bars: list[dict], now: datetime) -> dict:
    """Score completed daily closes only, with liquidity and freshness guards."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Timezone-aware timestamp required")
    local_date = now.astimezone(WARSAW).date()
    safe = []
    for bar in bars:
        try:
            d = datetime.strptime(str(bar["date"]), "%Y-%m-%d").date()
            close = float(bar["close"])
            vol = float(bar["volume"])
        except (ValueError, KeyError, TypeError):
            continue
        if d >= local_date or not math.isfinite(close) or close <= 0 or not math.isfinite(vol) or vol < 0:
            continue
        safe.append((d, close, vol))
    safe.sort()
    if len(safe) < 51:
        return {"ticker": symbol, "status": "INSUFFICIENT_DATA", "bars": len(safe)}
    safe = safe[-90:]
    last_day, last, _ = safe[-1]
    age = (local_date - last_day).days
    if age > 5:
        return {"ticker": symbol, "status": "STALE", "last_bar": last_day.isoformat(), "age_days": age}
    closes = [item[1] for item in safe]
    vols = [item[2] for item in safe]
    avg20 = sum(closes[-20:]) / 20
    avg50 = sum(closes[-50:]) / 50
    # Past-price only. No future information, intraday fill or FX conversion.
    momentum20 = 100 * (last / closes[-21] - 1)
    volatility20 = 100 * math.sqrt(sum(
        ((closes[i] / closes[i-1] - 1) ** 2) for i in range(len(closes)-19, len(closes))
    ) / 19)
    liquidity = sum(vols[-20:]) / 20
    return {
        "ticker": symbol,
        "status": "OBSERVATION",
        "bar_date": last_day.isoformat(),
        "adjusted_close_native": round(last, 4),
        "ma20": round(avg20, 4),
        "ma50": round(avg50, 4),
        "momentum_20d_pct": round(momentum20, 2),
        "daily_volatility_20d_pct": round(volatility20, 2),
        "avg_daily_volume_20d_shares": int(liquidity),
        "trend_above_ma20": last > avg20,
        "trend_above_ma50": last > avg50,
        "strength_score": int(last > avg20) + int(last > avg50) + int(momentum20 > 0),
        "limitations": "Unadjusted broker fill and current XTB availability NOT verified; price history alone does not predict profit",
    }


def scan(*, now: datetime, fetcher=None) -> dict:
    """Fetch independently for each instrument; never label gaps as a good signal."""
    if fetcher is None:
        from tradingagents.dataflows.vendors.yahoo.daily_scan import fetch_daily_bars

        fetcher = fetch_daily_bars
    rows = []
    for symbol, (name, market, currency) in WATCHLIST.items():
        try:
            scored = score_history(symbol, fetcher(symbol), now)
        except Exception as exc:
            scored = {"ticker": symbol, "status": "DATA_ERROR", "error_type": type(exc).__name__}
        rows.append({"name": name, "market": market, "listing_currency": currency, **scored})
    return {
        "mode": "UNATTENDED_RESEARCH_ONLY",
        "run_at_warsaw": now.astimezone(WARSAW).isoformat(),
        "capital_reference_pln": "10000.00",
        "trade_executed": False,
        "broker_connected": False,
        "transactions_submitted": 0,
        "scores_are_not_orders": True,
        "status": "DATA_REVIEW_REQUIRED" if any(r["status"] != "OBSERVATION" for r in rows) else "OBSERVATIONS_READY",
        "candidates": sorted(rows, key=lambda row: (
            row["status"] != "OBSERVATION", -row.get("strength_score", -1), row["ticker"]
        )),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Read-only price/volatility watchlist scan")
    parser.add_argument("--output", type=Path, default=Path("scan-output/market_scan.json"))
    parser.add_argument("--enforce-window", action="store_true")
    args = parser.parse_args(argv)
    now = datetime.now(WARSAW)
    if args.enforce_window and not allowed_window(now):
        print("SKIP: not a weekday 10:00 or 19:00 Europe/Warsaw review window")
        return 0
    result = scan(now=now)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"], "time": result["run_at_warsaw"],
        "observations": sum(r["status"] == "OBSERVATION" for r in result["candidates"]),
        "candidates": len(result["candidates"]), "artifact": str(args.output),
        "trade_executed": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
