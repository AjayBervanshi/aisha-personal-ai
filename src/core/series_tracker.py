"""
series_tracker.py
=================
Tracks episodic YouTube Shorts series.
Provides continuity context for Episode N from Episodes 1..N-1.
"""
import os
import logging
from typing import Optional

log = logging.getLogger("Aisha.SeriesTracker")


def _sb():
    from supabase import create_client
    return create_client(
        os.getenv("SUPABASE_URL", ""),
        os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
    )


def get_or_create_series(series_name: str, channel: str, total_episodes: int = 5) -> dict:
    """Get existing active series or create a new one."""
    try:
        sb = _sb()
        existing = sb.table("aisha_series")\
            .select("*")\
            .eq("series_name", series_name)\
            .eq("channel", channel)\
            .eq("is_active", True)\
            .limit(1).execute()
        if existing.data:
            return existing.data[0]
        result = sb.table("aisha_series").insert({
            "series_name": series_name,
            "channel": channel,
            "total_episodes": total_episodes,
            "current_episode": 0,
        }).execute()
        return result.data[0] if result.data else {}
    except Exception as e:
        log.error(f"[SeriesTracker] get_or_create_series error: {e}")
        return {}


def get_continuity_context(series_id: str) -> str:
    """
    Returns a context string summarizing all previous episodes.
    Used to inject into the script prompt so Episode N continues from N-1.
    """
    try:
        sb = _sb()
        eps = sb.table("aisha_episodes")\
            .select("episode_number,title,script_summary,cliffhanger")\
            .eq("series_id", series_id)\
            .order("episode_number").execute()
        if not eps.data:
            return ""
        lines = ["PREVIOUS EPISODES (for continuity):"]
        for ep in eps.data:
            lines.append(
                f"Episode {ep['episode_number']}: {ep.get('title', '?')} | "
                f"Summary: {ep.get('script_summary', '')[:150]} | "
                f"Cliffhanger: {ep.get('cliffhanger', '')[:100]}"
            )
        return "\n".join(lines)
    except Exception as e:
        log.error(f"[SeriesTracker] get_continuity_context error: {e}")
        return ""


def save_episode(series_id: str, episode_number: int, title: str,
                 script: str, cliffhanger: str, youtube_url: str = None,
                 instagram_post_id: str = None, content_job_id: str = None) -> bool:
    """Save completed episode metadata."""
    try:
        sb = _sb()
        summary = script[:800].rsplit(" ", 1)[0] + "..." if len(script) > 800 else script
        sb.table("aisha_episodes").insert({
            "series_id": series_id,
            "episode_number": episode_number,
            "title": title,
            "script_summary": summary,
            "cliffhanger": cliffhanger,
            "youtube_url": youtube_url,
            "instagram_post_id": instagram_post_id,
            "content_job_id": content_job_id,
        }).execute()
        # Increment current_episode counter on series
        from datetime import datetime, timezone
        sb.table("aisha_series").update({
            "current_episode": episode_number,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", series_id).execute()
        return True
    except Exception as e:
        log.error(f"[SeriesTracker] save_episode error: {e}")
        return False


def advance_or_close_series(series_id: str, episode_number: int, total_episodes: int) -> str:
    """
    After saving an episode, check if series is complete.
    Returns 'ongoing' or 'completed'.
    """
    if episode_number >= total_episodes:
        try:
            _sb().table("aisha_series").update({"is_active": False})\
                .eq("id", series_id).execute()
        except Exception as e:
            log.error(f"[SeriesTracker] advance_or_close error: {e}")
        return "completed"
    return "ongoing"


def get_next_episode_number(series_id: str) -> int:
    """Returns the next episode number to produce."""
    try:
        sb = _sb()
        row = sb.table("aisha_series").select("current_episode").eq("id", series_id).single().execute()
        return (row.data.get("current_episode", 0) + 1) if row.data else 1
    except Exception as e:
        log.error(f"[SeriesTracker] get_next_episode_number error: {e}")
        return 1
