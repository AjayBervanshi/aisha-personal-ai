"""
autonomous_loop.py
==================
The Clona/Molt Autonomous AI background loop.
This script runs continuously 24/7. It allows Aisha to "wake up"
proactively, review her memories, browse for ideas, and text Ajay first.
"""

import time
import json
import schedule
import logging
from datetime import datetime
from pathlib import Path
import pytz

# ── Startup message dedup ─────────────────────────────────────────────────────
_last_startup_msg_time: float = 0.0
_STARTUP_MSG_COOLDOWN: int = 1800  # 30 minutes

# Project root for relative imports and background process launching
PROJECT_ROOT = Path(__file__).parent.parent.parent

from src.core.config import TIMEZONE
from src.core.aisha_brain import AishaBrain
from src.core.logger import get_logger
from src.core.token_manager import run_token_health_check
from src.core.ai_router import _log_to_db
import os
import telebot

log = get_logger("Autonomous")

class AutonomousLoop:
    def __init__(self):
        self.brain = AishaBrain()
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.ajay_id = os.getenv("AJAY_TELEGRAM_ID")
        self.telegram = telebot.TeleBot(bot_token) if bot_token else None
        self._used_topics = []  # Deduplication — never produce the same topic twice

        # New engines
        from src.core.notification_engine import NotificationEngine
        from src.core.digest_engine import DigestEngine
        from src.memory.memory_compressor import MemoryCompressor
        self.notif = NotificationEngine(self.brain, self.brain.memory)
        self.digest = DigestEngine(self.brain.memory, self.brain.ai)
        self.compressor = MemoryCompressor(self.brain.memory)

        self._startup_recovery()
        self._assert_no_telegram_webhook()
        self._db_self_repair()
        log.info("event=autonomous_loop_init")

    def _db_self_repair(self):
        """Auto-create any missing Supabase tables on startup."""
        try:
            from src.core.self_db import check_and_repair
            results = check_and_repair()
            created = [t for t, s in results.items() if s == "created"]
            failed  = [f"{t}: {s}" for t, s in results.items() if s.startswith("failed")]
            if created:
                log.info(f"event=db_self_repair created={created}")
            if failed:
                log.warning(f"event=db_self_repair failed={failed}")
        except Exception as e:
            log.warning(f"event=db_self_repair err={e}")

    def _startup_recovery(self):
        """Reset content_jobs jobs stuck in 'processing' for >30 min back to 'queued'."""
        try:
            import os as _os
            from supabase import create_client
            sb = create_client(
                _os.getenv("SUPABASE_URL", ""),
                _os.getenv("SUPABASE_SERVICE_KEY") or _os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
            )
            from datetime import datetime, timezone, timedelta
            cutoff = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
            stuck = sb.table("content_jobs").select("id").eq("status", "processing").lt("updated_at", cutoff).execute()
            if stuck.data:
                ids = [row["id"] for row in stuck.data]
                # Chunk into batches of 100 to avoid PostgREST URL length limits
                chunk_size = 100
                for i in range(0, len(ids), chunk_size):
                    chunk = ids[i:i + chunk_size]
                    sb.table("content_jobs").update({"status": "queued"}).in_("id", chunk).execute()
                log.info(f"event=startup_recovery reset={len(stuck.data)}_stuck_jobs")
        except Exception as e:
            log.warning(f"event=startup_recovery_failed err={e}")

    # Class-level flag — only send the webhook warning ONCE across all restarts
    # (Render may restart the process multiple times in quick succession)
    _webhook_warned: bool = False

    def _assert_no_telegram_webhook(self):
        """Auto-delete any stale Telegram webhook on startup when running in polling mode.
        Only runs once per process lifetime.
        SKIPPED when running on Render — Render uses the webhook, not polling."""
        if AutonomousLoop._webhook_warned:
            return
        AutonomousLoop._webhook_warned = True
        # On Render, the bot is webhook-mode — never delete the webhook here.
        if os.getenv("RENDER"):
            return
        try:
            bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
            if not bot_token:
                return
            import requests as _req
            resp = _req.get(f"https://api.telegram.org/bot{bot_token}/getWebhookInfo", timeout=5).json()
            webhook_url = resp.get("result", {}).get("url", "")
            if not webhook_url:
                return  # no webhook set — nothing to do
            log.warning(f"event=webhook_stale webhook_url={webhook_url} action=auto_deleting")
            del_resp = _req.post(
                f"https://api.telegram.org/bot{bot_token}/deleteWebhook",
                json={"drop_pending_updates": False},
                timeout=5,
            ).json()
            if del_resp.get("result"):
                log.info("event=webhook_deleted status=ok")
            else:
                log.warning(f"event=webhook_delete_failed resp={del_resp}")
        except Exception as e:
            log.warning(f"event=webhook_check_failed err={e}")

    def run_evening_wrapup(self):
        """Send evening summary at 9 PM IST."""
        log.info("event=evening_wrapup_start")
        _log_to_db("INFO", "autonomous_loop", "job_started: evening_wrapup")
        try:
            self.notif.evening_wrapup()
            _log_to_db("INFO", "autonomous_loop", "job_completed: evening_wrapup")
        except Exception as e:
            log.error("event=evening_wrapup_failed — %s", str(e))
            _log_to_db("ERROR", "autonomous_loop", f"job_failed: evening_wrapup: {e}")

    def run_daily_digest(self):
        """Generate and send daily digest at 9 PM IST."""
        log.info("event=daily_digest_trigger")
        _log_to_db("INFO", "autonomous_loop", "job_started: daily_digest")
        try:
            digest_text = self.digest.generate_daily_digest()
            if self.telegram and self.ajay_id:
                self.telegram.send_message(self.ajay_id, digest_text)
            _log_to_db("INFO", "autonomous_loop", "job_completed: daily_digest")
        except Exception as e:
            log.error("event=daily_digest_send_failed — %s", str(e))
            _log_to_db("ERROR", "autonomous_loop", f"job_failed: daily_digest: {e}")

    def run_weekly_digest(self):
        """Generate and send weekly digest every Sunday."""
        log.info("event=weekly_digest_trigger")
        _log_to_db("INFO", "autonomous_loop", "job_started: weekly_digest")
        try:
            digest_text = self.digest.generate_weekly_digest()
            if self.telegram and self.ajay_id:
                self.telegram.send_message(self.ajay_id, digest_text)
            _log_to_db("INFO", "autonomous_loop", "job_completed: weekly_digest")
        except Exception as e:
            log.error("event=weekly_digest_send_failed — %s", str(e))
            _log_to_db("ERROR", "autonomous_loop", f"job_failed: weekly_digest: {e}")

    def run_task_reminder_poll(self):
        """Poll for tasks due in 30 minutes and send reminders."""
        try:
            self.notif.check_task_reminders()
        except Exception as e:
            log.error("event=task_reminder_poll_failed — %s", str(e))

    def run_inactivity_check(self):
        """Check if Ajay has been silent for 18+ hours."""
        try:
            self.notif.inactivity_check()
        except Exception as e:
            log.error("event=inactivity_check_failed — %s", str(e))

    def run_memory_cleanup(self):
        """Weekly memory deduplication and decay (Sunday 3 AM)."""
        log.info("event=memory_cleanup_trigger")
        _log_to_db("INFO", "autonomous_loop", "job_started: memory_cleanup")
        try:
            stats = self.compressor.run_weekly_cleanup()
            log.info("event=memory_cleanup_done", **stats)
            _log_to_db("INFO", "autonomous_loop", "job_completed: memory_cleanup")
        except Exception as e:
            log.error("event=memory_cleanup_failed — %s", str(e))
            _log_to_db("ERROR", "autonomous_loop", f"job_failed: memory_cleanup: {e}")

    def run_morning_checkin(self):
        """Proactively message Ajay in the morning based on his schedule & memory."""
        # Verify we are actually in morning hours IST before sending greeting
        _ist = pytz.timezone("Asia/Kolkata")
        ist_hour = datetime.now(_ist).hour
        if not (5 <= ist_hour < 12):
            log.warning(f"run_morning_checkin fired outside IST morning hours (hour={ist_hour}) — skipping")
            return
        log.info(f"[{datetime.now(_ist).strftime('%Y-%m-%d %H:%M IST')}] Waking up for Morning Check-in...")
        _log_to_db("INFO", "autonomous_loop", "job_started: morning_checkin")

        # Use brain.think() so full context pipeline runs (memory, mood, tasks, profile)
        prompt = (
            "It is morning. You are waking up Ajay proactively — he has not messaged you yet. "
            "Look at his schedule for today and his recent memories. "
            "Write a warm, energetic, loving morning message. "
            "Be highly contextual — reference his actual tasks, goals, or mood if relevant. "
            "You are starting the conversation, not replying to him."
        )
        morning_text = self.brain.think(prompt, platform="telegram")

        log.info(f"[Aisha] Morning message: {morning_text[:100]}...")

        if self.telegram and self.ajay_id:
            try:
                self.telegram.send_message(self.ajay_id, morning_text)
                log.info("Sent morning check-in to Ajay on Telegram.")
            except Exception as e:
                log.error(f"Failed to send Telegram message: {e}")
        _log_to_db("INFO", "autonomous_loop", "job_completed: morning_checkin")

    def run_memory_consolidation(self):
        """Runs at 3 AM: Analyzes all talks from the day and updates deep profile."""
        log.info(f"[{datetime.now()}] Running deep memory consolidation sleep cycle...")
        _log_to_db("INFO", "autonomous_loop", "job_started: memory_consolidation")
        
        # 1. Pull recent conversations (past 24h)
        chats = self.brain.memory.get_recent_conversation(limit=50)
        if not chats:
            log.info("No conversations to consolidate today.")
            return

        chat_text = "\n".join([f"{c['role']}: {c['message']}" for c in chats])
        
        # 2. Ask Aisha to summarize and extract insights
        prompt = f"""
        You are Aisha. Here are your conversations with Ajay from the last 24 hours:
        {chat_text}

        Your task:
        1. Summarize the key events/facts (Episodic Memory).
        2. Identify any emotional patterns or stresses (Emotional Memory).
        3. Identify any new skills or tasks you learned to do (Skill Memory).

        Return ONLY a valid JSON object (no backticks, no extra text) with keys: 'episodic', 'emotional', 'skills'.
        Each value should be a list of strings.
        """

        try:
            res = self.brain.ai.generate("You are Aisha. Return only valid JSON.", prompt).text
            # Strip any markdown code fences if present
            import re as _re
            res = _re.sub(r'^```(?:json)?\s*', '', res.strip())
            res = _re.sub(r'\s*```$', '', res).strip()
            data = json.loads(res)
            
            # 3. Save to deep memory tables
            for fact in data.get("episodic", []):
                self.brain.memory.save_episodic_memory("Ajay", fact, datetime.now().strftime("%Y-%m-%d"))
            
            for emote in data.get("emotional", []):
                self.brain.memory.save_emotional_memory("detected", "contextual", emote)
                
            for skill in data.get("skills", []):
                self.brain.memory.save_skill_memory(skill, f"Auto-learned during conversation: {skill}")
                
            log.info("✅ Consolidation complete. Memories stored.")
            _log_to_db("INFO", "autonomous_loop", "job_completed: memory_consolidation")

        except Exception as e:
            log.error(f"Consolidation failed: {e}")
            _log_to_db("ERROR", "autonomous_loop", f"job_failed: memory_consolidation: {e}")

    def run_studio_session(self):
        """Aisha autonomously decides which channel needs content and starts the crew.

        Priority order:
        1. Drain oldest queued job from the backlog (if any exist).
        2. Only when the queue is empty, generate a fresh topic and enqueue it.
        This ensures the backlog never grows unboundedly.
        """
        log.info(f"[{datetime.now()}] Aisha entering Studio for proactive session...")
        _log_to_db("INFO", "autonomous_loop", "job_started: studio_session")

        try:
            from src.agents.antigravity_agent import AntigravityAgent
            agent = AntigravityAgent()

            # Step 1: Try to drain an existing queued job first
            existing_job = agent.fetch_next_job()
            if existing_job:
                log.info(
                    f"[Studio] Draining backlog job {existing_job.get('id')} | "
                    f"channel={existing_job.get('channel')} | topic={existing_job.get('topic')}"
                )
                _log_to_db("INFO", "autonomous_loop", "studio_draining_backlog",
                           details={"job_id": existing_job.get("id"), "topic": existing_job.get("topic")})
                import threading as _threading
                _threading.Thread(
                    target=agent.process_job,
                    args=(existing_job,),
                    daemon=True,
                    name=f"drain-job-{existing_job.get('id','?')[:8]}"
                ).start()
                log.info(f"[Studio] Backlog drain thread started for job {existing_job.get('id')}")
                _log_to_db("INFO", "autonomous_loop", "job_completed: studio_session",
                           details={"job_id": existing_job.get("id"), "mode": "backlog_drain"})
                return

            # Step 2: Queue is empty — generate a fresh topic
            import random
            channels = [
                {"name": "Story With Aisha",          "format": "Long Form",   "vibe": "Romantic and Heart-touching"},
                {"name": "Riya's Dark Whisper",        "format": "Long Form",   "vibe": "Seductive and Mysterious"},
                {"name": "Riya's Dark Romance Library","format": "Long Form",   "vibe": "Intense Mafia/Obsessive Romance"},
                {"name": "Aisha & Him",                "format": "Short/Reel",  "vibe": "Relatable Couple Moments/Dialogue"}
            ]
            selected = random.choice(channels)

            for attempt in range(5):
                prompt = (f"You are Aisha, the Creative Director. For channel '{selected['name']}', "
                         f"suggest ONE viral {selected['vibe']} story topic title. "
                         f"Already used: {self._used_topics[-10:] if self._used_topics else 'none'}. "
                         "Return ONLY the topic title, nothing else.")
                topic = self.brain.ai.generate("You are Aisha.", prompt).text.strip()
                if topic not in self._used_topics:
                    self._used_topics.append(topic)
                    # Cap at 200 entries — old topics can be reused after that
                    if len(self._used_topics) > 200:
                        self._used_topics = self._used_topics[-200:]
                    break

            log.info(f"[Studio] Channel: '{selected['name']}' | Topic: '{topic}'")

            # Notify Ajay — apply cooldown to avoid spam on rapid restarts
            global _last_startup_msg_time
            _now = time.time()
            _in_cooldown = (_now - _last_startup_msg_time) < _STARTUP_MSG_COOLDOWN
            if self.telegram and self.ajay_id and not _in_cooldown:
                try:
                    _last_startup_msg_time = _now
                    self.telegram.send_message(
                        self.ajay_id,
                        f"Ajju, I'm starting a new production for '{selected['name']}' right now!\n"
                        f"Topic: '{topic}'\nI'll ping you when the script is ready! Let me cook. 💜"
                    )
                except Exception as e:
                    log.warning(f"[Telegram] Failed to notify: {e}")
            elif _in_cooldown:
                log.info(
                    f"[Studio] Startup notification skipped — sent "
                    f"{int(_now - _last_startup_msg_time)}s ago (cooldown={_STARTUP_MSG_COOLDOWN}s)"
                )

            job = agent.enqueue_job(
                topic=topic,
                channel=selected["name"],
                fmt=selected["format"],
                platform_targets=["youtube", "instagram"],
                auto_post=True,
                payload={"render_video": True},
            )
            log.info(f"[Studio] Enqueued content job: {job.get('id')}")
            import threading as _threading
            _threading.Thread(
                target=agent.process_job,
                args=(job,),
                daemon=True,
                name=f"studio-job-{job.get('id','?')[:8]}"
            ).start()
            log.info(f"[Studio] Processing thread started for job {job.get('id')}")
            _log_to_db("INFO", "autonomous_loop", "job_completed: studio_session",
                       details={"job_id": job.get("id"), "channel": selected["name"], "topic": topic})

        except Exception as e:
            log.error(f"[Studio] Session failed: {e}")
            _log_to_db("ERROR", "autonomous_loop", f"job_failed: studio_session: {e}")
            # Fallback path: launch production script directly (no agent available)
            try:
                import subprocess, random as _rand, sys as _sys
                _ch = _rand.choice(["Story With Aisha", "Aisha & Him"])
                subprocess.Popen([
                    _sys.executable, "-m", "src.agents.run_youtube",
                    "--channel", _ch,
                ], cwd=str(PROJECT_ROOT))
                log.info(f"[Studio] Production crew launched via fallback for: {_ch}")
            except Exception as ex:
                log.error(f"[Studio] Failed to launch production fallback: {ex}")

    def run_temp_cleanup(self):
        """Delete temp voice/video files older than 24 hours to prevent disk exhaustion."""
        import time as _time
        cutoff = _time.time() - 86400  # 24 hours
        deleted = 0
        for folder in ["temp_voice", "temp_videos", "temp_assets"]:
            folder_path = PROJECT_ROOT / folder
            if not folder_path.exists():
                continue
            for f in folder_path.iterdir():
                if f.is_file() and f.stat().st_mtime < cutoff:
                    try:
                        f.unlink()
                        deleted += 1
                    except Exception:
                        pass
        if deleted > 0:
            log.info(f"event=temp_cleanup deleted={deleted}_files")

    def run_key_expiry_check(self):
        """Check API key expiry dates and alert Ajay via Telegram if any expire within 30 days."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        warnings = []

        # NVIDIA keys — all expire 2026-09-17
        nvidia_expiry = datetime(2026, 9, 17, tzinfo=timezone.utc)
        days_left = (nvidia_expiry - now).days
        if days_left <= 30:
            warnings.append(f"⚠️ NVIDIA NIM keys expire in {days_left} days (2026-09-17)! Renew at build.nvidia.com")

        # YouTube OAuth token — check expiry field from DB (fallback to file)
        try:
            yt_data = None
            # Try DB first
            try:
                from src.core.social_media_engine import _load_db_secret
                raw = _load_db_secret("YOUTUBE_OAUTH_TOKEN")
                if raw:
                    yt_data = json.loads(raw)
            except Exception:
                pass
            # File fallback
            if not yt_data:
                yt_path = PROJECT_ROOT / "tokens" / "youtube_token.json"
                if yt_path.exists():
                    yt_data = json.loads(yt_path.read_text())
            if yt_data:
                expiry_str = yt_data.get("expiry", "") or yt_data.get("token_expiry", "")
                if expiry_str:
                    exp = datetime.fromisoformat(str(expiry_str).replace("Z", "+00:00"))
                    d = (exp - now).days
                    if d <= 7:
                        warnings.append(f"⚠️ YouTube OAuth access token expires in {d} days — will auto-refresh on next upload.")
        except Exception:
            pass

        if warnings and self.telegram and self.ajay_id:
            msg = "🔑 Key Expiry Alert:\n\n" + "\n".join(warnings)
            try:
                self.telegram.send_message(self.ajay_id, msg)
            except Exception as e:
                log.warning(f"event=key_expiry_alert_failed err={e}")
        elif not warnings:
            log.info("event=key_expiry_check all_keys_ok")


def run_weekly_analytics_sync(loop: AutonomousLoop):
    """
    Performance feedback loop — runs every Sunday at 06:00 IST.
    1. Syncs YouTube view/like/CTR stats for all published episodes into aisha_episodes.
    2. Sends a formatted performance report to Ajay via Telegram.
    """
    log.info("[PerformanceTracker] Starting weekly analytics sync...")
    try:
        from src.core.performance_tracker import run_weekly_performance_sync, generate_performance_report
        updated = run_weekly_performance_sync()
        log.info(f"[PerformanceTracker] Sync complete: {updated} episodes updated")
        report = generate_performance_report()
        if loop.telegram and loop.ajay_id:
            try:
                loop.telegram.send_message(loop.ajay_id, report, parse_mode="Markdown")
            except Exception as tg_err:
                log.warning(f"[PerformanceTracker] Telegram send failed: {tg_err}")
                try:
                    plain = report.replace("*", "").replace("_", "")
                    loop.telegram.send_message(loop.ajay_id, plain)
                except Exception:
                    pass
    except Exception as e:
        log.error(f"[PerformanceTracker] Weekly analytics sync failed: {e}")


def run_self_improvement(loop: AutonomousLoop):
    """Aisha audits and improves her own code every night."""
    log.info("[SelfEditor] Starting nightly self-improvement session...")
    try:
        from src.core.self_editor import SelfEditor
        editor = SelfEditor()
        editor.run_improvement_session()
    except Exception as e:
        log.error(f"[SelfEditor] Session failed: {e}")


def run_daily_audit_job():
    """Wrapper for the async daily audit — called by the scheduler at 20:30 UTC (2 AM IST)."""
    import asyncio
    log.info("[DailyAudit] Starting daily audit job...")
    try:
        from src.core.daily_audit import run_daily_audit
        asyncio.run(run_daily_audit())
    except Exception as e:
        log.error(f"[DailyAudit] Audit job failed: {e}")

    # ── Self-Repair: integrity scan + auto-restore ─────────────────────────────
    log.info("[SelfRepair] Starting file integrity scan...")
    try:
        from src.core.self_repair import SelfRepairEngine
        repair_engine = SelfRepairEngine()
        repair_summary = repair_engine.run_repair_cycle()
        log.info(f"[SelfRepair] {repair_summary}")
    except Exception as e:
        log.error(f"[SelfRepair] Repair cycle failed: {e}")


def run_scheduled_improvement():
    """Run self-improvement if the last session was more than 6 hours ago."""
    log.info("[SelfEditor] Checking whether scheduled improvement should run...")
    try:
        from src.core.learning_engine import LearningEngine
        le = LearningEngine()
        recent = le.get_recent_improvements(1)
        if recent:
            last_str = recent[0].get("started_at", "")
            if last_str:
                from datetime import datetime, timezone, timedelta
                last_dt = datetime.fromisoformat(last_str.replace("Z", "+00:00"))
                elapsed = datetime.now(timezone.utc) - last_dt
                if elapsed < timedelta(hours=6):
                    log.info(
                        f"[SelfEditor] Skipping — last improvement was only "
                        f"{int(elapsed.total_seconds() / 3600)}h ago."
                    )
                    return
        from src.core.self_editor import SelfEditor
        editor = SelfEditor()
        editor.run_improvement_session()
    except Exception as e:
        log.error(f"[SelfEditor] Scheduled improvement failed: {e}")


def start_loop(once: bool = False):
    """
    Start Aisha's autonomous loop.
    --once: Run one studio session and exit (for manual trigger from Telegram)
    """
    bot = AutonomousLoop()

    if once:
        log.info("[Aisha] Running single studio session (--once mode)...")
        bot.run_studio_session()
        return

    # ── Daily Schedule ──────────────────────────────────────────────────
    schedule.every().day.at("08:00").do(bot.run_morning_checkin)
    schedule.every().day.at("21:00").do(bot.run_evening_wrapup)
    schedule.every().day.at("21:30").do(bot.run_daily_digest)
    schedule.every().day.at("03:00").do(bot.run_memory_consolidation)

    # ── Weekly Schedule ────────────────────────────────────────────────
    schedule.every().sunday.at("19:00").do(bot.run_weekly_digest)
    schedule.every().sunday.at("03:00").do(bot.run_memory_cleanup)
    # Performance feedback loop — sync YouTube stats & send report every Sunday 6 AM IST
    schedule.every().sunday.at("06:00").do(run_weekly_analytics_sync, bot)

    # ── High-frequency Polls ──────────────────────────────────────────
    # Task reminders — check every 5 min
    schedule.every(5).minutes.do(bot.run_task_reminder_poll)
    # Inactivity check — every 3 hours
    schedule.every(3).hours.do(bot.run_inactivity_check)

    # ── Studio Management (Every 4 Hours) ─────────────────────────────
    schedule.every(4).hours.do(bot.run_studio_session)

    # ── Nightly Self-Improvement (2 AM) ───────────────────────────────
    schedule.every().day.at("02:00").do(run_self_improvement, bot)

    # ── Daily Audit (2 AM IST = 20:30 UTC) ────────────────────────────
    schedule.every().day.at("20:30").do(run_daily_audit_job)

    # ── Scheduled Self-Improvement (every 6 hours) ────────────────────
    schedule.every(6).hours.do(run_scheduled_improvement)

    # ── Maintenance Jobs ───────────────────────────────────────────────
    # Temp file cleanup — daily at 4 AM (delete voice/video files >24h old)
    schedule.every().day.at("04:00").do(bot.run_temp_cleanup)
    # API key expiry monitor — daily at 9 AM
    schedule.every().day.at("09:00").do(bot.run_key_expiry_check)
    # Token health check — daily at 6 AM (refresh Instagram/YouTube OAuth before expiry)
    schedule.every().day.at("06:00").do(run_token_health_check)

    # Run the first studio session instantly on startup
    bot.run_studio_session()

    log.info("[Aisha] Autonomous biological clock is ticking. Running 24/7...")

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run one session and exit")
    args = parser.parse_args()
    start_loop(once=args.once)
