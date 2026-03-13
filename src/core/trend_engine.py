"""
trend_engine.py
===============
Real-time trend research engine for Aisha's content channels.
Finds what's ACTUALLY trending right now — no guessing.

Data sources (all FREE, no API key needed for most):
  1. Google Trends via pytrends    — trending search topics in India
  2. YouTube Data API v3           — trending videos in entertainment/music (quota: free)
  3. DuckDuckGo Instant Answer API — zero-click web search (completely free, no key)

Usage:
  from src.core.trend_engine import get_trends_for_channel
  trends = get_trends_for_channel("Story With Aisha")
  # Returns: {"top_angles": [...], "trending_topics": [...], "viral_keywords": [...]}
"""

import os
import json
import logging
import requests
from datetime import datetime

log = logging.getLogger("Aisha.TrendEngine")

# ── Channel → Search Keywords Mapping ──────────────────────

CHANNEL_KEYWORDS = {
    "Story With Aisha": {
        "google_trends":  ["hindi love story", "romantic story hindi", "emotional story", "pyar ki kahani"],
        "youtube_search": "hindi romantic story emotional 2025",
        "ddg_query":      "trending hindi love story YouTube 2025 viral",
        "geo":            "IN",
        "category":       "romantic storytelling",
    },
    "Riya's Dark Whisper": {
        "google_trends":  ["adult hindi story", "dark romance hindi", "erotic kahani", "bold story"],
        "youtube_search": "hindi dark romance story 2025",
        "ddg_query":      "trending adult hindi story YouTube shorts 2025",
        "geo":            "IN",
        "category":       "adult storytelling",
    },
    "Riya's Dark Romance Library": {
        "google_trends":  ["mafia romance hindi", "dark romance novel hindi", "possessive hero story"],
        "youtube_search": "hindi mafia romance dark story 2025",
        "ddg_query":      "trending dark romance mafia story hindi 2025",
        "geo":            "IN",
        "category":       "dark romance novels",
    },
    "Aisha & Him": {
        "google_trends":  ["couple goals hindi", "relationship story", "boyfriend girlfriend story"],
        "youtube_search": "cute couple story hindi shorts 2025",
        "ddg_query":      "viral couple scenario Instagram reels 2025 hindi",
        "geo":            "IN",
        "category":       "couple content",
    },
}


# ── Google Trends (pytrends, FREE) ───────────────────────────

def get_google_trends(keywords: list[str], geo: str = "IN") -> list[dict]:
    """
    Fetch rising and top search trends from Google Trends.
    Uses pytrends (unofficial Google Trends API wrapper).
    """
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="hi-IN", tz=330, timeout=(5, 15))

        results = []
        # Process keywords in batches of 5 (Google Trends limit)
        for i in range(0, len(keywords), 5):
            batch = keywords[i:i+5]
            try:
                pytrends.build_payload(batch, cat=0, timeframe="now 7-d", geo=geo)

                # Get related queries (rising = explosive growth)
                related = pytrends.related_queries()
                for kw in batch:
                    if kw in related and related[kw]["rising"] is not None:
                        rising_df = related[kw]["rising"].head(5)
                        for _, row in rising_df.iterrows():
                            results.append({
                                "query": row["query"],
                                "value": int(row["value"]),
                                "type": "rising",
                                "keyword": kw,
                            })
            except Exception as e:
                log.warning(f"pytrends batch failed: {e}")
                continue

        return sorted(results, key=lambda x: x["value"], reverse=True)[:10]

    except ImportError:
        log.warning("pytrends not installed. Run: pip install pytrends")
        return []
    except Exception as e:
        log.warning(f"Google Trends failed: {e}")
        return []


# ── YouTube Trending Search (YouTube Data API v3, FREE quota) ──

def get_youtube_trending(search_query: str, max_results: int = 10) -> list[dict]:
    """
    Search YouTube for trending videos matching the query.
    Uses YouTube Data API v3 search endpoint (free quota: 10,000 units/day).
    """
    api_key = os.getenv("YOUTUBE_API_KEY") or os.getenv("GEMINI_API_KEY")  # Try both
    # Note: YouTube Data API uses a different key than Gemini
    yt_key = os.getenv("YOUTUBE_API_KEY")
    if not yt_key:
        log.warning("YOUTUBE_API_KEY not set — skipping YouTube trending search")
        return []

    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": search_query,
            "type": "video",
            "order": "viewCount",
            "publishedAfter": "2025-01-01T00:00:00Z",
            "regionCode": "IN",
            "relevanceLanguage": "hi",
            "maxResults": max_results,
            "key": yt_key,
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            log.warning(f"YouTube API returned {response.status_code}")
            return []

        data = response.json()
        results = []
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            results.append({
                "title": snippet.get("title", ""),
                "channel": snippet.get("channelTitle", ""),
                "description": snippet.get("description", "")[:100],
                "published": snippet.get("publishedAt", ""),
            })
        return results

    except Exception as e:
        log.warning(f"YouTube trending search failed: {e}")
        return []


# ── DuckDuckGo Instant Search (FREE, no API key) ─────────────

def get_duckduckgo_trends(query: str) -> list[str]:
    """
    Uses DuckDuckGo Instant Answer API to find related search topics.
    Completely free, no API key required.
    """
    try:
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
        }
        response = requests.get(url, params=params, timeout=8)
        if response.status_code != 200:
            return []

        data = response.json()
        results = []

        # Extract related topics
        for topic in data.get("RelatedTopics", [])[:8]:
            if "Text" in topic:
                results.append(topic["Text"])
            elif "Topics" in topic:
                for sub in topic["Topics"][:3]:
                    if "Text" in sub:
                        results.append(sub["Text"])

        return results[:10]

    except Exception as e:
        log.warning(f"DuckDuckGo search failed: {e}")
        return []


# ── AI-Powered Trend Synthesis ────────────────────────────────

def synthesize_trends_with_ai(
    channel: str,
    google_data: list[dict],
    youtube_data: list[dict],
    ddg_data: list[str],
) -> dict:
    """
    Uses Gemini to synthesize raw trend data into actionable story angles.
    Returns structured content strategy.
    """
    try:
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return _fallback_trend_report(channel)

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")

        # Build context from trend data
        google_summary = ", ".join([t["query"] for t in google_data[:5]]) if google_data else "Not available"
        youtube_titles = "\n".join([f"- {v['title']}" for v in youtube_data[:5]]) if youtube_data else "Not available"
        ddg_insights = "\n".join([f"- {t[:80]}" for t in ddg_data[:4]]) if ddg_data else "Not available"

        prompt = f"""You are a viral content strategist for the YouTube channel '{channel}'.

Current trend data (collected right now):

GOOGLE TRENDS (rising searches in India):
{google_summary}

TOP PERFORMING YOUTUBE VIDEOS IN THIS NICHE:
{youtube_titles}

WEB INSIGHTS (DuckDuckGo):
{ddg_insights}

Based on this data, generate a content strategy report. Return ONLY valid JSON:
{{
    "top_angles": [
        "Angle 1: specific story idea based on trend data",
        "Angle 2: second specific story idea",
        "Angle 3: third specific story idea"
    ],
    "trending_topics": ["topic1", "topic2", "topic3", "topic4", "topic5"],
    "viral_keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
    "recommended_topic": "The single best topic to make content about right now",
    "hook_idea": "One-sentence hook that will make viewers stop scrolling",
    "best_thumbnail_concept": "Description of the most clickable thumbnail"
}}"""

        response = model.generate_content(prompt)
        import re
        match = re.search(r'\{[\s\S]*\}', response.text)
        if match:
            return json.loads(match.group(0))

    except Exception as e:
        log.error(f"AI synthesis failed: {e}")

    return _fallback_trend_report(channel)


def _fallback_trend_report(channel: str) -> dict:
    """Static fallback when all APIs fail."""
    fallbacks = {
        "Story With Aisha": {
            "top_angles": [
                "Office romance where colleagues fall in love during late night deadlines",
                "Long-distance love rekindled at a common friend's wedding",
                "Train strangers who keep meeting by coincidence across India"
            ],
            "trending_topics": ["office romance", "long distance relationship", "arranged love marriage"],
            "viral_keywords": ["emotional story", "pyar ki kahani", "hindi love story", "romantic"],
            "recommended_topic": "Office colleagues who fall in love during a project deadline",
            "hook_idea": "क्या आपने कभी किसी अजनबी से इस तरह प्यार किया जैसे आप उसे हमेशा से जानते थे?",
            "best_thumbnail_concept": "Two people in office at night, warm laptop glow, eyes meeting, emotional"
        },
        "Riya's Dark Whisper": {
            "top_angles": [
                "Boss-employee forbidden attraction turning into obsession",
                "Neighbor who watches from across the building — dangerous desire",
                "College professor with a secret dark past and a student who discovers it"
            ],
            "trending_topics": ["forbidden romance", "boss employee story", "dark desire"],
            "viral_keywords": ["adult story hindi", "bold kahani", "dark romance", "riya"],
            "recommended_topic": "Forbidden boss-employee obsession in a Mumbai corporate office",
            "hook_idea": "जब वो पहली बार मेरी आँखों में देखा, मुझे पता था ये कहानी ख़तरनाक होगी...",
            "best_thumbnail_concept": "Mysterious woman in dark office, dramatic lighting, intense eye contact"
        },
    }
    return fallbacks.get(channel, {
        "top_angles": ["Fresh content idea 1", "Fresh content idea 2", "Fresh content idea 3"],
        "trending_topics": ["trending", "viral", "popular"],
        "viral_keywords": ["hindi", "story", "emotional"],
        "recommended_topic": "A compelling story for your audience",
        "hook_idea": "A powerful opening line",
        "best_thumbnail_concept": "Emotional cinematic thumbnail"
    })


# ── Main Public Function ──────────────────────────────────────

def get_trends_for_channel(channel: str) -> dict:
    """
    Main function: fetch real-time trends for a specific YouTube channel.

    Returns dict with:
      - top_angles:            3 specific story angles to make content about
      - trending_topics:       5 currently trending topics
      - viral_keywords:        5 keywords for titles/descriptions
      - recommended_topic:     Single best topic right now
      - hook_idea:             Opening line that stops scrolling
      - best_thumbnail_concept: Thumbnail description

    Usage:
      trends = get_trends_for_channel("Story With Aisha")
      topic  = trends["recommended_topic"]
    """
    config = CHANNEL_KEYWORDS.get(channel, CHANNEL_KEYWORDS["Story With Aisha"])

    log.info(f"[TrendEngine] Fetching trends for '{channel}'...")

    # Fetch from all sources in parallel-ish
    google_data = get_google_trends(config["google_trends"], config["geo"])
    log.info(f"[TrendEngine] Google Trends: {len(google_data)} results")

    youtube_data = get_youtube_trending(config["youtube_search"])
    log.info(f"[TrendEngine] YouTube: {len(youtube_data)} results")

    ddg_data = get_duckduckgo_trends(config["ddg_query"])
    log.info(f"[TrendEngine] DuckDuckGo: {len(ddg_data)} results")

    # Synthesize with AI
    result = synthesize_trends_with_ai(channel, google_data, youtube_data, ddg_data)
    result["fetched_at"] = datetime.now().isoformat()
    result["channel"] = channel

    log.info(f"[TrendEngine] Recommended topic: {result.get('recommended_topic', 'N/A')}")
    return result


def get_trending_topic_for_autonomous_loop(channel: str) -> str:
    """
    Simplified function for autonomous_loop.py — returns just the best topic string.
    """
    try:
        trends = get_trends_for_channel(channel)
        return trends.get("recommended_topic", f"Latest {channel} story")
    except Exception as e:
        log.error(f"Trend fetch failed: {e}")
        return f"Trending story for {channel}"


# ── Test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    channel = sys.argv[1] if len(sys.argv) > 1 else "Story With Aisha"
    result = get_trends_for_channel(channel)
    print(json.dumps(result, indent=2, ensure_ascii=False))
