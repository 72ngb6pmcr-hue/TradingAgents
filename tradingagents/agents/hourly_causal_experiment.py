"""72-hour reproducible investigation: commodity leads and sector returns.

Exploratory research ONLY. Daily adjusted close futures proxies cannot identify
intraday information timing or causality. No trading, LLM, or brokerage calls.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import mean
from typing import Any

START = datetime(2026, 11, 12, 4, 0, tzinfo=UTC)  # 05:00 Warsaw (CET)
END = START + timedelta(hours=72)  # exclusive
UNDERLYING = "BZ=F"
CANDIDATES = ("XLE", "JETS", "XOM", "DAL", "SPY")
LAGS = (0, 1, 2, 5)
LOOKBACK = (180, 365, 730, 1460)
EVENTS = (
    ("2019-09-14", "Saudi Abqaiq oil infrastructure attack"),
    ("2020-01-02", "US-Iraq military escalation and risk premium"),
    ("2022-02-24", "Russia invasion of Ukraine, global commodity repricing"),
)
MIN_PAIRS = 40


def phase(now: datetime) -> tuple[str, int | None]:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Timezone-aware run time required")
    time = now.astimezone(UTC)
    if time < START:
        return "WAIT", None
    if time >= END:
        return "DONE", None
    return "ACTIVE", int((time - START).total_seconds() // 3600)


def returns(prices: dict[str, float]) -> dict[str, float]:
    ordered = sorted(prices)
    result: dict[str, float] = {}
    for i in range(1, len(ordered)):
        before, after = prices[ordered[i - 1]], prices[ordered[i]]
        if before > 0 and after > 0 and math.isfinite(before) and math.isfinite(after):
            result[ordered[i]] = after / before - 1
    return result


def corr(a: list[float], b: list[float]) -> float | None:
    if len(a) != len(b) or len(a) < MIN_PAIRS:
        return None
    aa, bb = mean(a), mean(b)
    var_a = sum((v - aa) ** 2 for v in a)
    var_b = sum((v - bb) ** 2 for v in b)
    if var_a <= 0 or var_b <= 0:
        return None
    return sum((x - aa) * (y - bb) for x, y in zip(a, b, strict=True)) / math.sqrt(var_a * var_b)


def lagged_relationship(brent: dict[str, float], equity: dict[str, float],
                        *, lag: int, lookback: int) -> dict[str, Any]:
    """Return correlations of Brent return(t) with equity return(t+lag).

    Uses aligned daily dates, *not* calendar offsets. lag>0 is retrospective
    lead/lag association and must NEVER be used as causal probability.
    """
    if lag < 0 or lookback < MIN_PAIRS:
        raise ValueError("Invalid lag / lookback")
    x, y = returns(brent), returns(equity)
    dates = sorted(set(x) & set(y))[-lookback:]
    pairs = [(x[dates[i]], y[dates[i + lag]]) for i in range(len(dates) - lag)]
    xs, ys = [v[0] for v in pairs], [v[1] for v in pairs]
    total = corr(xs, ys)
    half = len(xs) // 2
    first, second = corr(xs[:half], ys[:half]), corr(xs[half:], ys[half:])
    stable = (first is not None and second is not None
              and first * second > 0 and abs(first) >= 0.1 and abs(second) >= 0.1)
    return {
        "lag_sessions": lag, "lookback_sessions": lookback, "observations": len(pairs),
        "correlation": round(total, 4) if total is not None else None,
        "first_half_correlation": round(first, 4) if first is not None else None,
        "second_half_correlation": round(second, 4) if second is not None else None,
        "same_sign_halves_with_abs_at_least_0_1": stable,
        "finding_status": "EXPLORATORY_CORRELATION_NOT_CAUSATION",
    }


def event_returns(prices: dict[str, float], *, event_date: str,
                  horizons: tuple[int, ...] = (1, 5, 20, 60)) -> dict:
    """Post-event daily closes. Not a valid real-time event trading backtest."""
    days = sorted(d for d in prices if d >= event_date and prices[d] > 0)
    if not days:
        return {"status": "MISSING_DATED_PRICES"}
    base = prices[days[0]]
    return {
        "status": "RETROSPECTIVE_CLOSE_ONLY",
        "first_close_at_or_after_event": days[0],
        "returns_by_horizon": {
            str(h): round(100 * (prices[days[h]] / base - 1), 3)
            if len(days) > h else None for h in horizons
        },
        "warning": "Event-time price and first public timestamp not verified; not a tradeable signal.",
    }


def run_hour(*, now: datetime, loader, casebook: dict) -> dict:
    status, index = phase(now)
    if status != "ACTIVE":
        return {"status": status, "iteration": index, "trades": 0}
    assert index is not None
    # Rotate across pre-registered hypotheses, rather than reselecting what
    # happened to work. 80 possible combinations; 72 samples by design.
    choices = [(ticker, lag, lookback) for ticker in CANDIDATES
               for lag in LAGS for lookback in LOOKBACK]
    ticker, lag, lookback = choices[index]
    needed = [UNDERLYING, ticker]
    data, errors = {}, {}
    for symbol in needed:
        try:
            values = loader(symbol)
            filtered = {str(d): float(v) for d, v in values.items()
                        if str(d) < now.astimezone(UTC).date().isoformat()
                        and math.isfinite(float(v)) and float(v) > 0}
            if len(filtered) < 120:
                raise ValueError("Not enough completed daily close observations")
            data[symbol] = filtered
        except (ValueError, TypeError, KeyError, RuntimeError, OSError) as exc:
            errors[symbol] = {"error_type": type(exc).__name__, "reason": str(exc)[:160]}
    output: dict[str, Any] = {
        "status": "DATA_MISSING" if errors else "EXPLORATORY_RESULT",
        "iteration": index, "run_at_utc": now.astimezone(UTC).isoformat(),
        "model": "SIMPLE_CROSS_CORRELATION_NO_CAUSAL_IDENTIFICATION",
        "predeclared_test": {"commodity": UNDERLYING, "equity": ticker,
                             "lag_sessions": lag, "lookback_sessions": lookback},
        "source": "Yahoo Finance auto-adjusted EOD historical bars via yfinance; continuous Brent futures proxy",
        "source_limitations": (
            "Vendor bars can be revised or missing; futures continuous contract rolls "
            "can distort returns; time zones differ and common trading dates omit holidays."
        ),
        "errors": errors, "sample": None, "event_studies": [],
        "hypotheses_tested": 1 if not errors else 0,
        "predictions_issued": 0, "trades": 0,
        "probability": None,
    }
    if errors:
        return output
    output["sample"] = lagged_relationship(data[UNDERLYING], data[ticker],
                                           lag=lag, lookback=lookback)
    recorded = {item.get("event_date") for item in casebook.get("historical_cases", [])}
    for day, title in EVENTS:
        if day not in recorded:
            continue
        output["event_studies"].append({
            "event_date": day, "event_label": title,
            "commodity": event_returns(data[UNDERLYING], event_date=day),
            "equity": event_returns(data[ticker], event_date=day),
        })
    return output


def yahoo_daily(symbol: str) -> dict[str, float]:
    import yfinance as yf

    bars = yf.Ticker(symbol).history(period="10y", interval="1d", auto_adjust=True)
    if bars.empty:
        raise ValueError("Empty Yahoo historical response")
    return {index.date().isoformat(): float(row["Close"]) for index, row in bars.iterrows()}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path("research-data/causal-72h"))
    parser.add_argument("--now", default=None, help="ISO 8601 aware override; for tests only")
    args = parser.parse_args(argv)
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(UTC)
    status, idx = phase(now)
    if status != "ACTIVE":
        print(json.dumps({"status": status, "iteration": idx, "trades": 0}))
        return 0
    source = Path("tradingagents/knowledge/historical_event_cases.json")
    casebook = json.loads(source.read_text(encoding="utf-8"))
    result = run_hour(now=now, loader=yahoo_daily, casebook=casebook)
    args.output_root.mkdir(parents=True, exist_ok=True)
    target = args.output_root / f"iteration-{idx:02d}.json"
    # A repeated delayed scheduled run must not overwrite original evidence.
    if target.exists():
        print(json.dumps({"status": "ALREADY_RECORDED", "iteration": idx, "trades": 0}))
    else:
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
        print(json.dumps({"status": result["status"], "iteration": idx,
                          "hypotheses_tested": result["hypotheses_tested"],
                          "trades": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
