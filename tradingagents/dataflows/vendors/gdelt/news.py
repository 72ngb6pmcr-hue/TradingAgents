"""Keyless GDELT DOC 2.0 article discovery. Headlines remain untrusted leads."""
from __future__ import annotations

import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"
QUERIES = {
    "HORMUZ_ENERGY": '("strait of hormuz" OR "hormuz strait")',
    "ENERGY_SUPPLY": '("oil supply disruption" OR "opec production" OR "oil tanker attack")',
    "MONETARY_POLICY": '("central bank rates" OR "interest rate decision")',
    "TRADE_SANCTIONS": '("new tariffs" OR "economic sanctions")',
}


def fetch_news_articles(*, query: str) -> list[dict]:
    """Read GDELT result references without executing page content.

    Transport, rate-limit or JSON errors propagate; callers must report
    DATA_ERROR rather than confuse an outage with no news.
    """
    params = urlencode({
        "query": query, "mode": "artlist", "format": "json",
        "timespan": "24h", "maxrecords": 75, "sort": "datedesc",
    })
    request = Request(
        ENDPOINT + "?" + params,
        headers={"User-Agent": "TradingAgents-paper-research/1.0"},
    )
    for attempt in range(3):
        try:
            with urlopen(request, timeout=15) as response:
                data = json.load(response)
            break
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            if isinstance(exc, HTTPError) and exc.code not in (408, 429, 500, 502, 503, 504):
                raise
            if attempt == 2:
                raise
            time.sleep(2 ** attempt * 5)
    if not isinstance(data, dict) or not isinstance(data.get("articles"), list):
        raise ValueError("Invalid or missing GDELT articles list")
    articles = []
    for item in data["articles"]:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "")
        title = str(item.get("title") or "").strip()
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or not title:
            continue
        articles.append({
            "title": title[:500], "url": url,
            "domain": parsed.hostname.lower().removeprefix("www."),
            "seendate": str(item.get("seendate") or ""),
            "language": str(item.get("language") or ""),
        })
    return articles
