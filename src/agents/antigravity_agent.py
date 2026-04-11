"""
antigravity_agent.py
====================
Queue-driven content ops worker — Aisha's autonomous publishing engine.

Flow:
1) Pull queued job from content_jobs
2) Generate content package via YouTubeCrew (script + voice + video)
3) Upload video to Supabase Storage to get a public URL
4) Post to YouTube as Short and Instagram as Reel
5) Persist outputs + performance seeds back to Supabase
6) Notify Ajay on Telegram with results
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
from src.core.config import SUPABASE_URL, SUPABASE_SERVICE_KEY, PRIMARY_YOUTUBE_CHANNEL
import src.core.system_logger as syslog

log = logging.getLogger("Aisha.Antigravity")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AntigravityAgent:
    """Queue processor that turns content jobs into published YouTube Shorts + Instagram Reels."""

    def __init__(self, supabase: Optional[Client] = None):
        self.db = supabase or create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        self.crew = YouTubeCrew()
        self.social = SocialMediaEngine()

    def enqueue_job(
        self,
        topic: str,
        channel: str = None,
        fmt: str = "Short/Reel",
        platform_targets: Optional[List[str]] = None,
        auto_post: bool = True,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Insert a new content job into Supabase queue."""
        record = {
            "topic": topic,
            "channel": channel or PRIMARY_YOUTUBE_CHANNEL,
            "format": fmt,
            "platform_targets": platform_targets or ["youtube", "instagram"],
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

    def _upload_to_storage(self, local_path: str, job_id: str, prefix: str = "videos") -> Optional[str]:
        """Upload a local file to Supabase Storage and return the public URL."""
        if not local_path or not os.path.exists(local_path):
            return None
        try:
            import mimetypes
            mime = mimetypes.guess_type(local_path)[0] or "application/octet-stream"
            storage_path = f"{prefix}/{job_id}_{os.path.basename(local_path)}"
            with open(local_path, "rb") as f:
                self.db.storage.from_("content-videos").upload(
                    storage_path, f.read(),
                    file_options={"content-type": mime, "upsert": "true"}
                )
            public_url = (
                f"{os.getenv('SUPABASE_URL', '').rstrip('/')}"
                f"/storage/v1/object/public/content-videos/{storage_path}"
            )
            log.info(f"[Storage] Uploaded {prefix}/{os.path.basename(local_path)}")
            return public_url
        except Exception as e:
            log.error(f"[Storage] Upload failed for {local_path}: {e}")
            return None

    def _notify_ajay(self, message: str):
        """Send a Telegram notification to Ajay."""
        try:
            import telebot
            bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
            ajay_id = os.getenv("AJAY_TELEGRAM_ID")
            if bot_token and ajay_id:
                bot = telebot.TeleBot(bot_token)
                bot.send_message(ajay_id, message)
        except Exception as e:
            log.warning(f"[Telegram] Notification failed: {e}")

    def _extract_marketing_fields(self, marketing_text: str) -> Dict[str, Any]:
        """Extract structured marketing fields from crew output."""
        data = {"title": "New Story", "description": "", "caption": "", "hashtags": []}
        if not marketing_text:
            return data

        lines = [ln.strip() for ln in marketing_text.splitlines() if ln.strip()]

        for line in lines:
            upper = line.upper()
            if upper.startswith("TITLE:"):
                data["title"] = line.split(":", 1)[1].strip()[:100]
            elif upper.startswith("DESCRIPTION:"):
                data["description"] = line.split(":", 1)[1].strip()[:2000]
            elif upper.startswith("CAPTION:"):
                data["caption"] = line.split(":", 1)[1].strip()[:220]
            elif upper.startswith("HASHTAGS:"):
                raw = line.split(":", 1)[1].strip()
                data["hashtags"] = [t.strip("#,.;:!? ").lower() for t in raw.split() if "#" in t or len(t) > 2][:30]

        if not data["title"] and lines:
            data["title"] = lines[0][:100]

        joined = "\n".join(lines)
        if not data["description"]:
            data["description"] = joined[:2000]
        if not data["caption"]:
            data["caption"] = joined[:220]

        tags: List[str] = []
        for ln in lines:
            if "#" in ln:
                tags.extend([tok.strip("#,.;:!? ").lower() for tok in ln.split() if tok.startswith("#")])
        if not data["hashtags"]:
            data["hashtags"] = [t for t in tags if t][:30]

        return data

    def process_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        job_id = job["id"]
        topic = job["topic"]
        channel = job.get("channel", PRIMARY_YOUTUBE_CHANNEL)
        fmt = job.get("format", "Short/Reel")
        platform_targets = job.get("platform_targets") or ["youtube", "instagram"]
        auto_post = bool(job.get("auto_post", True))
        payload = job.get("payload") or {}

        self._set_status(job_id, "processing", started_at=_utc_now(), error_text=None)
        log.info(f"[Antigravity] Processing job {job_id} | {channel} | {topic}")
        syslog.info("antigravity_agent", "job_start", details={"job_id": job_id, "channel": channel, "topic": topic})

        try:
            crew_output = self.crew.kickoff(
                {
                    "topic": topic,
                    "channel": channel,
                    "format": fmt,
                    "master_prompt": payload.get("master_prompt", ""),
                    "render_video": payload.get("render_video", True),
                }
            )

            script_content = self.crew.results.get("script", "") if hasattr(self.crew, "results") else ""
            if not script_content or len(script_content.strip()) < 50:
                raise ValueError(f"Crew returned empty/stub script for job {job_id}")

            marketing = self._extract_marketing_fields(self.crew.results.get("marketing", ""))
            video_path = self.crew.results.get("video_path") or payload.get("video_path")
            thumbnail_path = self.crew.results.get("thumbnail_path")

            result = {
                "channel": channel,
                "topic": topic,
                "format": fmt,
                "script": self.crew.results.get("script"),
                "marketing": self.crew.results.get("marketing"),
                "voice_path": self.crew.results.get("voice_path"),
                "thumbnail_path": thumbnail_path,
                "video_path": video_path,
            }

            post_results: Dict[str, Any] = {}

            # Upload video to Supabase Storage for public URL (needed for Instagram Reels)
            video_url = None
            if video_path and os.path.exists(video_path):
                video_url = self._upload_to_storage(video_path, job_id, "videos")
                result["video_url"] = video_url

            # Upload thumbnail for public URL
            thumbnail_url = None
            if thumbnail_path and os.path.exists(thumbnail_path):
                thumbnail_url = self._upload_to_storage(thumbnail_path, job_id, "thumbnails")
                result["thumbnail_url"] = thumbnail_url

            if auto_post:
                title = payload.get("title", marketing["title"])
                description = payload.get("description", marketing["description"])
                tags = payload.get("tags", marketing["hashtags"])

                # YouTube Short — upload the video directly
                if "youtube" in platform_targets and video_path and os.path.exists(video_path):
                    if "#shorts" not in title.lower() and "#shorts" not in description.lower():
                        title = title.rstrip() + " #shorts"
                        description += "\n\n#shorts"

                    yt = self.social.upload_youtube_video(
                        video_path=video_path,
                        title=title,
                        description=description,
                        tags=tags,
                        channel_name=channel,
                        privacy=payload.get("privacy", "public"),
                    )
                    post_results["youtube"] = yt
                    if yt.get("success"):
                        log.info(f"[YouTube] Uploaded: {yt.get('url')}")
                        try:
                            self.db.table("content_performance").insert({
                                "content_job_id": job_id,
                                "platform": "youtube",
                                "external_post_id": yt.get("video_id"),
                                "external_url": yt.get("url"),
                                "metrics": {},
                            }).execute()
                        except Exception as e:
                            log.warning(f"[DB] Performance tracking failed: {e}")
                    else:
                        log.error(f"[YouTube] Upload failed: {yt.get('error')}")

                # Instagram Reel — needs a public video URL
                if "instagram" in platform_targets:
                    caption = payload.get("caption", marketing.get("caption", ""))
                    if video_url:
                        ig = self.social.post_instagram_reel(
                            video_url=video_url,
                            caption=caption,
                            hashtags=tags,
                            channel=channel,
                        )
                        post_results["instagram"] = ig
                        if ig.get("success"):
                            log.info(f"[Instagram] Reel posted: {ig.get('post_id')}")
                        else:
                            log.error(f"[Instagram] Reel failed: {ig.get('error')}")
                    elif thumbnail_url:
                        ig = self.social.post_instagram_image(
                            image_url=thumbnail_url,
                            caption=caption,
                            hashtags=tags,
                            channel=channel,
                        )
                        post_results["instagram"] = ig
                        if ig.get("success"):
                            log.info(f"[Instagram] Image posted: {ig.get('post_id')}")
                        else:
                            log.error(f"[Instagram] Image failed: {ig.get('error')}")
                    else:
                        log.warning("[Instagram] No video URL or thumbnail available for posting")
                        post_results["instagram"] = {"success": False, "error": "No publishable asset"}

            result["post_results"] = post_results
            self._set_status(job_id, "completed", completed_at=_utc_now(), output=result)
            syslog.info("antigravity_agent", "job_complete", details={
                "job_id": job_id, "channel": channel, "topic": topic,
                "platforms": list(post_results.keys()),
                "youtube_ok": post_results.get("youtube", {}).get("success", False),
                "instagram_ok": post_results.get("instagram", {}).get("success", False),
            })

            # Notify Ajay with results
            yt_status = "Uploaded" if post_results.get("youtube", {}).get("success") else "Failed"
            ig_status = "Posted" if post_results.get("instagram", {}).get("success") else "Failed"
            yt_url = post_results.get("youtube", {}).get("url", "")
            self._notify_ajay(
                f"Content published!\n\n"
                f"Topic: {topic}\n"
                f"YouTube: {yt_status} {yt_url}\n"
                f"Instagram: {ig_status}\n"
            )

            return result

        except Exception as e:
            err_text = f"{type(e).__name__}: {e}"
            log.exception(f"[Antigravity] Job failed {job_id}")

            retry_count = int(job.get("retry_count") or 0) + 1
            RETRY_DELAYS = {1: 5, 2: 15, 3: 60}

            if retry_count <= 3:
                delay_minutes = RETRY_DELAYS.get(retry_count, 60)
                from datetime import timedelta
                next_run = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
                next_run_iso = next_run.isoformat()
                log.warning(
                    f"[Antigravity] Job {job_id} failed (attempt {retry_count}/3). "
                    f"Retrying in {delay_minutes} min. Error: {err_text}"
                )
                self.db.table("content_jobs").update({
                    "status": "queued",
                    "retry_count": retry_count,
                    "scheduled_at": next_run_iso,
                    "error_text": err_text,
                }).eq("id", job_id).execute()
                syslog.warning("antigravity_agent", "job_retrying", details={
                    "job_id": job_id, "attempt": retry_count, "error": err_text,
                })
                return {"status": "retrying", "retry_count": retry_count, "error": err_text}
            else:
                log.error(f"[Antigravity] Job {job_id} permanently failed after {retry_count - 1} retries")
                self._set_status(job_id, "failed", completed_at=_utc_now(), error_text=err_text)
                self._notify_ajay(f"Content job failed!\nTopic: {topic}\nError: {err_text[:200]}")
                syslog.error("antigravity_agent", "job_failed", details={
                    "job_id": job_id, "retries": retry_count - 1, "error": err_text,
                })
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
