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

        try:
            crew_output = self.crew.kickoff(
                {
                    "topic": topic,
                    "channel": channel,
                    "format": fmt,
                    "master_prompt": payload.get("master_prompt", ""),
                }
            )

            marketing = self._extract_marketing_fields(self.crew.results.get("marketing", ""))
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
            }

            post_results: Dict[str, Any] = {}

            if auto_post:
                if "youtube" in platform_targets and payload.get("video_path"):
                    yt = self.social.upload_youtube_video(
                        video_path=payload["video_path"],
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

                # One-account-first image posting path
                if "instagram" in platform_targets and payload.get("thumbnail_url"):
                    ig = self.social.post_instagram_image(
                        image_url=payload["thumbnail_url"],
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
            return result

        except Exception as e:
            err_text = f"{type(e).__name__}: {e}"
            log.exception(f"[Antigravity] Job failed {job_id}")
            self._set_status(job_id, "failed", completed_at=_utc_now(), error_text=err_text)
            return {"error": err_text}

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
