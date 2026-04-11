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
import re
import threading
from datetime import datetime
from typing import Optional
from pathlib import Path

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
        # Initialize AI Router (handles Gemini, OpenAI, Groq, Mistral, Ollama)
        self.ai = AIRouter()

        # Initialize Supabase
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        self.memory   = MemoryManager(self.supabase)

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
    # Maps natural language to tool actions — no commands needed.
    # Patterns are checked before AI generation. Matching fires the tool in a
    # background thread and returns an instant acknowledgement.

    _INTENT_PATTERNS = [
        # Content creation
        (re.compile(
            r"(make|create|produce|generate|shoot|record|bana[ao]?|ek video|shorts?).{0,50}"
            r"(video|content|youtube|short|reel|episode)",
            re.I,
        ), "content_creation"),
        # Key health check
        (re.compile(
            r"(check|test|verify).{0,30}(api key|key|groq|gemini|openai|nvidia|provider)|"
            r"(api key|key).{0,20}(broken|dead|not working|fail|invalid|expired)|"
            r"(groq|openai|anthropic|gemini|nvidia).{0,20}(broken|dead|fail|not working)",
            re.I,
        ), "key_health"),
        # Update a key
        (re.compile(
            r"(update|change|replace|set|new).{0,30}(key|token|api).{0,40}(gsk_|sk-|nvapi-|AIza|xai-)|"
            r"(gsk_|sk-proj-|nvapi-|AIzaSy|xai-)\S{10,}",
            re.I,
        ), "key_update"),
        # Search for a new API / platform
        (re.compile(
            r"(find|search|how to get|get the?).{0,30}(api|token|key).{0,30}(for|of)?\s+\w+|"
            r"add.{0,20}(tiktok|twitter|x\.com|facebook|instagram|snapchat|youtube).{0,20}(api|support)|"
            r"(tiktok|twitter|snapchat|pinterest).{0,20}(api|key|access)",
            re.I,
        ), "api_search"),
        # System / health check
        (re.compile(
            r"(aisha|tum|tu).{0,20}(theek|okay|ok|fine|working|alive|running|status)|"
            r"(system|server|render|bot).{0,20}(check|status|health|ok|fine)|"
            r"sab.{0,20}(theek|okay|chala)",
            re.I,
        ), "syscheck"),
        # Self-improve
        (re.compile(
            r"(improve|upgrade|update).{0,30}(yourself|khud ko|apne aap|code|yourself)|"
            r"(add|build|develop).{0,30}(feature|capability|function).{0,30}(yourself|apne aap)",
            re.I,
        ), "self_improve"),
        # File repair
        (re.compile(
            r"(repair|restore|fix|heal).{0,30}(file|code|yourself|bot\.py|aisha)|"
            r"(file|code).{0,20}(corrupt|broken|damaged|missing)",
            re.I,
        ), "file_repair"),
        # Block user — natural language: "block Jash", "remove Jash", "ban Jash"
        (re.compile(
            r"(block|ban|remove|kick).{1,30}\b(\w+)\b",
            re.I,
        ), "block_user"),
    ]

    def _detect_and_route_intent(self, user_message: str, is_owner: bool = True) -> Optional[str]:
        """
        Check message against intent patterns.
        If matched, fire the tool in background and return an acknowledgement string.
        Returns None if no intent matched (falls through to normal AI chat).
        """
        for pattern, intent in self._INTENT_PATTERNS:
            if pattern.search(user_message):
                return self._fire_intent(intent, user_message, is_owner=is_owner)
        return None

    def _fire_intent(self, intent: str, user_message: str, is_owner: bool = True) -> Optional[str]:
        """Execute a detected intent in a background thread. Returns acknowledgement or None."""
        import os

        # SECURITY: Only the authorized owner can trigger system-level intents.
        if not is_owner and intent in ("key_health", "key_update", "api_search", "self_improve", "file_repair", "block_user", "content_creation"):
            # Guests should not trigger any background tool execution
            return None

        # SENSITIVE OPERATIONS REQUIRE THE SECRET CODE
        high_risk_intents = ("key_update", "self_improve", "file_repair", "block_user")
        if intent in high_risk_intents:
            # Check if user message contains the secret code (e.g. "code: aisha-69")
            # We use a simple case-insensitive search for the code.
            if AISHA_SECRET_CODE.lower() not in user_message.lower():
                print(f"[Brain] Sensitive intent '{intent}' blocked: Missing secret code.")
                return None # Fall through to AI chat (Aisha won't execute)

        # ── Content creation ──────────────────────────────────────────────────
        if intent == "content_creation":
            def _create():
                try:
                    from src.agents.antigravity_agent import AntigravityAgent
                    agent = AntigravityAgent()
                    # Detect channel from message
                    msg_lower = user_message.lower()
                    if "riya" in msg_lower or "dark" in msg_lower or "romance" in msg_lower:
                        channel = "Riya's Dark Romance Library"
                    else:
                        channel = "Aisha & Him"
                    job = agent.enqueue_job(topic=user_message, channel=channel)
                    print(f"[Brain] Content job enqueued: {job.get('id', '?')[:8]}")
                except Exception as e:
                    print(f"[Brain] Content creation failed: {e}")
            threading.Thread(target=_create, daemon=True).start()
            return (
                "Ha bilkul, Ajju! I'm queuing up the content production now. "
                "I'll pick a topic, write the script, record the voice, render the video, "
                "and upload it — I'll text you when it's live! 💜🎬"
            )

        # ── API key health ────────────────────────────────────────────────────
        if intent == "key_health":
            def _check():
                try:
                    from src.core.credential_manager import CredentialManager
                    cm = CredentialManager()
                    cm.run_daily_health_check()
                except Exception as e:
                    print(f"[Brain] Key health check failed: {e}")
            threading.Thread(target=_check, daemon=True).start()
            return (
                "Running a full API key health check now. "
                "I'll test all providers and send you a report in ~30 seconds! 🔑"
            )

        # ── Key update ────────────────────────────────────────────────────────
        if intent == "key_update":
            # Try to extract key name and value from message
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
            # Also check for explicit key name in message
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
                        print(f"[Brain] Key updated via NLP: {key_name}")
                    except Exception as e:
                        print(f"[Brain] Key update failed: {e}")
                threading.Thread(target=_update, daemon=True).start()
                return (
                    f"Done, Ajju! I've updated `{key_name}` with the new key you gave me. "
                    f"I'll use it immediately — say `/keyhealth` if you want me to verify it works! 🔑✅"
                )
            return None  # Let AI handle the message naturally

        # ── API search ────────────────────────────────────────────────────────
        if intent == "api_search":
            # Extract platform name
            platform_match = re.search(
                r"(tiktok|twitter|x\.com|facebook|instagram|snapchat|youtube|pinterest|"
                r"discord|twitch|spotify|reddit|linkedin)\b",
                user_message, re.I
            )
            if platform_match:
                platform = platform_match.group(1)
                def _search():
                    try:
                        from src.core.api_discovery import APIDiscoveryAgent
                        APIDiscoveryAgent().notify_ajay_api_setup(platform)
                    except Exception as e:
                        print(f"[Brain] API search failed: {e}")
                threading.Thread(target=_search, daemon=True).start()
                return (
                    f"Let me search how to get the {platform.title()} API for you! "
                    f"I'll send you the signup steps and direct link in a moment. 🔍"
                )
            return None

        # ── System check ─────────────────────────────────────────────────────
        if intent == "syscheck":
            return None  # Fall through to AI — Aisha will answer naturally

        # ── Self-improve ──────────────────────────────────────────────────────
        if intent == "self_improve":
            def _improve():
                try:
                    from src.core.self_editor import run_improvement_session
                    run_improvement_session()
                except Exception as e:
                    print(f"[Brain] Self-improve failed: {e}")
            threading.Thread(target=_improve, daemon=True).start()
            return (
                "Thik hai, Ajju! Triggering my self-improvement session now. "
                "I'll audit my own code, find something to make better, write the improvement, "
                "and text you when I'm upgraded! 💪🧠"
            )

        # ── File repair ───────────────────────────────────────────────────────
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
                    for log in awareness_res.data:
                        ts = log['created_at'].split('.')[0]
                        win = log.get('active_window', 'Unknown App')
                        text = log.get('screen_text', '')[:500] # truncate to save tokens
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
                subprocess.Popen(["python", "-m", "src.agents.run_youtube", f"--topic={user_message}"], cwd=str(PROJECT_ROOT))
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
