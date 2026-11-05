"""Headline intelligence is independent, unverified and never trade-producing."""
from datetime import datetime, timezone

from tradingagents.agents.news_event_watch import classify_articles, watch


def test_hormuz_headline_is_not_event_confirmation():
    result = classify_articles("HORMUZ_ENERGY", [{
        "title": "Unconfirmed report: attack near Strait of Hormuz shipping lane",
        "url": "https://example.org/article1",
        "seendate": "20261105T120000Z",
    }])
    assert result["headline_only_potential_disruption"] is True
    assert result["event_confirmed"] is False
    assert result["market_move_confirmed"] is False
    assert result["action"] == "RESEARCH_ONLY"
    assert result["evidence_level"] == "UNVERIFIED_MEDIA_REFERENCES"


def test_duplicate_news_cannot_be_mistaken_for_independent_confirmation():
    same = {"title": "Hormuz tanker incident", "url": "https://news.test/a"}
    other = {"title": "Hormuz blockade claimed", "url": "https://news.test/b"}
    result = classify_articles("HORMUZ_ENERGY", [same, same, other])
    assert result["article_count"] == 2
    assert result["distinct_domains"] == 1
    assert result["event_confirmed"] is False


def test_unrelated_headline_does_not_create_disruption():
    result = classify_articles("HORMUZ_ENERGY", [{
        "title": "Hormuz tourism guide published", "url": "https://example.org/tour"
    }])
    assert result["headline_only_potential_disruption"] is False


def test_non_https_and_empty_urls_are_discarded():
    result = classify_articles("HORMUZ_ENERGY", [
        {"title": "Hormuz attack", "url": "http://unsafe.test"},
        {"title": "Hormuz attack", "url": ""},
    ])
    assert result["article_count"] == 0
    assert result["status"] == "NO_MATCHING_HEADLINES"


def test_vendor_failure_is_explicit_not_no_news():
    def fetcher(*, query):
        if "hormuz" in query:
            raise TimeoutError("unavailable")
        return []
    result = watch(fetcher=fetcher, now=datetime(2026, 11, 5, tzinfo=timezone.utc))
    assert result["status"] == "DATA_REVIEW_REQUIRED"
    assert result["topics"][0]["status"] == "DATA_ERROR"
    assert result["no_auto_buy_or_sell"] is True
    assert result["direct_model_consultations"] == 0


def test_empty_news_has_no_market_recommendation():
    result = watch(fetcher=lambda *, query: [], now=datetime(2026, 11, 5, tzinfo=timezone.utc))
    assert result["status"] == "RESEARCH_LEADS_ONLY"
    assert all(topic["action"] == "RESEARCH_ONLY" for topic in result["topics"])
    assert all(topic["event_confirmed"] is False for topic in result["topics"])
