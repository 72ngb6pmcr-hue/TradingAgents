"""Point-in-time supply/demand scenarios and lag correlations. Offline, no trades."""
from __future__ import annotations
import argparse
import json
import math
from datetime import date, datetime, timezone
from pathlib import Path


def _series(records: list[dict], as_of: str, field: str) -> dict[str, float]:
    cutoff = date.fromisoformat(as_of)
    out = {}
    for row in records:
        day = date.fromisoformat(row["date"])
        published = datetime.fromisoformat(row["published_at"].replace("Z", "+00:00"))
        if published.tzinfo is None:
            raise ValueError("published_at must contain timezone")
        if day > cutoff or published.date() > cutoff:
            continue  # no look-ahead
        if not row.get("source_url", "").startswith("https://"):
            raise ValueError("Missing HTTPS provenance")
        value = row[field]
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError("Invalid numeric value")
        if day.isoformat() in out:
            raise ValueError("Duplicate dated observation")
        out[day.isoformat()] = float(value)
    return out


def supply_demand_gap(demand: list[dict], supply: list[dict], as_of: str) -> list[dict]:
    """Compare same-period volumes with matching units, not price predictions."""
    if demand and supply and any(x.get("unit") != demand[0].get("unit") for x in demand + supply):
        raise ValueError("Demand and supply units differ")
    d = _series(demand, as_of, "value")
    s = _series(supply, as_of, "value")
    result = []
    for day in sorted(d.keys() & s.keys()):
        if d[day] <= 0 or s[day] < 0:
            raise ValueError("Demand must be positive and supply nonnegative")
        result.append({"date": day, "demand": d[day], "supply": s[day],
                       "gap_pct_of_demand": round((d[day] - s[day]) / d[day] * 100, 4),
                       "status": "OBSERVED_REPORTED_VALUES_NOT_PRICE_FORECAST"})
    return result


def lagged_return_correlations(a: list[dict], b: list[dict], as_of: str,
                               max_lag: int = 5, min_pairs: int = 12) -> list[dict]:
    """Pearson on log returns, matched dated sessions; lag is session index, not calendar days.

    Positive lag: A's earlier return compared with B's later return.
    Correlation is descriptive and does not establish causation or a trading edge.
    """
    if not 0 <= max_lag <= 30 or min_pairs < 8:
        raise ValueError("Invalid lag or sample threshold")
    x = _series(a, as_of, "close")
    y = _series(b, as_of, "close")
    dates = sorted(x.keys() & y.keys())
    if any(x[t] <= 0 or y[t] <= 0 for t in dates):
        raise ValueError("Prices must be positive")
    xr = [math.log(x[dates[i]] / x[dates[i - 1]]) for i in range(1, len(dates))]
    yr = [math.log(y[dates[i]] / y[dates[i - 1]]) for i in range(1, len(dates))]
    results = []
    for lag in range(max_lag + 1):
        xx, yy = xr[:len(xr) - lag] if lag else xr, yr[lag:]
        n = len(xx)
        if n < min_pairs:
            results.append({"lag_sessions": lag, "pairs": n, "correlation": None,
                            "status": "INSUFFICIENT_SAMPLE"})
            continue
        xm, ym = sum(xx) / n, sum(yy) / n
        vx = sum((v - xm) ** 2 for v in xx)
        vy = sum((v - ym) ** 2 for v in yy)
        if vx <= 0 or vy <= 0:
            corr = None
            status = "ZERO_VARIANCE"
        else:
            corr = round(sum((xx[i] - xm) * (yy[i] - ym) for i in range(n)) /
                         math.sqrt(vx * vy), 5)
            status = "DESCRIPTIVE_ONLY_NOT_CAUSAL"
        results.append({"lag_sessions": lag, "pairs": n, "correlation": corr, "status": status})
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="JSON with as_of, demand, supply, prices_a, prices_b")
    parser.add_argument("--output", type=Path, default=Path("scan-output/structural_market_report.json"))
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8")) if args.input else {}
    as_of = payload.get("as_of", datetime.now(timezone.utc).date().isoformat())
    report = {
        "schema_version": 1, "mode": "RESEARCH_ONLY_NO_ORDERS",
        "as_of": as_of,
        "supply_demand": supply_demand_gap(payload.get("demand", []), payload.get("supply", []), as_of),
        "lag_correlations": lagged_return_correlations(
            payload.get("prices_a", []), payload.get("prices_b", []), as_of),
        "limitations": ["No observations means no forecast", "Source URLs are provenance fields, not independent source verification",
                        "Correlations are descriptive, not causal", "No automated orders or price targets"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Supply/demand matched periods: {len(report['supply_demand'])}; no orders")


if __name__ == "__main__":
    main()
