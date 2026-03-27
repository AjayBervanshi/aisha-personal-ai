"""
antigravity_agent.py
====================
Queue-driven content ops worker.
Flow:
1) Pull queued job from content_jobs
2) Generate content package via YouTubeCrew
3) Auto-post to configured platforms (one-account-first defaults)
4) Persist outputs + performance seeds back to Supabase
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from supabase import create_client, Client

from src.agents.youtube_crew import YouTubeCrew
from src.core.social_media_engine import SocialMediaEngine
from src.core.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
import src.core.system_logger as syslog

log = logging.getLogger("Aisha.Antigravity")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AntigravityAgent:
    """Queue processor that turns content jobs into publishable outputs."""

    def __init__(self, supabase: Optional[Client] = None):
        self.db = supabase or create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        self.crew = YouTubeCrew()
        self.social = SocialMediaEngine()

    def enqueue_job(
        self,
        topic: str,
        channel: str = "Story With Aisha",
        fmt: str = "Short/Reel",
        platform_targets: Optional[List[str]] = None,
        auto_post: bool = True,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Insert a new content job into Supabase queue."""
        record = {
            "topic": topic,
            "channel": channel,
            "format": fmt,
            "platform_targets": platform_targets or ["instagram"],
            "auto_post": auto_post,
            "payload": payload or {},
            "status": "queued",
        }
        return self.db.table("content_jobs").insert(record).execute().data[0]

    def fetch_next_job(self) -> Optional[Dict[str, Any]]:
        """Fetch the next due queued job by priority + schedule time."""
        res = (
            self.db.table("content_jobs")
            .select("*")
            .eq("status", "queued")
            .lte("scheduled_at", _utc_now())
            .order("priority", desc=False)
            .order("scheduled_at", desc=False)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    def _set_status(self, job_id: str, status: str, **extra):
        payload = {"status": status, **extra}
        self.db.table("content_jobs").update(payload).eq("id", job_id).execute()

    def _extract_marketing_fields(self, marketing_text: str) -> Dict[str, Any]:
        """
        Best-effort parser for Cappy output.
        Keeps system robust even if LLM output format varies.
        """
        data = {
            "title": "New Story",
            "description": "",
            "caption": "",
            "hashtags": [],
        }
        if not marketing_text:
            return data

        lines = [ln.strip() for ln in marketing_text.splitlines() if ln.strip()]
        if lines:
            data["title"] = lines[0][:100]

        joined = "\n".join(lines)
        data["description"] = joined[:2000]
        data["caption"] = joined[:220]

        tags: List[str] = []
        for ln in lines:
            if "#" in ln:
                tags.extend([tok.strip("#,.;:!? ").lower() for tok in ln.split() if tok.startswith("#")])
        data["hashtags"] = [t for t in tags if t][:30]
        return data

    def process_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        job_id = job["id"]
        topic = job["topic"]
        channel = job.get("channel", "Story With Aisha")
        fmt = job.get("format", "Short/Reel")
        platform_targets = job.get("platform_targets") or ["instagram"]
        auto_post = bool(job.get("auto_post", True))
        payload = job.get("payload") or {}

        self._set_status(job_id, "processing", started_at=_utc_now(), error_text=None)
        log.info(f"[Antigravity] Processing job {job_id} | {channel} | {topic}")
        syslog.info("antigravity_agent", "job_start", details={"job_id": job_id, "channel": channel, "topic": topic, "format": fmt})

        try:
            crew_output = self.crew.kickoff(
                {
                    "topic": topic,
                    "channel": channel,
                    "format": fmt,
                    "master_prompt": payload.get("master_prompt", ""),
                    "render_video": payload.get("render_video", False),
                }
            )

            marketing = self._extract_marketing_fields(self.crew.results.get("marketing", ""))
            video_path = self.crew.results.get("video_path") or payload.get("video_path")
            result = {
                "channel": channel,
                "topic": topic,
                "format": fmt,
                "final_text_bundle": crew_output,
                "script": self.crew.results.get("script"),
                "visuals": self.crew.results.get("visuals"),
                "marketing": self.crew.results.get("marketing"),
                "voice_path": self.crew.results.get("voice_path"),
                "thumbnail_path": self.crew.results.get("thumbnail_path"),
                "video_path": video_path,
            }

            post_results: Dict[str, Any] = {}

            # Upload thumbnail to Supabase Storage → get public URL for Instagram
            thumbnail_url = payload.get("thumbnail_url")
            thumbnail_path = result.get("thumbnail_path")
            if not thumbnail_url and thumbnail_path and os.path.exists(thumbnail_path):
                try:
                    import mimetypes
                    mime = mimetypes.guess_type(thumbnail_path)[0] or "image/png"
                    storage_path = f"thumbnails/{job_id}_{os.path.basename(thumbnail_path)}"
                    with open(thumbnail_path, "rb") as f:
                        self.db.storage.from_("content-media").upload(
                            storage_path, f.read(),
                            file_options={"content-type": mime, "upsert": "true"}
                        )
                    public_url = (
                        f"{os.getenv('SUPABASE_URL', '').rstrip('/')}"
                        f"/storage/v1/object/public/content-media/{storage_path}"
                    )
                    thumbnail_url = public_url
                    result["thumbnail_url"] = public_url
                    log.info(f"[Antigravity] Thumbnail uploaded to Supabase Storage: {public_url}")
                except Exception as e:
                    log.error(f"[Antigravity] Thumbnail upload to Storage failed: {e}")

            if auto_post:
                if "youtube" in platform_targets and video_path:
                    yt = self.social.upload_youtube_video(
                        video_path=video_path,
                        title=payload.get("title", marketing["title"]),
                        description=payload.get("description", marketing["description"]),
                        tags=payload.get("tags", marketing["hashtags"]),
                        channel_name=channel,
                        privacy=payload.get("privacy", "public"),
                    )
                    post_results["youtube"] = yt
                    if yt.get("success"):
                        self.db.table("content_performance").insert(
                            {
                                "content_job_id": job_id,
                                "platform": "youtube",
                                "external_post_id": yt.get("video_id"),
                                "external_url": yt.get("url"),
                                "metrics": {},
                            }
                        ).execute()

                # Instagram: uses public Supabase Storage URL
                if "instagram" in platform_targets and thumbnail_url:
                    ig = self.social.post_instagram_image(
                        image_url=thumbnail_url,
                        caption=payload.get("caption", marketing["caption"]),
                        hashtags=payload.get("tags", marketing["hashtags"]),
                        channel=channel,
                    )
                    post_results["instagram"] = ig
                    if ig.get("success"):
                        self.db.table("content_performance").insert(
                            {
                                "content_job_id": job_id,
                                "platform": "instagram",
                                "external_post_id": ig.get("post_id"),
                                "metrics": {},
                            }
                        ).execute()

            result["post_results"] = post_results
            self._set_status(job_id, "completed", completed_at=_utc_now(), output=result)
            syslog.info("antigravity_agent", "job_complete", details={"job_id": job_id, "channel": channel, "topic": topic, "platforms": list(post_results.keys())})
            return result

        except Exception as e:
            err_text = f"{type(e).__name__}: {e}"
            log.exception(f"[Antigravity] Job failed {job_id}")

            # ── Retry logic: up to 3 attempts with exponential back-off ──────
            retry_count = int(job.get("retry_count") or 0) + 1
            RETRY_DELAYS = {1: 5, 2: 15, 3: 60}  # minutes per attempt

            if retry_count <= 3:
                delay_minutes = RETRY_DELAYS.get(retry_count, 60)
                # Compute next scheduled_at using a raw ISO timestamp offset
                from datetime import timedelta
                next_run = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
                next_run_iso = next_run.isoformat()
                log.warning(
                    f"[Antigravity] Job {job_id} failed (attempt {retry_count}/3). "
                    f"Retrying in {delay_minutes} min at {next_run_iso}. Error: {err_text}"
                )
                self.db.table("content_jobs").update({
                    "status": "queued",
                    "retry_count": retry_count,
                    "scheduled_at": next_run_iso,
                    "error_text": err_text,
                }).eq("id", job_id).execute()
                syslog.warning("antigravity_agent", "job_retrying", details={"job_id": job_id, "attempt": retry_count, "next_run": next_run_iso, "error": err_text})
                return {"status": "retrying", "retry_count": retry_count, "next_run": next_run_iso, "error": err_text}
            else:
                log.error(
                    f"[Antigravity] Job {job_id} permanently failed after {retry_count - 1} retries. Error: {err_text}"
                )
                self._set_status(job_id, "failed", completed_at=_utc_now(), error_text=err_text)
                syslog.error("antigravity_agent", "job_failed", details={"job_id": job_id, "retries": retry_count - 1, "error": err_text})
                return {"status": "failed", "error": err_text}

    def run_once(self) -> Dict[str, Any]:
        job = self.fetch_next_job()
        if not job:
            return {"status": "idle", "message": "No queued job"}
        return {"status": "processed", "result": self.process_job(job)}

    def run_forever(self, poll_seconds: int = 30):
        log.info(f"[Antigravity] Queue worker started. poll={poll_seconds}s")
        while True:
            out = self.run_once()
            if out.get("status") == "idle":
                time.sleep(poll_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = AntigravityAgent()
    mode = os.getenv("ANTIGRAVITY_MODE", "once").lower()
    if mode == "forever":
        agent.run_forever(int(os.getenv("ANTIGRAVITY_POLL_SECONDS", "30")))
    else:
        print(json.dumps(agent.run_once(), ensure_ascii=False))
