"""
performance_tracker.py
======================
Aisha's content performance feedback loop.

Fetches YouTube Analytics for every published episode, writes stats back to
aisha_episodes, and surfaces top-performing topics so the studio session can
weight future content towards what the audience loves.

All YouTube API calls use google-api-python-client with credentials loaded
exactly the same way as social_media_engine.py (DB → token file fallback).
All Supabase writes use direct REST (requests) to avoid supabase-py quirks
with UPSERT and column discovery.
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import requests as _req

log = logging.getLogger("Aisha.PerformanceTracker")

# ---------------------------------------------------------------------------
# Internal helpers — mirror social_media_engine.py patterns
# ---------------------------------------------------------------------------

def _sb_rest(path: str, method: str = "GET", payload: dict = None) -> dict:
    """
    Thin wrapper around Supabase REST API.
    path example: '/aisha_episodes?id=eq.abc123'
    """
    url = os.getenv("SUPABASE_URL", "").rstrip("/") + "/rest/v1" + path
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    try:
        resp = _req.request(
            method,
            url,
            headers=headers,
            json=payload,
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}
    except Exception as e:
        log.error(f"[Supabase REST] {method} {path} failed: {e}")
        return {}


def _load_db_secret(name: str) -> Optional[str]:
    """Fetch a secret from api_keys table (mirrors social_media_engine.py)."""
    try:
        from supabase import create_client
        sb = create_client(
            os.getenv("SUPABASE_URL", ""),
            os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        )
        row = sb.table("api_keys").select("secret").eq("name", name).eq("active", True).single().execute()
        return row.data["secret"] if row.data else None
    except Exception as e:
        log.warning(f"[api_keys] Could not load '{name}' from DB: {e}")
        return None


def _get_youtube_credentials():
    """
    Load YouTube OAuth credentials.
    Priority: DB (api_keys) → tokens/youtube_token.json
    Returns a google.oauth2.credentials.Credentials object or raises.
    """
    from google.oauth2.credentials import Credentials

    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")

    # 1. Try Supabase api_keys table
    raw = _load_db_secret("YOUTUBE_OAUTH_TOKEN")
    if raw:
        try:
            token_data = json.loads(raw)
            return Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=token_data.get("client_id") or client_id,
                client_secret=token_data.get("client_secret") or client_secret,
                scopes=token_data.get("scopes"),
            )
        except (json.JSONDecodeError, TypeError):
            pass

    # 2. Token file fallback
    for path in ["tokens/youtube_token.json"]:
        if os.path.exists(path):
            log.warning(f"[PerformanceTracker] Using token file fallback: {path}")
            return Credentials.from_authorized_user_file(path)

    raise FileNotFoundError(
        "No YouTube OAuth token found. Run setup_youtube_oauth.py or insert into api_keys table."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_video_stats(video_id: str) -> dict:
    """
    Fetch performance stats for a YouTube video via the YouTube Data API v3.

    Returns a dict with:
        video_id, views, likes, comments, avg_view_duration_seconds,
        impressions, ctr, fetched_at

    Falls back gracefully if YouTube Analytics scope is missing — returns
    only the public stats (views, likes, comments) from the videos.list
    endpoint which only needs 'youtube.readonly' scope.
    """
    try:
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request as _GRequest

        creds = _get_youtube_credentials()

        # Refresh token if expired
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(_GRequest())
            except Exception as refresh_err:
                log.warning(f"[PerformanceTracker] Token refresh failed: {refresh_err}")

        youtube = build("youtube", "v3", credentials=creds)

        # ── Basic stats (views, likes, comments) ────────────────
        videos_resp = youtube.videos().list(
            part="statistics",
            id=video_id,
        ).execute()

        items = videos_resp.get("items", [])
        if not items:
            log.warning(f"[PerformanceTracker] No video found for id={video_id}")
            return {}

        stats = items[0].get("statistics", {})

        result = {
            "video_id": video_id,
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
            "avg_view_duration_seconds": None,
            "impressions": None,
            "ctr": None,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        # ── Analytics stats (avg duration, impressions, CTR) ────
        # Requires ytAnalytics scope — catch and skip if missing
        try:
            yt_analytics = build("youtubeAnalytics", "v2", credentials=creds)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            analytics_resp = yt_analytics.reports().query(
                ids="channel==MINE",
                startDate="2020-01-01",
                endDate=today,
                metrics="averageViewDuration,impressions,impressionClickThroughRate",
                filters=f"video=={video_id}",
                dimensions="video",
            ).execute()

            rows = analytics_resp.get("rows", [])
            if rows:
                row = rows[0]
                # columns: video, averageViewDuration, impressions, impressionClickThroughRate
                result["avg_view_duration_seconds"] = int(float(row[1])) if len(row) > 1 else None
                result["impressions"] = int(float(row[2])) if len(row) > 2 else None
                result["ctr"] = round(float(row[3]), 4) if len(row) > 3 else None

        except Exception as analytics_err:
            log.warning(
                f"[PerformanceTracker] Analytics scope not available for {video_id} "
                f"(continuing with basic stats only): {analytics_err}"
            )

        log.info(
            f"[PerformanceTracker] Fetched stats for {video_id}: "
            f"views={result['views']} likes={result['likes']} ctr={result['ctr']}"
        )
        return result

    except ImportError:
        log.error("[PerformanceTracker] Install: pip install google-api-python-client google-auth")
        return {}
    except FileNotFoundError as e:
        log.warning(f"[PerformanceTracker] No YouTube credentials: {e}")
        return {}
    except Exception as e:
        log.error(f"[PerformanceTracker] fetch_video_stats({video_id}) failed: {e}")
        return {}


def update_episode_performance(episode_id: str, video_id: str) -> bool:
    """
    Fetch YouTube stats for video_id and write them back to the
    aisha_episodes row identified by episode_id.

    Columns written: views, likes, comments, avg_view_duration_seconds,
                     impressions, ctr, performance_updated_at

    If the columns don't exist yet in the table the PATCH will simply fail
    gracefully (Supabase returns 400) — we log and continue.
    """
    stats = fetch_video_stats(video_id)
    if not stats:
        log.warning(f"[PerformanceTracker] No stats returned for video_id={video_id}")
        return False

    payload = {
        "views": stats.get("views"),
        "likes": stats.get("likes"),
        "comments": stats.get("comments"),
        "avg_view_duration_seconds": stats.get("avg_view_duration_seconds"),
        "impressions": stats.get("impressions"),
        "ctr": stats.get("ctr"),
        "performance_updated_at": stats.get("fetched_at"),
    }
    # Strip None values so we don't overwrite existing data with nulls
    payload = {k: v for k, v in payload.items() if v is not None}

    try:
        _sb_rest(
            f"/aisha_episodes?id=eq.{episode_id}",
            method="PATCH",
            payload=payload,
        )
        log.info(f"[PerformanceTracker] Updated episode {episode_id} with stats")
        return True
    except Exception as e:
        log.error(f"[PerformanceTracker] update_episode_performance({episode_id}) failed: {e}")
        return False


def get_top_performing_topics(channel: str, limit: int = 5) -> list:
    """
    Query aisha_episodes for the highest-view videos on a given channel.
    Returns a list of topic strings (title field), ordered by views desc.

    Joins via aisha_series to filter by channel.
    Falls back to an empty list if DB is unavailable.
    """
    try:
        from supabase import create_client
        sb = create_client(
            os.getenv("SUPABASE_URL", ""),
            os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        )

        # Get all series IDs for the given channel
        series_resp = sb.table("aisha_series").select("id").eq("channel", channel).execute()
        if not series_resp.data:
            return []

        series_ids = [row["id"] for row in series_resp.data]

        # Fetch episodes with views, ordered by views desc
        ep_resp = (
            sb.table("aisha_episodes")
            .select("title,views")
            .in_("series_id", series_ids)
            .not_.is_("views", "null")
            .order("views", desc=True)
            .limit(limit)
            .execute()
        )

        topics = [row["title"] for row in (ep_resp.data or []) if row.get("title")]
        return topics

    except Exception as e:
        log.error(f"[PerformanceTracker] get_top_performing_topics({channel}) failed: {e}")
        return []


def generate_performance_report() -> str:
    """
    Generate a Telegram-friendly performance summary.

    Shows the top 3 videos per channel by views across all 4 Aisha channels.
    Designed to be sent by the weekly scheduler as a digest.
    """
    channels = [
        "Story With Aisha",
        "Riya's Dark Whisper",
        "Riya's Dark Romance Library",
        "Aisha & Him",
    ]

    lines = ["📊 *Weekly Performance Report*\n"]

    try:
        from supabase import create_client
        sb = create_client(
            os.getenv("SUPABASE_URL", ""),
            os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        )

        for channel in channels:
            lines.append(f"*{channel}*")

            series_resp = sb.table("aisha_series").select("id").eq("channel", channel).execute()
            if not series_resp.data:
                lines.append("  No episodes yet.\n")
                continue

            series_ids = [row["id"] for row in series_resp.data]

            ep_resp = (
                sb.table("aisha_episodes")
                .select("title,views,likes,youtube_url")
                .in_("series_id", series_ids)
                .not_.is_("views", "null")
                .order("views", desc=True)
                .limit(3)
                .execute()
            )

            if not ep_resp.data:
                lines.append("  No performance data yet.\n")
                continue

            for i, ep in enumerate(ep_resp.data, 1):
                title = ep.get("title", "Untitled")[:50]
                views = ep.get("views", 0)
                likes = ep.get("likes", 0)
                url = ep.get("youtube_url", "")
                url_part = f" — {url}" if url else ""
                lines.append(f"  {i}. {title}")
                lines.append(f"     👁 {views:,} views · ❤️ {likes:,} likes{url_part}")

            lines.append("")

    except Exception as e:
        log.error(f"[PerformanceTracker] generate_performance_report failed: {e}")
        lines.append(f"Error generating report: {e}")

    # Timestamp
    lines.append(f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Weekly batch runner — called by autonomous_loop.py every Sunday at 06:00 IST
# ---------------------------------------------------------------------------

def run_weekly_performance_sync() -> int:
    """
    Iterate over all aisha_episodes that have a youtube_video_id and
    refresh their performance stats.

    Returns the number of episodes successfully updated.
    """
    updated = 0
    try:
        from supabase import create_client
        sb = create_client(
            os.getenv("SUPABASE_URL", ""),
            os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        )

        # Fetch all episodes that have been uploaded to YouTube
        ep_resp = (
            sb.table("aisha_episodes")
            .select("id,youtube_video_id,title")
            .not_.is_("youtube_video_id", "null")
            .execute()
        )

        episodes = ep_resp.data or []
        log.info(f"[PerformanceTracker] Weekly sync: {len(episodes)} episodes to refresh")

        for ep in episodes:
            ep_id = ep.get("id")
            video_id = ep.get("youtube_video_id")
            if not ep_id or not video_id:
                continue
            success = update_episode_performance(ep_id, video_id)
            if success:
                updated += 1

        log.info(f"[PerformanceTracker] Weekly sync complete: {updated}/{len(episodes)} updated")
    except Exception as e:
        log.error(f"[PerformanceTracker] run_weekly_performance_sync failed: {e}")

    return updated
