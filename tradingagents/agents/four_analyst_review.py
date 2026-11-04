"""Run all four TradingAgents research analysts, save a read-only report.

Nothing executes paper or real fills. Launch manually at a convenient time.
The session policy defines two *decision-review* windows, not two mandatory
orders; the full multi-agent graph can incur provider costs and rate limits.

Example:
 python -m tradingagents.agents.four_analyst_review --ticker NVDA --date 2026-11-03
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

ANALYSTS = ("market", "social", "news", "fundamentals")
STATE_FIELDS = (
    "company_of_interest", "trade_date", "final_rating", "final_trade_decision",
    "market_report", "sentiment_report", "news_report", "fundamentals_report",
    "investment_plan", "trader_investment_plan",
)


def saved_report(ticker: str, trade_date: str, final_state: dict[str, Any], signal: str) -> dict:
    """Only persist information needed for a reproducible preview; no secrets."""
    state = {key: str(final_state[key]) if not isinstance(final_state[key], str)
             else final_state[key]
             for key in STATE_FIELDS if final_state.get(key) is not None}
    state["company_of_interest"] = ticker.upper()
    state["trade_date"] = trade_date
    return {
        "ticker": ticker.upper(), "analysis_date": trade_date,
        "decision": str(signal), "analysts_requested": list(ANALYSTS),
        "mode": "PAPER_RESEARCH_ONLY", "state": state,
        "trade_executed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Four AI analyst reports; research only")
    parser.add_argument("--ticker", required=True, help="Yahoo ticker, e.g. NVDA")
    parser.add_argument("--date", required=True, help="Analysis date YYYY-MM-DD (completed trading session)")
    parser.add_argument("--output-dir", type=Path, default=Path("raporty"))
    args = parser.parse_args(argv)

    from dotenv import load_dotenv
    load_dotenv(".env", override=True)

    from tradingagents.default_config import DEFAULT_CONFIG, _apply_env_overrides
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    config = _apply_env_overrides(DEFAULT_CONFIG.copy())
    # Bound the free-tier analysis so the four analysts do not run unlimited
    # tool loops. Provider-specific rate limits can still reject the request.
    config["max_tool_rounds"] = min(config["max_tool_rounds"], 2)
    config["max_debate_rounds"] = min(config["max_debate_rounds"], 1)
    config["max_risk_discuss_rounds"] = min(config["max_risk_discuss_rounds"], 1)
    if config.get("max_tokens") is None:
        config["max_tokens"] = 2000
    if config.get("llm_max_retries") is None:
        config["llm_max_retries"] = 0

    graph = TradingAgentsGraph(selected_analysts=list(ANALYSTS), debug=False, config=config)
    state, signal = graph.propagate(args.ticker.upper(), args.date)
    report = saved_report(args.ticker, args.date, state, signal)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = args.output_dir / f"{args.ticker.upper()}_four_analysts_{timestamp}.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "mode": "PAPER_RESEARCH_ONLY", "analysts": list(ANALYSTS),
        "ticker": report["ticker"], "analysis_date": report["analysis_date"],
        "rating": report["decision"], "saved_report": str(output),
        "trade_executed": False,
        "next_step": "Preview with paper_preview and apply human-paced session policy",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
