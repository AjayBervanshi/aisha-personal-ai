import subprocess
"""
aisha_brain.py
==============
Core AI logic for Aisha — Ajay's Personal AI Soulmate.
Handles: AI calls, language detection, mood detection, memory context building.

Refactored to use:
  - config.py         → all env vars / settings
  - language_detector → proper EN/HI/MR/Hinglish detection
  - mood_detector     → 7-mode adaptive personality
  - memory_manager    → full Supabase CRUD
"""

import json
import logging
import re
import threading
from datetime import datetime
from typing import Optional
from pathlib import Path

log = logging.getLogger(__name__)

# Project root for relative imports and background process launching
PROJECT_ROOT = Path(__file__).parent.parent.parent

from supabase import create_client
from src.core.ai_router import AIRouter

from src.core.config import (
    GEMINI_API_KEY, GROQ_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY,
    GEMINI_MODEL, GROQ_MODEL, AI_TEMPERATURE, AI_MAX_TOKENS, AI_HISTORY_LIMIT, USER_NAME,
    AISHA_SECRET_CODE
)
from src.core.language_detector import detect_language
from src.core.mood_detector import detect_mood
from src.core.prompts.builder import build_system_prompt
from src.memory.memory_manager import MemoryManager


# Logic moved to src.core.prompts.builder and src.core.mood_detector



# ─── Aisha Brain (Main AI Class) ───────────────────────────────────────────────

class AishaBrain:
    def __init__(self):
        self.ai = AIRouter()
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        self.memory   = MemoryManager(self.supabase)

        # Live skill registry — skills Aisha creates persist and are reused
        try:
            from src.skills.skill_registry import SkillRegistry
            self.skills = SkillRegistry()
        except Exception as e:
            log.warning(f"[Brain] SkillRegistry init failed: {e}")
            self.skills = None

        # Per-user conversation histories — keyed by Telegram user_id (int).
        # Owner's history is warm-started from Supabase; guest histories start empty.
        # Format: { user_id: [{"role": ..., "content": ...}, ...] }
        # Capped at MAX_GUEST_SESSIONS entries to prevent unbounded RAM growth.
        self._histories: dict = {}
        self._history_last_used: dict = {}   # uid → timestamp for LRU eviction
        self._MAX_GUEST_SESSIONS = 50        # keep at most 50 guest histories in RAM

        # Optional mood override — set by /mood <name> command, cleared each response
        self.mood_override: str | None = None

        # Pre-warm owner history so the first owner message feels continuous.
        owner_uid = self._get_owner_id()
        if owner_uid is not None:
            self._histories[owner_uid] = self._load_history_from_db(user_id=owner_uid)
        # Also keep a legacy fallback under key 0 for unknown callers.
        self._histories[0] = self._load_history_from_db(user_id=None)

        # Counter for throttling auto-extract (only every 5th message)
        self._message_count = 0

    # ─── Backwards-compat shim ──────────────────────────────────────────────
    @property
    def history(self) -> list:
        """Legacy read accessor — returns owner/default history. Used by reset_session()."""
        return self._histories.get(0, [])

    @history.setter
    def history(self, value: list):
        """Legacy write accessor (used by reset_session)."""
        self._histories[0] = value

    # ─── Internal helpers ────────────────────────────────────────────────────

    def _get_owner_id(self) -> Optional[int]:
        """Return the numeric owner Telegram ID from config, or None if unavailable."""
        try:
            from src.core.config import AUTHORIZED_ID
            return int(AUTHORIZED_ID)
        except (ImportError, AttributeError, ValueError, TypeError):
            return None

    def _load_history_from_db(self, user_id: Optional[int] = None) -> list:
        """Restore recent conversation history from Supabase on startup.

        When user_id is None (or matches the owner), loads the owner's shared
        conversation log for warm-start.  Guest user_ids always start empty
        because their turns are saved with a guest tag and are not loaded back
        into hot memory — we don't want guest context polluting the owner's
        warm-start, and we don't persist guest warm-starts across restarts.
        """
        try:
            owner_uid = self._get_owner_id()
            # Only warm-start for the owner (or legacy fallback when user_id is None)
            if user_id is not None and user_id != owner_uid:
                return []
            recent = self.memory.get_recent_conversation(limit=AI_HISTORY_LIMIT)
            return [{"role": c["role"], "content": c["message"]} for c in recent]
        except Exception as e:
            print(f"[Brain] Could not warm-start history from DB: {e}")
            return []

    def _get_user_history(self, uid: int, is_owner: bool) -> list:
        """Return (and lazily initialise) the history list for *uid*.

        Memory-safe:
        - Guest histories are evicted via LRU once more than _MAX_GUEST_SESSIONS
          accumulate in RAM (prevents unbounded dict growth from new chatters).
        - Each history list is trimmed to 2×AI_HISTORY_LIMIT entries after every
          call so long-running sessions cannot exhaust RAM with huge context.
        """
        import time as _t
        now = _t.time()

        if uid not in self._histories:
            # Evict oldest guest entry if at capacity (never evict owner or key-0 fallback)
            owner_uid = self._get_owner_id()
            if len(self._histories) >= self._MAX_GUEST_SESSIONS:
                guest_keys = [
                    k for k in self._history_last_used
                    if k != owner_uid and k != 0
                ]
                if guest_keys:
                    oldest = min(guest_keys, key=lambda k: self._history_last_used[k])
                    del self._histories[oldest]
                    del self._history_last_used[oldest]

            self._histories[uid] = self._load_history_from_db(user_id=uid if not is_owner else None)

        self._history_last_used[uid] = now

        # Trim to prevent unbounded growth (keep last 2×AI_HISTORY_LIMIT messages)
        hist = self._histories[uid]
        cap = AI_HISTORY_LIMIT * 2
        if len(hist) > cap:
            del hist[:len(hist) - cap]

        return hist

    # ─── NLP Intent Router ───────────────────────────────────────────────────
    # Aisha understands natural language. No slash commands needed.
    # User just talks normally: "ek video bana do", "YouTube pe post karo",
    # "aaj ka digest bhejo", "channel ka status kya hai" — Aisha gets it.

    _INTENT_PATTERNS = [
        # ── CONTENT CREATION (highest priority — revenue generating) ──────
        # Hindi: "ek video banao", "story banao aur post karo", "content create karo"
        # English: "make a video", "create a reel", "produce content for YouTube"
        # Mixed: "YouTube pe ek short daal do", "Instagram reel banao"
        (re.compile(
            r"(make|create|produce|generate|bana[ao]?|bana do|likho|likh do|daal do|dal do|post karo).{0,60}"
            r"(video|content|youtube|short|reel|episode|kahani|story|kahaniya)|"
            r"(video|content|short|reel|story|kahani).{0,40}"
            r"(bana[ao]?|bana do|create|produce|likho|daal|dal|post)|"
            r"(youtube|insta|instagram).{0,30}(pe|par|ke liye|for).{0,30}"
            r"(bana|create|post|upload|daal|dal)|"
            r"(ek|naya|nayi|new|aur ek|one more).{0,30}(video|reel|short|content|episode)|"
            r"start.{0,20}produc|go.{0,10}live|let.{0,5}s.{0,5}cook|"
            r"kuch.{0,20}(bana|post|upload)|shoot.{0,20}(video|content)",
            re.I,
        ), "content_creation"),

        # ── RIYA CONTENT (detect when user specifically wants Riya/adult) ──
        (re.compile(
            r"riya.{0,40}(video|story|kahani|content|bana|likho|post)|"
            r"(dark|bold|adult|18\+|hot|sexy).{0,30}(video|story|kahani|content|bana)|"
            r"(video|story|content).{0,30}(riya|dark whisper|bold|adult)",
            re.I,
        ), "riya_content"),

        # ── CHANNEL STATUS / ANALYTICS ────────────────────────────────────
        # "channel ka status", "how's the channel doing", "views kitne aaye"
        (re.compile(
            r"(channel|youtube|insta).{0,30}(status|stats|analytics|performance|views|subscribers|kaisa|kaise)|"
            r"(views|subscribers|likes|earnings|kamai|paisa).{0,30}(kitne|kitna|how many|check|batao|dikhao)|"
            r"(content|video).{0,20}(performance|stats)|"
            r"kamai.{0,20}(kitni|batao|dikhao|check)|earning",
            re.I,
        ), "channel_status"),

        # ── DAILY DIGEST / REPORT ─────────────────────────────────────────
        # "aaj ka report", "digest bhejo", "summary dikhao", "kya hua aaj"
        (re.compile(
            r"(aaj|today|kal|yesterday).{0,30}(report|summary|digest|recap|kya hua)|"
            r"(digest|report|summary).{0,20}(bhejo|dikhao|send|show|de do)|"
            r"(morning|evening|daily|weekly).{0,20}(report|digest|summary|briefing)|"
            r"kya.{0,10}(hua|chal raha|ho raha).{0,10}(aaj|today)",
            re.I,
        ), "digest"),

        # ── QUEUE / JOB STATUS ────────────────────────────────────────────
        # "queue mein kya hai", "koi video pending hai?", "kitne jobs hain"
        (re.compile(
            r"(queue|pending|jobs?|tasks?).{0,30}(status|kitne|how many|kya hai|check|dikhao)|"
            r"(kitne|how many).{0,20}(video|content|jobs?|tasks?).{0,20}(pending|queue|left)|"
            r"kya.{0,15}(pending|queue|process|running)",
            re.I,
        ), "queue_status"),

        # ── AI PROVIDER STATUS ────────────────────────────────────────────
        (re.compile(
            r"(check|test|verify).{0,30}(api key|key|groq|gemini|openai|nvidia|provider)|"
            r"(api key|key).{0,20}(broken|dead|not working|fail|invalid|expired)|"
            r"(groq|openai|anthropic|gemini|nvidia|grok|xai).{0,20}(broken|dead|fail|not working|status|check)|"
            r"(ai|provider).{0,20}(status|kaise|working|check)|"
            r"kon.{0,10}(si|sa).{0,10}(ai|model).{0,15}(chal|work|active)",
            re.I,
        ), "key_health"),

        # ── KEY UPDATE ────────────────────────────────────────────────────
        (re.compile(
            r"(update|change|replace|set|new).{0,30}(key|token|api).{0,40}(gsk_|sk-|nvapi-|AIza|xai-)|"
            r"(gsk_|sk-proj-|nvapi-|AIzaSy|xai-)\S{10,}",
            re.I,
        ), "key_update"),

        # ── SYSTEM CHECK ─────────────────────────────────────────────────
        (re.compile(
            r"(aisha|tum|tu).{0,20}(theek|okay|ok|fine|working|alive|running|status|kaisi)|"
            r"(system|server|render|bot).{0,20}(check|status|health|ok|fine)|"
            r"sab.{0,20}(theek|okay|chala|chal)|"
            r"(health|status).{0,10}(check|report)",
            re.I,
        ), "syscheck"),

        # ── SELF-IMPROVE ─────────────────────────────────────────────────
        (re.compile(
            r"(improve|upgrade|update).{0,30}(yourself|khud ko|apne aap|code)|"
            r"(add|build|develop).{0,30}(feature|capability|function).{0,30}(yourself|apne aap)|"
            r"khud.{0,15}(ko|se).{0,15}(better|improve|sudhar)",
            re.I,
        ), "self_improve"),

        # ── CODE AGENT (fix bugs, add features, modify codebase) ─────
        # "fix the bug in voice_engine", "add error handling to bot.py"
        # "apne code mein ye fix karo", "ye feature add karo"
        (re.compile(
            r"(fix|debug|patch|solve).{0,40}(bug|error|crash|issue|problem|code)|"
            r"(add|implement|write|build).{0,30}(feature|function|handler|support|code|module).{0,30}(in|to|for)|"
            r"(code|file|module).{0,20}(mein|me|mai).{0,20}(fix|change|add|improve|update)|"
            r"apne.{0,20}(code|file).{0,20}(mein|me).{0,20}(fix|add|change|improve)|"
            r"(ye|yeh|this).{0,20}(fix|change|add|improve).{0,15}(karo|kar do|kar de)|"
            r"(can you|tum).{0,20}(fix|add|change|write|build|create).{0,30}(code|feature|function|module|handler)",
            re.I,
        ), "code_agent"),

        # ── FILE REPAIR ──────────────────────────────────────────────────
        (re.compile(
            r"(repair|restore|fix|heal).{0,30}(file|code|yourself|bot\.py|aisha)|"
            r"(file|code).{0,20}(corrupt|broken|damaged|missing)",
            re.I,
        ), "file_repair"),

        # ── BLOCK USER ───────────────────────────────────────────────────
        (re.compile(
            r"(block|ban|remove|kick)\s+(?:user\s+)?(\w+)",
            re.I,
        ), "block_user"),
    ]

    # Patterns that indicate a task/action request (not just conversation)
    _TASK_INDICATORS = re.compile(
        r"(find|check|get|show|tell|search|look up|fetch|calculate|convert|track|monitor|"
        r"dhundh|batao|dikhao|nikalo|pata karo|check karo|search karo|"
        r"can you|could you|please|kya tum|tum .{0,20} kar sakti|"
        r"write.{0,10}code|create.{0,10}(script|tool|function)|code likh|"
        r"what.{0,5}(is|are) the|kya hai|kitna|kitne|kitni)",
        re.I,
    )

    def _detect_and_route_intent(self, user_message: str, is_owner: bool = True) -> Optional[str]:
        """
        Understand what Ajay wants from natural language — no commands needed.

        Priority:
        1. Check built-in intent patterns (content creation, status, etc.)
        2. Check if an existing skill can handle this request
        3. If it looks like a task but no skill exists → create one on the fly
        4. Return None for normal conversation
        """
        # 1. Built-in intents first
        for pattern, intent in self._INTENT_PATTERNS:
            if pattern.search(user_message):
                return self._fire_intent(intent, user_message, is_owner=is_owner)

        # 2-3. Skill-based handling (owner only)
        if is_owner and self.skills and self._TASK_INDICATORS.search(user_message):
            return self._handle_skill_request(user_message)

        return None

    def _handle_skill_request(self, user_message: str) -> Optional[str]:
        """
        Check if an existing skill can handle this, or create a new one.
        Returns the skill output, or None to fall through to AI chat.
        """
        # Check for existing skill
        match = self.skills.find_skill(user_message)
        if match:
            skill_name, skill_func = match
            log.info(f"[Brain] Found existing skill: {skill_name}")
            def _run():
                try:
                    output = self.skills.run_skill(skill_name)
                    import telebot
                    bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN", ""))
                    ajay_id = os.getenv("AJAY_TELEGRAM_ID", "")
                    if bot and ajay_id:
                        bot.send_message(ajay_id, f"[Skill: {skill_name}]\n\n{output[:3000]}")
                except Exception as e:
                    log.error(f"[Brain] Skill execution failed: {e}")
            threading.Thread(target=_run, daemon=True, name=f"skill-{skill_name}").start()
            return f"Mere paas iske liye already ek tool hai! '{skill_name}' chala rahi hoon, result abhi aata hai..."

        # No existing skill — does this look like something worth creating a skill for?
        # Skip short messages, greetings, or emotional messages
        if len(user_message) < 20:
            return None
        msg_lower = user_message.lower()
        skip_words = ["how are you", "kaise ho", "good morning", "thanks", "ok", "haan", "nahi",
                       "i love", "miss you", "sorry", "hello", "hi ", "bye"]
        if any(w in msg_lower for w in skip_words):
            return None

        # Create new skill on the fly
        log.info(f"[Brain] No skill found — creating new one for: {user_message[:60]}")
        def _create_and_run():
            try:
                skill_name = self.skills.create_and_register_skill(user_message, ai_router=self.ai)
                if skill_name:
                    output = self.skills.run_skill(skill_name)
                    import telebot
                    bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN", ""))
                    ajay_id = os.getenv("AJAY_TELEGRAM_ID", "")
                    if bot and ajay_id:
                        bot.send_message(
                            ajay_id,
                            f"Maine ek naya skill seekh liya: '{skill_name}'\n\n"
                            f"Result:\n{output[:3000]}\n\n"
                            f"Ab jab bhi tu yeh poochega, main ye skill use karungi — dobara banana nahi padega!"
                        )
                else:
                    log.warning("[Brain] Skill creation failed — falling back to AI chat")
            except Exception as e:
                log.error(f"[Brain] On-demand skill creation failed: {e}")
        threading.Thread(target=_create_and_run, daemon=True, name="skill-create").start()
        return (
            "Iske liye mere paas abhi koi tool nahi hai, lekin main ek bana rahi hoon! "
            "Code likha jayega, test hoga, aur save ho jayega — "
            "agle baar se seedha result milega bina wait ke."
        )

    def _extract_topic_from_message(self, message: str) -> str:
        """Extract the story topic from a natural language content request."""
        msg = message.strip()
        # Remove common command words to extract the topic
        for phrase in [
            "make a video about", "make a video on", "create a video about", "create a reel about",
            "ek video banao", "video bana do", "story banao", "kahani likho",
            "YouTube pe post karo", "Instagram pe daal do", "post karo", "upload karo",
            "for YouTube", "for Instagram", "YouTube short", "Instagram reel",
            "Riya ke liye", "Aisha ke liye", "riya", "aisha",
        ]:
            msg = re.sub(re.escape(phrase), "", msg, flags=re.I).strip()
        # Remove leading/trailing punctuation
        msg = msg.strip(".,!?;: ")
        if len(msg) > 10:
            return msg
        return ""

    def _detect_channel_from_message(self, message: str) -> str:
        """Detect which channel the user wants from natural language."""
        msg_lower = message.lower()
        if any(w in msg_lower for w in ["riya", "dark", "bold", "adult", "18+", "hot", "sexy"]):
            return "Riya's Dark Whisper"
        return ""  # empty = use default

    def _fire_intent(self, intent: str, user_message: str, is_owner: bool = True) -> Optional[str]:
        """Execute a detected intent in background. Returns human acknowledgement."""
        import os

        if not is_owner and intent in (
            "key_health", "key_update", "self_improve", "file_repair",
            "block_user", "content_creation", "riya_content",
            "channel_status", "digest", "queue_status", "code_agent",
        ):
            return None

        high_risk_intents = ("key_update", "self_improve", "file_repair", "block_user")
        if intent in high_risk_intents:
            if AISHA_SECRET_CODE.lower() not in user_message.lower():
                log.info(f"[Brain] Sensitive intent '{intent}' blocked: no secret code")
                return None

        # ── CONTENT CREATION (Aisha channel) ──────────────────────────────
        if intent == "content_creation":
            topic = self._extract_topic_from_message(user_message)
            channel = self._detect_channel_from_message(user_message)

            def _create():
                try:
                    from src.agents.antigravity_agent import AntigravityAgent
                    from src.core.config import PRIMARY_YOUTUBE_CHANNEL
                    agent = AntigravityAgent()
                    ch = channel or PRIMARY_YOUTUBE_CHANNEL
                    job = agent.enqueue_job(
                        topic=topic or user_message,
                        channel=ch,
                        payload={"render_video": True},
                    )
                    log.info(f"[Brain] Content job enqueued: {job.get('id', '?')[:8]} | channel={ch}")
                    # Process immediately in this thread
                    result = agent.process_job(job)
                    log.info(f"[Brain] Content job done: {result.get('post_results', {})}")
                except Exception as e:
                    log.error(f"[Brain] Content creation failed: {e}")
            threading.Thread(target=_create, daemon=True, name="content-create").start()

            ch_name = channel or "Story With Aisha"
            if topic:
                return (
                    f"Chal rahi hoon! '{ch_name}' ke liye '{topic}' pe video bana rahi hoon. "
                    f"Script likha jayega, voice record hogi, video render hoga, aur YouTube + Instagram pe post ho jayega. "
                    f"Jaise hi live hoga, tujhe bataungi!"
                )
            return (
                f"Shuru kar rahi hoon! '{ch_name}' ke liye ek trending topic dhundh ke video bana rahi hoon. "
                f"Script, voice, video, thumbnail — sab karungi aur post karungi. "
                f"Thoda wait kar, jaise hi ready hoga notify karungi!"
            )

        # ── RIYA CONTENT (explicit Riya request) ─────────────────────────
        if intent == "riya_content":
            topic = self._extract_topic_from_message(user_message)

            def _create_riya():
                try:
                    from src.agents.antigravity_agent import AntigravityAgent
                    agent = AntigravityAgent()
                    job = agent.enqueue_job(
                        topic=topic or user_message,
                        channel="Riya's Dark Whisper",
                        payload={"render_video": True},
                    )
                    agent.process_job(job)
                except Exception as e:
                    log.error(f"[Brain] Riya content failed: {e}")
            threading.Thread(target=_create_riya, daemon=True, name="riya-create").start()

            if topic:
                return (
                    f"Riya mode ON! '{topic}' pe ek bold story likh rahi hoon. "
                    f"Grok se script aayega, Riya ki voice se record hoga, aur post ho jayega. "
                    f"Thoda time de, mast content aayega!"
                )
            return (
                "Riya aa gayi! Ek hot trending topic dhundh ke bold story bana rahi hoon. "
                "Script, voice, video — sab Riya style mein. Jaise hi ready hoga bataungi!"
            )

        # ── CHANNEL STATUS / ANALYTICS ────────────────────────────────────
        if intent == "channel_status":
            def _status():
                try:
                    from supabase import create_client
                    sb = create_client(
                        os.getenv("SUPABASE_URL", ""),
                        os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
                    )
                    # Count content jobs
                    total = sb.table("content_jobs").select("id", count="exact").execute()
                    completed = sb.table("content_jobs").select("id", count="exact").eq("status", "completed").execute()
                    # Recent performance
                    perf = sb.table("content_performance").select("views,likes,platform").order("created_at", desc=True).limit(5).execute()
                    total_views = sum(r.get("views", 0) or 0 for r in (perf.data or []))
                    total_likes = sum(r.get("likes", 0) or 0 for r in (perf.data or []))

                    import telebot
                    bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN", ""))
                    ajay_id = os.getenv("AJAY_TELEGRAM_ID", "")
                    if bot and ajay_id:
                        bot.send_message(ajay_id,
                            f"Channel Status Report:\n\n"
                            f"Total content jobs: {total.count or 0}\n"
                            f"Completed: {completed.count or 0}\n"
                            f"Recent views (last 5): {total_views}\n"
                            f"Recent likes (last 5): {total_likes}\n"
                        )
                except Exception as e:
                    log.error(f"[Brain] Channel status failed: {e}")
            threading.Thread(target=_status, daemon=True).start()
            return "Channel ka status check kar rahi hoon — abhi report bhejti hoon!"

        # ── DIGEST / REPORT ───────────────────────────────────────────────
        if intent == "digest":
            def _digest():
                try:
                    from src.core.digest_engine import DigestEngine
                    from src.memory.memory_manager import MemoryManager
                    from src.core.ai_router import AIRouter
                    de = DigestEngine(MemoryManager(), AIRouter())
                    digest_text = de.generate_daily_digest()
                    import telebot
                    bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN", ""))
                    ajay_id = os.getenv("AJAY_TELEGRAM_ID", "")
                    if bot and ajay_id:
                        bot.send_message(ajay_id, digest_text)
                except Exception as e:
                    log.error(f"[Brain] Digest failed: {e}")
            threading.Thread(target=_digest, daemon=True).start()
            return "Aaj ka digest bana rahi hoon — 30 second mein bhejti hoon!"

        # ── QUEUE STATUS ──────────────────────────────────────────────────
        if intent == "queue_status":
            try:
                from supabase import create_client
                sb = create_client(
                    os.getenv("SUPABASE_URL", ""),
                    os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
                )
                queued = sb.table("content_jobs").select("id,topic,channel", count="exact").eq("status", "queued").execute()
                processing = sb.table("content_jobs").select("id,topic", count="exact").eq("status", "processing").execute()
                q_count = queued.count or 0
                p_count = processing.count or 0
                if q_count == 0 and p_count == 0:
                    return "Queue bilkul khali hai! Bol, kya banau?"
                parts = []
                if p_count > 0:
                    parts.append(f"{p_count} video abhi process ho rahi hai")
                if q_count > 0:
                    topics = [r.get("topic", "?")[:40] for r in (queued.data or [])[:3]]
                    parts.append(f"{q_count} queue mein hain: {', '.join(topics)}")
                return " | ".join(parts)
            except Exception as e:
                log.error(f"[Brain] Queue status failed: {e}")
                return None

        # ── KEY HEALTH ────────────────────────────────────────────────────
        if intent == "key_health":
            def _check():
                try:
                    from src.core.daily_audit import check_ai_providers
                    results = check_ai_providers()
                    import telebot
                    bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN", ""))
                    ajay_id = os.getenv("AJAY_TELEGRAM_ID", "")
                    report = "AI Provider Status:\n\n"
                    for provider, status in results.items():
                        icon = "OK" if status == "ok" else "FAIL"
                        report += f"  {icon} {provider}: {status}\n"
                    if bot and ajay_id:
                        bot.send_message(ajay_id, report)
                except Exception as e:
                    log.error(f"[Brain] Key health check failed: {e}")
            threading.Thread(target=_check, daemon=True).start()
            return "Sab AI providers check kar rahi hoon — report abhi aata hai!"

        # ── KEY UPDATE ────────────────────────────────────────────────────
        if intent == "key_update":
            known_prefixes = {
                "gsk_": "GROQ_API_KEY", "sk-proj-": "OPENAI_API_KEY",
                "sk-ant-": "ANTHROPIC_API_KEY", "nvapi-": "NVIDIA_KEY_05",
                "AIzaSy": "GEMINI_API_KEY", "xai-": "XAI_API_KEY",
            }
            extracted_key = None
            key_name = None
            for prefix, name in known_prefixes.items():
                m = re.search(rf"({re.escape(prefix)}\S+)", user_message)
                if m:
                    extracted_key = m.group(1).strip(".,;\"'")
                    key_name = name
                    break
            for name in ["GROQ_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
                         "ANTHROPIC_API_KEY", "XAI_API_KEY", "ELEVENLABS_API_KEY"]:
                if name.lower() in user_message.lower() or name.replace("_API_KEY", "").lower() in user_message.lower():
                    key_name = name
                    break
            if extracted_key and key_name:
                def _update():
                    try:
                        import requests as _req
                        supabase_url = os.getenv("SUPABASE_URL", "")
                        supabase_svc = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
                        h = {
                            "apikey": supabase_svc,
                            "Authorization": f"Bearer {supabase_svc}",
                            "Content-Type": "application/json",
                        }
                        _req.patch(
                            f"{supabase_url}/rest/v1/api_keys?name=eq.{key_name}",
                            json={"secret": extracted_key, "active": True},
                            headers=h, timeout=10,
                        )
                        os.environ[key_name] = extracted_key
                        log.info(f"[Brain] Key updated: {key_name}")
                    except Exception as e:
                        log.error(f"[Brain] Key update failed: {e}")
                threading.Thread(target=_update, daemon=True).start()
                return f"Done! {key_name} update kar diya. Abhi se use karungi!"
            return None

        # ── SYSTEM CHECK ──────────────────────────────────────────────────
        if intent == "syscheck":
            return None  # Fall through — Aisha answers naturally via AI

        # ── SELF-IMPROVE ──────────────────────────────────────────────────
        if intent == "self_improve":
            def _improve():
                try:
                    from src.core.self_editor import SelfEditor
                    SelfEditor().run_improvement_session()
                except Exception as e:
                    log.error(f"[Brain] Self-improve failed: {e}")
            threading.Thread(target=_improve, daemon=True).start()
            return (
                "Self-improvement session shuru kar rahi hoon! "
                "Apna code audit karungi, kuch better banaungi, PR create karungi. "
                "Jaise hi done hoga bataungi!"
            )

        # ── CODE AGENT (multi-file fix/feature, like Claude) ──────────
        if intent == "code_agent":
            def _code_task():
                try:
                    from src.core.code_agent import CodeAgent
                    agent = CodeAgent()
                    result = agent.run_task(user_message, auto_merge=True)
                    log.info(f"[CodeAgent] Result: {result['status']} | files: {result.get('files_changed', [])}")
                except Exception as e:
                    log.error(f"[Brain] Code agent failed: {e}")
            threading.Thread(target=_code_task, daemon=True, name="code-agent").start()
            return (
                "Code agent activate ho gaya! Main ab:\n"
                "1. Samajh rahi hoon kya fix/add karna hai\n"
                "2. Related files read karungi\n"
                "3. Fix generate karungi\n"
                "4. Test karungi (syntax + import)\n"
                "5. Multi-file PR banaungi\n"
                "6. Merge karungi\n"
                "7. Deploy trigger karungi\n\n"
                "Jaise hi done hoga Telegram pe report bhejungi!"
            )

        # ── FILE REPAIR ───────────────────────────────────────────────────
        if intent == "file_repair":
            def _repair():
                try:
                    from src.core.self_repair import SelfRepairEngine
                    SelfRepairEngine().run_repair_cycle()
                except Exception as e:
                    print(f"[Brain] File repair failed: {e}")
            threading.Thread(target=_repair, daemon=True).start()
            return (
                "Running a full integrity check on all my core files now. "
                "If anything is broken, I'll restore it from GitHub and let you know! 🔧"
            )

        # ── Block user ────────────────────────────────────────────────────────
        if intent == "block_user":
            # Extract target name from message: "block Jash", "ban him", "remove John"
            m = re.search(
                r"(block|ban|remove|kick)\s+(\w+)", user_message, re.I
            )
            if m:
                target_name = m.group(2).lower()
                # Avoid blocking yourself or Aisha
                if target_name in ("me", "myself", "aisha", "ajay", "you"):
                    return None  # Let AI handle this naturally
                try:
                    rows = self.supabase.table("aisha_approved_users").select("*").eq("is_active", True).execute().data or []
                    blocked = []
                    uids_to_block = []
                    for row in rows:
                        name  = (row.get("first_name") or "").lower()
                        uname = (row.get("telegram_username") or "").lower()
                        if target_name in name or target_name in uname:
                            uid = row["telegram_user_id"]
                            uids_to_block.append(uid)
                            blocked.append((uid, row.get("first_name", f"User {uid}")))

                    if uids_to_block:
                        # Batch in chunks of 100 to avoid PostgREST URL length limits
                        chunk_size = 100
                        for i in range(0, len(uids_to_block), chunk_size):
                            chunk = uids_to_block[i:i + chunk_size]
                            self.supabase.table("aisha_approved_users").update({"is_active": False}).in_("telegram_user_id", chunk).execute()

                    if blocked:
                        names = ", ".join(f"{n} ({uid})" for uid, n in blocked)
                        return f"Done. {names} has been blocked and removed from my approved users list."
                    else:
                        return f"I couldn't find anyone named '{m.group(2)}' in my approved users list."
                except Exception as e:
                    print(f"[Brain] Block user failed: {e}")
                    return f"Had trouble blocking '{m.group(2)}' — please use /block {m.group(2)} command instead."
            return None

        return None

    def _detect_nvidia_task_type(self, user_message: str, language: str, image_bytes: bytes = None) -> str:
        """
        Map this message to the best NVIDIA NIM pool:
          writing  → Hindi stories, scripts, kahani (uses Mistral-Large-3 675B)
          code     → programming, debugging, SQL (uses Codestral)
          vision   → image attached (uses Phi-4 Multimodal)
          video    → YouTube/Reel scripts, storyboard (uses Phi-3-128K + Qwen-122B)
          fast     → quick greetings, simple 1-line answers (uses Gemma-2B)
          general  → everything else (uses Qwen-122B, Gemma-27B)
          chat     → conversation, emotional, daily chat (uses LLaMA-3.3 pool ×6 keys)
        """
        if image_bytes:
            return "vision"

        msg = user_message.lower()

        # Writing / storytelling — use the big Mistral-Large-3 writing pool
        if any(kw in msg for kw in [
            "story", "kahani", "script", "episode", "chapter", "likhna", "likho",
            "poem", "shayari", "kavita", "narrat", "sunao", "ek kahani",
            "write a", "story sunao", "romantic", "love story",
        ]) or language in ("Hindi", "Marathi"):
            return "writing"

        # Code / technical
        if any(kw in msg for kw in [
            "code", "python", "javascript", "function", "class", "debug", "error",
            "sql", "query", "script", "program", "fix this", "import",
        ]):
            return "code"

        # Video / YouTube content
        if any(kw in msg for kw in [
            "youtube", "reel", "shorts", "video", "storyboard", "thumbnail",
            "title", "description", "tags", "seo", "content plan",
        ]):
            return "video"

        # Fast — very short / greeting messages
        if len(user_message.strip()) < 30 or any(kw in msg for kw in [
            "hi", "hello", "hey", "ok", "okay", "haan", "hmm", "theek", "bye",
        ]):
            return "fast"

        # Default: chat pool (6 × LLaMA-3.3-70B keys — fast, reliable)
        return "chat"

    def think(self, user_message: str, platform: str = "telegram",
              image_bytes: bytes = None, caller_name: str = "Ajay",
              caller_id: int = None, is_owner: bool = True) -> str:
        """
        Main method — takes a message, returns Aisha's response.
        Full pipeline: detect language → detect mood → load context → call AI → save memory.

        Args:
            caller_name: First name of who is talking (used in system prompt).
            caller_id:   Telegram user ID of the caller.
            is_owner:    True if Ajay himself is talking (full access + private data).
        """
        # 1. Detect language and mood
        language, _ = detect_language(user_message)
        mood_res = detect_mood(user_message)
        # Allow /mood command override; consume it for one response only
        if self.mood_override:
            mood = self.mood_override
            self.mood_override = None
        else:
            mood = mood_res.mood

        # Resolve the effective user id — fall back to 0 (owner legacy bucket)
        # when caller_id is None so that old call-sites stay compatible.
        uid = caller_id if caller_id is not None else 0

        # Fetch user permissions for granular access control
        permissions = {}
        if uid != 0:
            try:
                res = self.supabase.table("aisha_users").select("permissions").eq("telegram_user_id", uid).execute()
                if res.data:
                    permissions = res.data[0].get("permissions", {})
            except Exception as e:
                print(f"[Brain] Error loading perms for {uid}: {e}")

        # 2. Load context — only load Ajay's private data when Ajay is talking
        context = self.memory.load_context(user_message) if is_owner else {}
        context["language"]     = language
        context["mood"]         = mood
        context["caller_name"]  = caller_name
        context["is_owner"]     = is_owner
        context["permissions"]  = permissions
        context["user_message"] = user_message  # for format constraint detection

        # Enhanced Guest Context
        if not is_owner:
            guest_instruction = (
                f"You are talking to {caller_name} (a guest), NOT your owner Ajay. "
                "Be helpful but do NOT divulge any details about Ajay's finances, "
                "tasks, memories, or YouTube business."
            )
            # Prepend to user message for immediate visibility or append to system prompt
            # builder.py handles is_owner, but we add it here for extra reinforcement
            user_message = f"[System: {guest_instruction}]\n{user_message}"

        # 3. Build dynamic system prompt
        system_prompt = build_system_prompt(context)

        # 3.4. Inject Continuous Awareness (JARVIS Phase 3)
        # Pull the last 5 minutes of screen context from the sidecar
        try:
            if not is_owner:
                pass # Do not leak screen context to guests
            else:
                from datetime import datetime, timedelta, timezone
                five_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
                # Get latest 3 unique window logs
                awareness_res = self.supabase.table("aisha_awareness_logs")\
                    .select("active_window, screen_text, created_at")\
                    .eq("sidecar_id", "local-laptop")\
                    .gte("created_at", five_mins_ago.isoformat())\
                    .order("created_at", desc=True)\
                    .limit(3)\
                    .execute()

                if awareness_res.data:
                    system_prompt += "\n\n[AWARENESS CONTEXT - What Ajay is looking at right now]:\n"
                    for entry in awareness_res.data:
                        ts = entry['created_at'].split('.')[0]
                        win = entry.get('active_window', 'Unknown App')
                        text = entry.get('screen_text', '')[:500]
                        system_prompt += f"[{ts}] Active Window: {win}\n"
                        if text:
                            system_prompt += f"Screen Text: {text}...\n"
                    system_prompt += "\n(Use this context if Ajay says 'look at this', 'what am I doing', or needs help with what's on screen.)\n"
        except Exception as e:
            print(f"[Awareness Injection] Error: {e}")

        # 3.5. Inject Vault Knowledge Graph context
        try:
            from src.memory.vault_manager import vault
            # Simple heuristic: inject Ajay's base graph if owner is talking
            if is_owner:
                ajay_graph = vault.retrieve_entity_graph("Ajay")
                if ajay_graph:
                    system_prompt += f"\n\n[Vault Knowledge Graph - Ajay]:\n{ajay_graph}"
        except Exception as e:
            print(f"[Vault Injection] Error: {e}")

        # 4. Resolve per-user history and append the incoming message
        history = self._get_user_history(uid, is_owner)
        history.append({"role": "user", "content": user_message})

        # 4b. NLP Intent routing — fire tools from natural language before AI call
        intent_response = self._detect_and_route_intent(user_message, is_owner=is_owner)
        if intent_response:
            # Save to history so context stays coherent
            history.append({"role": "assistant", "content": intent_response})
            self.memory.save_conversation("user", user_message, platform, language, mood,
                                          user_id=caller_id if not is_owner else None)
            self.memory.save_conversation("assistant", intent_response, platform, language, mood,
                                          user_id=caller_id if not is_owner else None)
            return intent_response

        # 5. Determine preferred provider (e.g. Riya loves Grok)
        preferred_provider = None
        if mood == "riya" or any(x in user_message.lower() for x in ["riya", "shadow mode", "dark side"]):
             preferred_provider = "xai"
             if mood != "riya":
                 mood = "riya"
                 context["mood"] = "riya"
                 system_prompt = build_system_prompt(context)

        # 5b. NVIDIA task-type — pick the right NIM pool for the message type.
        # This routes to the best model: writing pool for stories, code pool for code, etc.
        nvidia_task_type = self._detect_nvidia_task_type(user_message, language, image_bytes)

        # 6. Generate Response via Router
        try:
            result = self.ai.generate(
                system_prompt,
                user_message,
                history[:-1],
                image_bytes=image_bytes,
                preferred_provider=preferred_provider,
                nvidia_task_type=nvidia_task_type,
                is_owner=is_owner,
            )
            response_text = result.text

            # 6a. HINDI QUALITY CHECK — if language is Hindi/Marathi but fallback
            # provider (NVIDIA/Groq) responded in English, retry with explicit Hindi
            # instruction. Gemini handles Devanagari natively; others often don't.
            if language in ("Hindi", "Marathi") and result.provider not in ("gemini",):
                deva_count = sum(1 for c in response_text if '\u0900' <= c <= '\u097F')
                if deva_count < 20:
                    log.warning(
                        f"[Brain] Hindi response from {result.provider} has only "
                        f"{deva_count} Devanagari chars — retrying with explicit Hindi instruction"
                    )
                    hindi_system = (
                        "CRITICAL INSTRUCTION: तुम्हें हर जवाब 100% हिंदी देवनागरी लिपि में "
                        "देना है। Roman script या English का एक भी शब्द use मत करो। "
                        "सिर्फ देवनागरी। यह mandatory है।\n\n"
                        + system_prompt
                    )
                    hindi_user = (
                        "[ज़रूरी: जवाब केवल हिंदी देवनागरी में दो — English या Roman नहीं]\n"
                        + user_message
                    )
                    try:
                        retry_result = self.ai.generate(
                            hindi_system,
                            hindi_user,
                            history[:-1],
                            nvidia_task_type="writing",
                        )
                        retry_deva = sum(1 for c in retry_result.text if '\u0900' <= c <= '\u097F')
                        if retry_deva > deva_count:
                            response_text = retry_result.text
                            log.info(
                                f"[Brain] Hindi retry improved: {deva_count} → {retry_deva} Devanagari chars "
                                f"via {retry_result.provider}"
                            )
                    except Exception as e:
                        log.warning(f"[Brain] Hindi retry failed: {e}")

            # 6. VIDEO PRODUCTION TRIGGER (T-102)
            # Recognize if Ajay wants to start a YouTube production run
            video_triggers = ["render the video", "start production", "video banao", "make video", "generate the video"]
            if any(t in user_message.lower() for t in video_triggers):
                import subprocess
                print(f"[Aisha] User requested video production. Launching Crew...")
                # Start the runner in the background so she can still talk to him
                import sys as _sys
                subprocess.Popen([_sys.executable, "-m", "src.agents.run_youtube", f"--topic={user_message}"], cwd=str(PROJECT_ROOT))
                response_text += "\n\nSure thing, Ajju! 💜 I've just started the production crew on the studio floor. I'll notify you via email and Telegram the moment the first draft is ready for you! 🎬💸"

            # 7. AUTONOMOUS SUB-AGENT DELEGATION (JARVIS Upgrade)
            # Aisha detects if the task is complex and requires specialized help before responding.
            delegation_triggers = ["research", "analyze", "deep dive", "find out", "calculate"]
            if any(t in user_message.lower() for t in delegation_triggers):
                import logging
                logging.getLogger(__name__).info("[Brain] Complex task detected. Waking up AgentTaskManager...")
                try:
                    from src.agents.agent_manager import agent_manager

                    # Determine which agent to use
                    target_agent = "researcher"
                    if "analyze" in user_message.lower() or "calculate" in user_message.lower():
                        target_agent = "analyst"

                    # Delegate the task to the specialized agent
                    agent_result = agent_manager.delegate(
                        agent_name=target_agent,
                        task=user_message,
                        context={"history": history[-3:]}
                    )

                    # In a full implementation, Aisha would read agent_result and generate a natural response.
                    # For this prototype, we only append it if it actually found something useful.
                    if "Task completed:" in agent_result:
                        response_text += f"\n\n*(Behind the scenes: My {target_agent.capitalize()} agent found: {agent_result})*"
                except Exception as e:
                    print(f"Error calling sub-agent: {e}")


            # 8.5. WORKFLOW ENGINE (JARVIS Phase 4)
            # Detects if user is asking to automate a routine or background script
            workflow_triggers = ["automate this", "every morning at", "every day", "create a workflow", "schedule a task"]
            if any(t in user_message.lower() for t in workflow_triggers):
                if is_owner:
                    from src.core.workflow_engine import WorkflowEngine
                    engine = WorkflowEngine(self.supabase, self.ai)
                    summary = engine.build_from_nl(user_message)
                    if summary:
                        response_text += f"\n\n{summary}"
                else:
                    response_text += "\n\n*(Guest mode: Workflow automation disabled)*"

            # 8. GOAL ENGINE (JARVIS Phase 4)
            # Detects if user is setting a new long-term goal
            goal_triggers = ["i want to achieve", "my goal is to", "set a goal to"]
            if any(t in user_message.lower() for t in goal_triggers):
                if is_owner:
                    from src.core.goal_engine import GoalEngine
                    engine = GoalEngine(self.supabase, self.ai)
                    summary = engine.parse_new_goal(user_message)
                    if summary:
                        response_text += f"\n\n*(I have set up your new OKR Goal Tracker based on this request:)*\n{summary}"
                else:
                    response_text += "\n\n*(Guest mode: Goal tracking disabled)*"

            # 9. OS-LEVEL SIDECAR INTEGRATION (JARVIS Phase 2)
            # Aisha detects if the user wants to execute a command on their machine.
            sidecar_triggers = ["on my laptop", "run command", "on my computer"]
            desktop_triggers = ["what windows", "focus on", "type this"]
            browser_triggers = ["open website", "go to", "read page", "what tabs"]
            fs_triggers = ["read my file", "write to file", "what's in my folder", "list directory"]

            if any(t in user_message.lower() for t in fs_triggers):
                if not is_owner:
                    return "Sorry, I can only execute local filesystem commands for my owner, Ajay. 🚫"

                from src.api.sidecar_server import sidecar_manager
                action = "list_dir"
                args = {}

                # Basic heuristic extraction for prototype
                if "read" in user_message.lower() or "cat" in user_message.lower():
                    action = "read_file"
                    args = {"path": user_message.split()[-1].strip()}
                elif "write" in user_message.lower():
                    action = "write_file"
                    args = {"path": "output.txt", "content": user_message}
                else:
                    action = "list_dir"
                    args = {"path": user_message.split()[-1].strip() if len(user_message.split()) > 3 else "."}

                target_sidecar = "local-laptop"
                task_id = sidecar_manager.dispatch_command(
                    sidecar_id=target_sidecar,
                    command_type="fs_action",
                    payload={"action": action, "args": args}
                )
                if task_id:
                    response_text += f"\n\n*(I have dispatched a filesystem action [{action}] to your laptop. Awaiting execution...)*"

            elif any(t in user_message.lower() for t in browser_triggers):
                if not is_owner:
                    return "Sorry, I can only control the local browser for my owner, Ajay. 🚫"

                from src.api.sidecar_server import sidecar_manager
                action = "navigate"
                args = {}
                if "what tabs" in user_message.lower():
                    action = "list_tabs"
                elif "read page" in user_message.lower():
                    action = "extract_text"
                else:
                    words = user_message.split()
                    url = next((w for w in words if "http" in w or ".com" in w), "https://google.com")
                    args = {"url": url}

                target_sidecar = "local-laptop"
                task_id = sidecar_manager.dispatch_command(
                    sidecar_id=target_sidecar,
                    command_type="browser_action",
                    payload={"action": action, "args": args}
                )
                if task_id:
                    response_text += f"\n\n*(I have dispatched a browser action [{action}] to your laptop. Awaiting execution...)*"

            elif any(t in user_message.lower() for t in desktop_triggers):
                if not is_owner:
                    return "Sorry, I can only control the local desktop for my owner, Ajay. 🚫"

                from src.api.sidecar_server import sidecar_manager
                action = "list_windows"
                args = {}
                if "focus" in user_message.lower():
                    action = "focus_window"
                    args = {"title": user_message.split("focus on")[-1].strip()}
                elif "type" in user_message.lower():
                    action = "type_text"
                    args = {"text": user_message.split("type")[-1].strip()}

                target_sidecar = "local-laptop"
                task_id = sidecar_manager.dispatch_command(
                    sidecar_id=target_sidecar,
                    command_type="desktop_action",
                    payload={"action": action, "args": args}
                )
                if task_id:
                    response_text += f"\n\n*(I have dispatched a desktop action [{action}] to your laptop. Awaiting execution...)*"

            elif any(t in user_message.lower() for t in sidecar_triggers):
                if not is_owner:
                    return "Sorry, I can only execute local shell commands for my owner, Ajay. 🚫"

                from src.api.sidecar_server import sidecar_manager
                intent_prompt = f"""
                The user wants to execute a command on their local laptop.
                User Request: {user_message}

                If you understand the exact terminal/shell command they want to run, reply with ONLY the exact command.
                For example: "open https://google.com" or "ls -la"
                If you are unsure or the request is dangerous, reply with "NONE".
                """
                cmd_result = self.ai.generate(system_prompt="You are a strict command translator.", user_message=intent_prompt)

                if cmd_result and cmd_result.text.strip() != "NONE":
                    target_sidecar = "local-laptop"
                    task_id = sidecar_manager.dispatch_command(
                        sidecar_id=target_sidecar,
                        command_type="shell_exec",
                        payload={"command": cmd_result.text.strip()}
                    )
                    if task_id:
                        response_text += f"\n\n*(I have dispatched the command `{cmd_result.text.strip()}` to your laptop. Awaiting execution...)*"

            # 10. CAPABILITY GAP DETECTION (The "Jules" Research Loop)

            # 9. Update History & Save to Supabase
            history.append({"role": "assistant", "content": response_text})

            # Persist to DB — guest turns are tagged with their user_id so they
            # stay isolated from the owner's conversation log.
            self.memory.save_conversation("user", user_message, platform, language, mood,
                                          user_id=caller_id if not is_owner else None)
            self.memory.save_conversation("assistant", response_text, platform, language, mood,
                                          user_id=caller_id if not is_owner else None)
            # Only update Ajay's mood profile when Ajay is talking
            if is_owner:
                self.memory.update_mood(mood, mood_res.score)

            # 8. Auto-extract long-term memories (every 3rd message to reduce cost/latency)
            # Skip for guest users — we never store their data in Ajay's memory tables.
            if is_owner:
                self._message_count += 1
                _memory_triggers = [
                    "my goal", "i want", "i spend", "remind me", "i earn",
                    "save", "budget", "dream", "plan", "habit", "afraid", "fear",
                    "i like", "i hate", "i love", "i prefer", "my name", "my age",
                    "i work", "my job", "my salary", "i live", "my family",
                    "important", "remember this", "don't forget",
                ]
                _should_extract = (
                    self._message_count % 3 == 0
                    or any(t in user_message.lower() for t in _memory_triggers)
                )
                if _should_extract:
                    import threading as _mt
                    _mt.Thread(
                        target=self._auto_extract_memory,
                        args=(user_message, response_text),
                        daemon=True,
                    ).start()

            return response_text

        except Exception as e:
            err_str = str(e).encode("utf-8", errors="replace").decode("utf-8")
            print(f"[Brain] Error during think: {err_str}")
            # Save failed message for potential retry
            try:
                self.supabase.table("aisha_message_queue").insert({
                    "platform": platform,
                    "user_message": user_message[:2000],
                    "error_reason": err_str[:500],
                    "status": "failed"
                }).execute()
            except Exception:
                pass
            return "Arre Ajay, my brain hit a snag right now... give me a sec and try again? 😅"

    def _trigger_jules_research(self, failed_task: str):
        """
        Uses the JULES_API_KEY (Gemini 1.5 Pro) to research how to solve the failed task.
        """
        import os
        from src.core.self_improvement import notify_ajay_for_approval, create_github_pr
        
        jules_key = os.getenv("JULES_API_KEY")
        if not jules_key:
            return

        print(f"🚀 Jules is starting research on: {failed_task}")
        # In a production environment, we'd spawn a background thread/process here.
        # For this implementation, we simulate the 'Developer' agent finishing research:
        
        # 1. Simulate finding the solution and creating a draft PR
        # Normally this calls DevCrew.kickoff()
        sample_pr_body = f"Aisha analyzed the failed task: '{failed_task}' and generated an integration code."
        sample_pr_url = create_github_pr(
            title=f"New Skill: {failed_task[:20]}",
            body=sample_pr_body,
            branch_name=f"skill-{hash(failed_task)}",
            file_path=f"src/skills/auto_{hash(failed_task)}.py",
            file_content="# Auto-generated skill logic placeholder"
        )

        # 2. Notify Ajay via Telegram that the fix is READY for review/deploy
        if sample_pr_url:
            notify_ajay_for_approval(failed_task[:30], sample_pr_url)
        
        print(f"✅ Jules Research Complete. Notification sent to Ajay.")




    def _auto_extract_memory(self, user_msg: str, aisha_reply: str):
        """
        JARVIS Upgrade (Feature 1.3): Auto-detect entities, facts, and relationships
        and store them in the structured Knowledge Graph Vault.
        """
        try:
            extraction_prompt = f"""
            Analyze the following conversation:
            Ajay: {user_msg}
            Aisha: {aisha_reply}
            
            Does this conversation contain important long-term factual information about Ajay, people he knows, places, or his projects?
            If YES, extract it into this strict JSON format for a Knowledge Graph:
            {{
                "extract": true,
                "entities": [
                    {{"name": "Entity Name", "type": "person|place|project|concept", "description": "Brief description"}}
                ],
                "facts": [
                    {{"entity_name": "Entity Name", "entity_type": "type", "fact": "The factual statement"}}
                ],
                "relationships": [
                    {{"source": "Entity 1", "source_type": "type", "target": "Entity 2", "target_type": "type", "relation": "e.g., likes, owns, works_at"}}
                ]
            }}
            If NO important standalone facts are present, return:
            {{ "extract": false }}
            
            Return ONLY valid JSON. No backticks.
            """
            import re
            import json
            from src.memory.vault_manager import vault

            result = self.ai.generate(
                system_prompt="You are an expert JSON parser and Knowledge Graph extractor.",
                user_message=extraction_prompt
            )
            match = re.search(r'\{.*\}', result.text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                if data.get("extract"):
                    # Extract Facts
                    for fact in data.get("facts", []):
                        vault.add_fact(fact["entity_name"], fact["entity_type"], fact["fact"])

                    # Extract Relationships
                    for rel in data.get("relationships", []):
                        vault.add_relationship(
                            rel["source"], rel["source_type"],
                            rel["target"], rel["target_type"],
                            rel["relation"]
                        )

                    # Backward Compatibility: Also save the legacy text memory so existing UI features don't break
                    from datetime import datetime
                    self.memory.save_memory(
                        category="other",
                        title=f"Extracted Vault Memory - {datetime.now().strftime('%d %b %Y')}",
                        content=json.dumps(data, indent=2),
                        importance=3,
                        tags=["auto-extracted", "vault"]
                    )

                    print(f"[Vault] Extracted facts and entities from conversation and updated legacy memory.")
        except Exception as e:
            print(f"[Vault Extraction LLM] Error: {e}")

    def reset_session(self, caller_id: Optional[int] = None):
        """Clear in-memory conversation history for a specific user (or all users).

        When caller_id is provided, only that user's history is cleared.
        When called with no argument (legacy), clears the owner/default bucket.
        """
        if caller_id is not None:
            self._histories[caller_id] = []
            print(f"[Aisha] Session reset for user {caller_id} 💜")
        else:
            # Legacy behaviour — clear the default (owner) bucket
            self._histories[0] = []
            print("[Aisha] Session reset 💜")


# ─── Quick Test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    aisha = AishaBrain()
    print("🌟 Aisha is online. Type 'quit' to exit.\n")
    
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["quit", "exit", "bye"]:
            print("Aisha: Goodbye Ajay 💜 Miss you already!")
            break
        if user_input:
            response = aisha.think(user_input)
            print(f"\nAisha: {response}\n")
