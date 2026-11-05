"""Geopolitical and macro headline watch: investigation leads, NEVER orders."""
from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from tradingagents.dataflows.vendors.gdelt.news import QUERIES

HORMUZ_WORDS = ("hormuz", "strait of hormuz")
SUPPLY_WORDS = ("tanker", "shipping", "blockade", "closed", "attack", "strike", "disruption", "transit")
FURTHER_CHECKS = {
    "HORMUZ_ENERGY": [
        "Verify original statements with named primary authorities and shipping traffic",
        "Compare Brent and WTI price change with the pre-news baseline",
        "Check actual transit disruption, spare production, strategic reserves and market hours",
    ],
    "ENERGY_SUPPLY": [
        "Verify physical barrel supply shock, duration and producer response",
        "Check Brent/WTI futures move, forward curve and spread",
    ],
    "MONETARY_POLICY": [
        "Verify official central bank statement and surprise versus consensus",
        "Check bond yields, foreign exchange and index reaction",
    ],
    "TRADE_SANCTIONS": [
        "Verify published legal measure, target companies and effective date",
        "Check exposures, exemptions, prior pricing and retaliatory steps",
    ],
}


def classify_articles(topic: str, articles: list[dict[str, Any]]) -> dict:
    """Deduplicate references; do not infer whether their allegations are true."""
    valid = []
    urls = set()
    domains = set()
    potential_disruption = False
    for article in articles:
        title = str(article.get("title") or "").strip()
        url = str(article.get("url") or "")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or not title or url in urls:
            continue
        urls.add(url)
        domain = parsed.hostname.lower().removeprefix("www.")
        domains.add(domain)
        lower = re.sub(r"\s+", " ", title.lower())
        if (topic == "HORMUZ_ENERGY" and any(x in lower for x in HORMUZ_WORDS)
                and any(x in lower for x in SUPPLY_WORDS)):
            potential_disruption = True
        valid.append({
            "title": title[:500], "url": url,
            "source_domain": domain, "reported_at": str(article.get("seendate") or ""),
        })
    return {
        "topic": topic, "status": "HEADLINES_FOUND" if valid else "NO_MATCHING_HEADLINES",
        "article_count": len(valid), "distinct_domains": len(domains),
        "headline_only_potential_disruption": potential_disruption,
        "evidence_level": "UNVERIFIED_MEDIA_REFERENCES",
        "event_confirmed": False,
        "market_move_confirmed": False,
        "action": "RESEARCH_ONLY",
        "requires_checks": FURTHER_CHECKS.get(topic, ["Verify original source and actual price reaction"]),
        "sources": valid[:25],
        "warning": "Multiple syndicated reports do not independently confirm an event. Do not infer a trade or profit.",
    }


def watch(*, fetcher=None, now: datetime | None = None) -> dict:
    """One report per topic; missing data blocks conclusions, not other topics."""
    if fetcher is None:
        from tradingagents.dataflows.vendors.gdelt.news import fetch_news_articles

        fetcher = fetch_news_articles
    timestamp = now or datetime.now(UTC)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("Aware timestamp required")
    topics = []
    for name, query in QUERIES.items():
        try:
            topics.append(classify_articles(name, fetcher(query=query)))
        except Exception as exc:
            topics.append({
                "topic": name, "status": "DATA_ERROR",
                "error_type": type(exc).__name__, "sources": [],
                "event_confirmed": False, "action": "RESEARCH_ONLY",
            })
    return {
        "mode": "EVENT_INTELLIGENCE_NO_ORDERS",
        "timestamp_utc": timestamp.astimezone(UTC).isoformat(),
        "status": "DATA_REVIEW_REQUIRED" if any(x["status"] == "DATA_ERROR" for x in topics) else "RESEARCH_LEADS_ONLY",
        "no_auto_buy_or_sell": True, "broker_connected": False,
        "direct_model_consultations": 0,
        "topics": topics,
        "limitations": (
            "Discovery depends on GDELT coverage and latency. Headlines can be false, "
            "duplicated, translated or delayed. No live Brent/WTI/FX marks, "
            "source verification, predictive probabilities, or execution quotes."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Untrusted market-event news leads; no brokerage or LLM")
    parser.add_argument("--output", type=Path, default=Path("scan-output/news_events.json"))
    args = parser.parse_args(argv)
    result = watch()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"], "topics": len(result["topics"]),
        "possible_headline_events": sum(
            x.get("headline_only_potential_disruption", False) for x in result["topics"]
        ), "trades": 0,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
