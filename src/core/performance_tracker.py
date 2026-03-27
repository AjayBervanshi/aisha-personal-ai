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
    Two-pass sync:
      1. Update aisha_episodes (existing behaviour — OAuth-based richer stats).
      2. Update content_jobs rows that have youtube_video_id set, using the
         public YouTube Data API v3 key (no OAuth required for public stats).

    Returns the total number of rows successfully updated across both tables.
    """
    updated = _sync_aisha_episodes()
    updated += _sync_content_jobs()
    return updated


def _sync_aisha_episodes() -> int:
    """Sync aisha_episodes (original behaviour). Returns number of rows updated."""
    updated = 0
    try:
        from supabase import create_client
        sb = create_client(
            os.getenv("SUPABASE_URL", ""),
            os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        )

        ep_resp = (
            sb.table("aisha_episodes")
            .select("id,youtube_video_id,title")
            .not_.is_("youtube_video_id", "null")
            .execute()
        )

        episodes = ep_resp.data or []
        log.info(f"[PerformanceTracker] aisha_episodes sync: {len(episodes)} episodes")

        for ep in episodes:
            ep_id = ep.get("id")
            video_id = ep.get("youtube_video_id")
            if not ep_id or not video_id:
                continue
            if update_episode_performance(ep_id, video_id):
                updated += 1

        log.info(f"[PerformanceTracker] aisha_episodes sync done: {updated}/{len(episodes)}")
    except Exception as e:
        log.error(f"[PerformanceTracker] _sync_aisha_episodes failed: {e}")

    return updated


def _fetch_stats_bulk(video_ids: list) -> dict:
    """
    Fetch view / like / comment counts for up to 50 video IDs in one API call.
    Uses the public YouTube Data API v3 key (YOUTUBE_API_KEY env var) — no OAuth.
    Returns {video_id: {"views": int, "likes": int, "comments": int}}.

    Batches into groups of 50 (YouTube API hard limit per request) and retries
    up to 3 times with exponential backoff on rate-limit (429) responses.
    """
    import time as _time

    api_key = os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        log.error("[PerformanceTracker] YOUTUBE_API_KEY not set — cannot fetch bulk stats")
        return {}

    result: dict = {}
    batch_size = 50

    for i in range(0, len(video_ids), batch_size):
        batch = video_ids[i : i + batch_size]
        ids_param = ",".join(batch)

        for attempt in range(3):
            try:
                resp = _req.get(
                    "https://www.googleapis.com/youtube/v3/videos",
                    params={"part": "statistics", "id": ids_param, "key": api_key},
                    timeout=20,
                )

                if resp.status_code == 429:
                    wait = 2 ** attempt * 5
                    log.warning("[YouTube API] Rate-limited (429). Waiting %ss...", wait)
                    _time.sleep(wait)
                    continue

                if resp.status_code != 200:
                    log.error(
                        "[YouTube API] Unexpected %s: %s",
                        resp.status_code,
                        resp.text[:200],
                    )
                    break

                for item in resp.json().get("items", []):
                    vid_id = item.get("id", "")
                    stats = item.get("statistics", {})
                    result[vid_id] = {
                        "views": int(stats.get("viewCount", 0)),
                        "likes": int(stats.get("likeCount", 0)),
                        "comments": int(stats.get("commentCount", 0)),
                    }
                break  # success

            except _req.exceptions.Timeout:
                wait = 2 ** attempt * 3
                log.warning("[YouTube API] Timeout attempt %d, retrying in %ds", attempt + 1, wait)
                _time.sleep(wait)
            except Exception as exc:
                log.error("[YouTube API] Request error: %s", exc)
                break

    return result


def _compute_performance_score(views: int, likes: int, comments: int) -> float:
    """
    Weighted engagement score (capped at 9999.99).
    Formula: (views * 1 + likes * 50 + comments * 30) / 1000
    Likes and comments carry higher weight — they signal active engagement.
    """
    raw = views * 1.0 + likes * 50.0 + comments * 30.0
    return min(round(raw / 1_000.0, 2), 9999.99)


def _sync_content_jobs() -> int:
    """
    Fetch YouTube stats for all content_jobs rows that have youtube_video_id set
    and write yt_views, yt_likes, yt_comments, performance_score back to DB.

    Uses the public YouTube Data API v3 key (no OAuth needed for public stats).
    Returns the number of rows successfully updated.
    """
    updated = 0
    try:
        from supabase import create_client
        from datetime import datetime, timezone
        sb = create_client(
            os.getenv("SUPABASE_URL", ""),
            os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        )

        rows_resp = (
            sb.table("content_jobs")
            .select("id, youtube_video_id, channel, topic")
            .not_.is_("youtube_video_id", "null")
            .execute()
        )
        rows = rows_resp.data or []

        if not rows:
            log.info("[PerformanceTracker] content_jobs sync: no published videos found")
            return 0

        log.info("[PerformanceTracker] content_jobs sync: %d video(s) to refresh", len(rows))

        video_id_map = {row["youtube_video_id"]: row["id"] for row in rows}
        stats_map = _fetch_stats_bulk(list(video_id_map.keys()))

        if not stats_map:
            log.warning("[PerformanceTracker] No stats returned — quota issue or all IDs invalid?")
            return 0

        for video_id, stats in stats_map.items():
            job_id = video_id_map.get(video_id)
            if not job_id:
                continue

            views = stats["views"]
            likes = stats["likes"]
            comments = stats["comments"]
            score = _compute_performance_score(views, likes, comments)

            try:
                sb.table("content_jobs").update({
                    "yt_views": views,
                    "yt_likes": likes,
                    "yt_comments": comments,
                    "performance_score": score,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", job_id).execute()
                updated += 1
                log.info(
                    "[PerformanceTracker] content_job=%s video=%s views=%d likes=%d score=%.2f",
                    job_id[:8], video_id, views, likes, score,
                )
            except Exception as exc:
                log.error("[PerformanceTracker] Update failed for job %s: %s", job_id[:8], exc)

        log.info(
            "[PerformanceTracker] content_jobs sync done: %d/%d updated", updated, len(rows)
        )
    except Exception as e:
        log.error("[PerformanceTracker] _sync_content_jobs failed: %s", e)

    return updated


def get_performance_insights() -> str:
    """
    Convenience function: sync content_jobs stats then return a human-readable
    performance insight string.

    Aisha calls this to understand what content resonates with the audience
    and to improve future topic selection in studio sessions.

    Returns a multi-line string formatted for Telegram (Markdown).
    """
    log.info("[PerformanceTracker] Running get_performance_insights()...")

    # 1. Sync latest stats
    updated = _sync_content_jobs()

    # 2. Query updated data
    try:
        from supabase import create_client
        from datetime import datetime, timezone
        sb = create_client(
            os.getenv("SUPABASE_URL", ""),
            os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        )

        rows_resp = (
            sb.table("content_jobs")
            .select("id, channel, topic, yt_views, yt_likes, yt_comments, performance_score")
            .not_.is_("youtube_video_id", "null")
            .not_.is_("performance_score", "null")
            .order("performance_score", desc=True)
            .execute()
        )
        rows = rows_resp.data or []
    except Exception as exc:
        log.error("[PerformanceTracker] get_performance_insights DB query failed: %s", exc)
        return "Performance data unavailable — database error."

    if not rows:
        return (
            "No performance data yet.\n"
            "Videos will be tracked after their first YouTube upload."
        )

    # ── Aggregate ────────────────────────────────────────────────────────────
    total_views = sum(r.get("yt_views") or 0 for r in rows)
    avg_views = total_views // len(rows)

    best = rows[0]
    worst = rows[-1]

    # Per-channel average views for recommendation
    channel_stats: dict = {}
    for r in rows:
        ch = r.get("channel") or "Unknown"
        channel_stats.setdefault(ch, []).append(r.get("yt_views") or 0)

    channel_avg = {ch: (sum(v) / len(v)) for ch, v in channel_stats.items() if v}
    best_ch = max(channel_avg, key=channel_avg.get) if channel_avg else None
    worst_ch = min(channel_avg, key=channel_avg.get) if channel_avg else None

    recommendation = ""
    if best_ch and worst_ch and best_ch != worst_ch and channel_avg.get(worst_ch, 0) > 0:
        ratio = channel_avg[best_ch] / channel_avg[worst_ch]
        recommendation = (
            f"Focus on *{best_ch}* — performs {ratio:.1f}x better than *{worst_ch}*"
        )
    elif best_ch:
        recommendation = f"*{best_ch}* is your top-performing channel right now"

    # ── Build report ─────────────────────────────────────────────────────────
    best_topic = (best.get("topic") or "Unknown")[:60]
    best_views = best.get("yt_views") or 0
    best_likes = best.get("yt_likes") or 0

    worst_topic = (worst.get("topic") or "Unknown")[:60]
    worst_views = worst.get("yt_views") or 0

    report_date = datetime.now(timezone.utc).strftime("%d %b %Y")

    lines = [
        f"📊 Content Performance Insights:",
        f"• Best performing topic: \"{best_topic}\" ({best_views:,} views, {best_likes:,} likes)",
        f"• Worst performing: \"{worst_topic}\" ({worst_views:,} views)",
        f"• Average views: {avg_views:,}",
    ]

    if recommendation:
        lines.append(f"• Recommendation: {recommendation}")

    top3 = rows[:3]
    if len(top3) > 1:
        lines.append("\nTop videos:")
        for idx, r in enumerate(top3, 1):
            t = (r.get("topic") or "Unknown")[:50]
            v = r.get("yt_views") or 0
            s = r.get("performance_score") or 0
            lines.append(f"  {idx}. \"{t}\" — {v:,} views (score: {s:.1f})")

    if updated > 0:
        lines.append(f"\n_Synced {updated} video(s) — {report_date}_")
    else:
        lines.append(f"\n_{report_date}_")

    return "\n".join(lines)
