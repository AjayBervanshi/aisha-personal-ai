"""
news_engine.py
==============
Curated news and content aggregation for Ajay.

Free data sources (no paid API needed):
  - Hacker News (tech/startup) — free public API
  - DuckDuckGo Instant Answer — zero-click, no key
  - NewsAPI free tier (100 req/day) — set NEWS_API_KEY in .env
  - Reuses trend_engine for YouTube niche trends

Used by NotificationEngine.morning_briefing() to enrich the morning message
with relevant headlines relevant to Ajay's interests (tech, finance, business).

Usage:
    news = NewsEngine()
    headlines = news.fetch_morning_headlines()
    # Returns a list of {"title": ..., "url": ..., "source": ...}
"""

import os
import logging
import requests
from typing import List, Dict, Any, Optional

from src.core.logger import get_logger

log = get_logger("NewsEngine")

_NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
_REQUEST_TIMEOUT = 5  # seconds


class NewsEngine:
    """Aggregates relevant news for Ajay's morning briefing."""

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "Aisha-Personal-AI/1.0"})

    # ── Public ─────────────────────────────────────────────────────────────

    def fetch_morning_headlines(self, max_items: int = 5) -> List[Dict[str, Any]]:
        """
        Fetch top news items from all sources, dedup, and return max_items.
        Falls back gracefully if any source fails.
        """
        items: List[Dict[str, Any]] = []
        items.extend(self._fetch_hackernews(limit=3))
        if _NEWS_API_KEY:
            items.extend(self._fetch_newsapi(limit=3))
        # Deduplicate by title similarity (simple substring check)
        seen_titles: set = set()
        deduped = []
        for item in items:
            key = item.get("title", "")[:50].lower()
            if key not in seen_titles:
                seen_titles.add(key)
                deduped.append(item)
        result = deduped[:max_items]
        log.info("event=news_fetched", count=len(result))
        return result

    def format_for_prompt(self, headlines: Optional[List[Dict]] = None) -> str:
        """Format headlines as a compact block for injection into a prompt."""
        if headlines is None:
            headlines = self.fetch_morning_headlines()
        if not headlines:
            return ""
        lines = ["Today's headlines:"]
        for h in headlines:
            source = h.get("source", "")
            title = h.get("title", "")
            lines.append(f"  • [{source}] {title}")
        return "\n".join(lines)

    def format_for_telegram(self, headlines: Optional[List[Dict]] = None) -> str:
        """Format headlines as a Telegram-ready message."""
        if headlines is None:
            headlines = self.fetch_morning_headlines()
        if not headlines:
            return "No headlines available right now."
        lines = ["*Today's Top Headlines:*\n"]
        for i, h in enumerate(headlines, 1):
            title = h.get("title", "")
            url = h.get("url", "")
            source = h.get("source", "")
            if url:
                lines.append(f"{i}. [{title}]({url}) — _{source}_")
            else:
                lines.append(f"{i}. {title} — _{source}_")
        return "\n".join(lines)

    # ── Sources ─────────────────────────────────────────────────────────────

    def _fetch_hackernews(self, limit: int = 3) -> List[Dict[str, Any]]:
        """Top stories from Hacker News (free, no key)."""
        try:
            resp = self._session.get(
                "https://hacker-news.firebaseio.com/v0/topstories.json",
                timeout=_REQUEST_TIMEOUT,
            )
            ids = resp.json()[:limit * 2]  # fetch extra to filter
            items = []
            for story_id in ids:
                if len(items) >= limit:
                    break
                try:
                    story = self._session.get(
                        f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                        timeout=_REQUEST_TIMEOUT,
                    ).json()
                    if story.get("type") == "story" and story.get("title"):
                        items.append({
                            "title": story["title"],
                            "url": story.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                            "source": "Hacker News",
                        })
                except Exception:
                    continue
            return items
        except Exception as e:
            log.warning("event=hackernews_fetch_failed", error=str(e))
            return []

    def _fetch_newsapi(self, limit: int = 3) -> List[Dict[str, Any]]:
        """Top business/tech headlines from NewsAPI (free tier: 100 req/day)."""
        if not _NEWS_API_KEY:
            return []
        try:
            resp = self._session.get(
                "https://newsapi.org/v2/top-headlines",
                params={
                    "apiKey": _NEWS_API_KEY,
                    "country": "in",
                    "category": "business",
                    "pageSize": limit,
                },
                timeout=_REQUEST_TIMEOUT,
            )
            data = resp.json()
            articles = data.get("articles", [])
            return [
                {
                    "title": a.get("title", ""),
                    "url": a.get("url", ""),
                    "source": a.get("source", {}).get("name", "NewsAPI"),
                }
                for a in articles
                if a.get("title")
            ]
        except Exception as e:
            log.warning("event=newsapi_fetch_failed", error=str(e))
            return []
