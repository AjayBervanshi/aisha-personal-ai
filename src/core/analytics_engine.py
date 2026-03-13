"""
analytics_engine.py
===================
Pulls YouTube Analytics and Instagram Insights into Supabase content_performance table.
Gives Aisha data to decide what content is working and what to make more of.

YouTube Analytics API  — free (uses OAuth token from setup_youtube_oauth.py)
Instagram Graph API    — free (uses token from setup_instagram_token.py)
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta

log = logging.getLogger("Aisha.Analytics")

YOUTUBE_TOKEN_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "tokens", "youtube_token.json"
)


# ── YouTube Analytics ─────────────────────────────────────────

def _get_youtube_access_token() -> str | None:
    """Load YouTube OAuth access token, refresh if needed."""
    if not os.path.exists(YOUTUBE_TOKEN_PATH):
        log.warning(f"YouTube token not found at {YOUTUBE_TOKEN_PATH}. Run: python scripts/setup_youtube_oauth.py")
        return None

    try:
        with open(YOUTUBE_TOKEN_PATH, "r") as f:
            token_data = json.load(f)

        # Check if token needs refresh
        expiry_str = token_data.get("token_expiry")
        if expiry_str:
            expiry = datetime.fromisoformat(expiry_str)
            if datetime.now() >= expiry - timedelta(minutes=5):
                return _refresh_youtube_token(token_data)

        return token_data.get("access_token")

    except Exception as e:
        log.error(f"Failed to load YouTube token: {e}")
        return None


def _refresh_youtube_token(token_data: dict) -> str | None:
    """Refresh an expired YouTube access token using the refresh token."""
    try:
        refresh_token = token_data.get("refresh_token")
        client_id = os.getenv("YOUTUBE_CLIENT_ID")
        client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")

        if not all([refresh_token, client_id, client_secret]):
            log.error("Missing credentials for token refresh")
            return None

        response = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }, timeout=10)

        if response.status_code == 200:
            new_data = response.json()
            token_data["access_token"] = new_data["access_token"]
            token_data["token_expiry"] = (
                datetime.now() + timedelta(seconds=new_data.get("expires_in", 3600))
            ).isoformat()

            # Save updated token
            os.makedirs(os.path.dirname(YOUTUBE_TOKEN_PATH), exist_ok=True)
            with open(YOUTUBE_TOKEN_PATH, "w") as f:
                json.dump(token_data, f)

            log.info("YouTube token refreshed successfully")
            return token_data["access_token"]
        else:
            log.error(f"Token refresh failed: {response.status_code} {response.text}")
            return None

    except Exception as e:
        log.error(f"Token refresh error: {e}")
        return None


def get_youtube_channel_stats(channel_id: str = None) -> dict:
    """
    Get channel-level stats: subscribers, total views, video count.
    Uses YouTube Data API v3 (free quota).
    """
    access_token = _get_youtube_access_token()
    if not access_token:
        return {}

    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {
            "part": "statistics",
            "mine": "true" if not channel_id else None,
            "id": channel_id if channel_id else None,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        response = requests.get(
            "https://www.googleapis.com/youtube/v3/channels",
            headers=headers, params=params, timeout=10
        )

        if response.status_code != 200:
            log.warning(f"YouTube channel stats failed: {response.status_code}")
            return {}

        data = response.json()
        items = data.get("items", [])
        if not items:
            return {}

        stats = items[0].get("statistics", {})
        return {
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "view_count": int(stats.get("viewCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
        }

    except Exception as e:
        log.error(f"YouTube channel stats error: {e}")
        return {}


def get_youtube_video_analytics(video_id: str, days_back: int = 28) -> dict:
    """
    Get per-video analytics: views, watch time, likes, CTR.
    Uses YouTube Analytics API (free quota).
    """
    access_token = _get_youtube_access_token()
    if not access_token:
        return {}

    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        response = requests.get(
            "https://youtubeanalytics.googleapis.com/v2/reports",
            headers=headers,
            params={
                "ids": "channel==MINE",
                "startDate": start_date,
                "endDate": end_date,
                "metrics": "views,estimatedMinutesWatched,averageViewDuration,likes,comments,shares,subscribersGained",
                "dimensions": "video",
                "filters": f"video=={video_id}",
                "maxResults": 1,
            },
            timeout=10
        )

        if response.status_code != 200:
            log.warning(f"YouTube video analytics failed: {response.status_code} {response.text}")
            return {}

        data = response.json()
        rows = data.get("rows", [])
        if not rows:
            return {}

        row = rows[0]
        headers_list = [h["name"] for h in data.get("columnHeaders", [])]
        result = dict(zip(headers_list, row))

        return {
            "views": int(result.get("views", 0)),
            "watch_time_minutes": float(result.get("estimatedMinutesWatched", 0)),
            "avg_view_duration_sec": float(result.get("averageViewDuration", 0)),
            "likes": int(result.get("likes", 0)),
            "comments": int(result.get("comments", 0)),
            "shares": int(result.get("shares", 0)),
            "subscribers_gained": int(result.get("subscribersGained", 0)),
        }

    except Exception as e:
        log.error(f"YouTube video analytics error: {e}")
        return {}


def get_recent_youtube_videos(max_results: int = 10) -> list[dict]:
    """
    Get list of recently uploaded videos with their IDs and titles.
    """
    access_token = _get_youtube_access_token()
    if not access_token:
        return []

    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            headers=headers,
            params={
                "part": "snippet",
                "forMine": "true",
                "type": "video",
                "order": "date",
                "maxResults": max_results,
            },
            timeout=10
        )

        if response.status_code != 200:
            return []

        data = response.json()
        videos = []
        for item in data.get("items", []):
            videos.append({
                "video_id": item["id"]["videoId"],
                "title": item["snippet"]["title"],
                "published_at": item["snippet"]["publishedAt"],
                "channel_title": item["snippet"]["channelTitle"],
            })
        return videos

    except Exception as e:
        log.error(f"YouTube video list error: {e}")
        return []


# ── Instagram Analytics ────────────────────────────────────────

def get_instagram_media_insights(media_id: str = None) -> list[dict]:
    """
    Get Instagram post/reel performance metrics.
    Uses Instagram Graph API (free).
    """
    access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    business_id = os.getenv("INSTAGRAM_BUSINESS_ID")

    if not access_token or not business_id:
        log.warning("Instagram credentials not configured")
        return []

    try:
        # Get recent media if no specific ID
        if not media_id:
            media_url = f"https://graph.facebook.com/v19.0/{business_id}/media"
            media_response = requests.get(media_url, params={
                "fields": "id,caption,media_type,timestamp,like_count,comments_count",
                "access_token": access_token,
                "limit": 10,
            }, timeout=10)

            if media_response.status_code != 200:
                log.warning(f"Instagram media list failed: {media_response.status_code}")
                return []

            media_items = media_response.json().get("data", [])
        else:
            media_items = [{"id": media_id}]

        results = []
        for item in media_items:
            m_id = item["id"]
            insights_url = f"https://graph.facebook.com/v19.0/{m_id}/insights"
            ins_response = requests.get(insights_url, params={
                "metric": "reach,impressions,saved,shares",
                "access_token": access_token,
            }, timeout=10)

            metrics = {}
            if ins_response.status_code == 200:
                for metric in ins_response.json().get("data", []):
                    metrics[metric["name"]] = metric["values"][0]["value"]

            results.append({
                "media_id": m_id,
                "caption": item.get("caption", "")[:100],
                "media_type": item.get("media_type", ""),
                "timestamp": item.get("timestamp", ""),
                "likes": item.get("like_count", 0),
                "comments": item.get("comments_count", 0),
                "reach": metrics.get("reach", 0),
                "impressions": metrics.get("impressions", 0),
                "saved": metrics.get("saved", 0),
                "shares": metrics.get("shares", 0),
            })

        return results

    except Exception as e:
        log.error(f"Instagram analytics error: {e}")
        return []


# ── Supabase Sync ─────────────────────────────────────────────

def pull_and_store_analytics(supabase_client=None):
    """
    Pull analytics from YouTube + Instagram and store in content_performance table.
    Called by autonomous_loop.py weekly.
    """
    if not supabase_client:
        from supabase import create_client
        supabase_client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_KEY")
        )

    log.info("[Analytics] Starting analytics pull...")
    stored_count = 0

    # YouTube analytics
    videos = get_recent_youtube_videos(max_results=20)
    for video in videos:
        try:
            video_analytics = get_youtube_video_analytics(video["video_id"])
            if video_analytics:
                supabase_client.table("content_performance").upsert({
                    "platform": "youtube",
                    "content_id": video["video_id"],
                    "title": video["title"],
                    "channel_name": video["channel_title"],
                    "views": video_analytics.get("views", 0),
                    "watch_time_minutes": video_analytics.get("watch_time_minutes", 0),
                    "likes": video_analytics.get("likes", 0),
                    "comments": video_analytics.get("comments", 0),
                    "shares": video_analytics.get("shares", 0),
                    "subscribers_gained": video_analytics.get("subscribers_gained", 0),
                    "pulled_at": datetime.now().isoformat(),
                }, on_conflict="content_id").execute()
                stored_count += 1
        except Exception as e:
            log.warning(f"Failed to store YouTube analytics for {video['video_id']}: {e}")

    # Instagram analytics
    ig_media = get_instagram_media_insights()
    for item in ig_media:
        try:
            supabase_client.table("content_performance").upsert({
                "platform": "instagram",
                "content_id": item["media_id"],
                "title": item.get("caption", "Instagram post")[:100],
                "views": item.get("impressions", 0),
                "likes": item.get("likes", 0),
                "comments": item.get("comments", 0),
                "shares": item.get("shares", 0),
                "reach": item.get("reach", 0),
                "saved": item.get("saved", 0),
                "pulled_at": datetime.now().isoformat(),
            }, on_conflict="content_id").execute()
            stored_count += 1
        except Exception as e:
            log.warning(f"Failed to store Instagram analytics for {item['media_id']}: {e}")

    log.info(f"[Analytics] Stored {stored_count} analytics records")
    return stored_count


def get_top_performing_content(supabase_client=None, limit: int = 5) -> list[dict]:
    """
    Returns the top performing content from content_performance table.
    Used by autonomous_loop.py to decide what to make more of.
    """
    if not supabase_client:
        from supabase import create_client
        supabase_client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_KEY")
        )

    try:
        result = supabase_client.table("content_performance") \
            .select("*") \
            .order("views", desc=True) \
            .limit(limit) \
            .execute()
        return result.data or []
    except Exception as e:
        log.error(f"Failed to get top content: {e}")
        return []


# ── Test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    print("YouTube channel stats:", get_youtube_channel_stats())
    print("Instagram insights:", get_instagram_media_insights())
