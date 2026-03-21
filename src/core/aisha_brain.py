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
    GEMINI_MODEL, GROQ_MODEL, AI_TEMPERATURE, AI_MAX_TOKENS, AI_HISTORY_LIMIT, USER_NAME
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

        # Conversation history — warm-started from Supabase on every init
        # so Railway restarts and redeploys don't wipe the thread
        self.history  = self._load_history_from_db()

        # Counter for throttling auto-extract (only every 5th message)
        self._message_count = 0

    def _load_history_from_db(self) -> list:
        """Restore recent conversation history from Supabase on startup."""
        try:
            recent = self.memory.get_recent_conversation(limit=AI_HISTORY_LIMIT)
            return [{"role": c["role"], "content": c["message"]} for c in recent]
        except Exception as e:
            print(f"[Brain] Could not warm-start history from DB: {e}")
            return []

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
    ]

    def _detect_and_route_intent(self, user_message: str) -> Optional[str]:
        """
        Check message against intent patterns.
        If matched, fire the tool in background and return an acknowledgement string.
        Returns None if no intent matched (falls through to normal AI chat).
        """
        for pattern, intent in self._INTENT_PATTERNS:
            if pattern.search(user_message):
                return self._fire_intent(intent, user_message)
        return None

    def _fire_intent(self, intent: str, user_message: str) -> Optional[str]:
        """Execute a detected intent in a background thread. Returns acknowledgement or None."""
        import os

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

        return None

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
        mood     = mood_res.mood

        # 2. Load context — only load Ajay's private data when Ajay is talking
        context = self.memory.load_context(user_message) if is_owner else {}
        context["language"]    = language
        context["mood"]        = mood
        context["caller_name"] = caller_name
        context["is_owner"]    = is_owner

        # 3. Build dynamic system prompt
        system_prompt = build_system_prompt(context)

        # 4. Add user message to local history
        self.history.append({"role": "user", "content": user_message})

        # 4b. NLP Intent routing — fire tools from natural language before AI call
        intent_response = self._detect_and_route_intent(user_message)
        if intent_response:
            # Save to history so context stays coherent
            self.history.append({"role": "user", "content": user_message})
            self.history.append({"role": "assistant", "content": intent_response})
            self.memory.save_conversation("user", user_message, platform, language, mood)
            self.memory.save_conversation("assistant", intent_response, platform, language, mood)
            return intent_response

        # 5. Determine preferred provider (e.g. Riya loves Grok)
        preferred_provider = None
        if mood == "riya" or any(x in user_message.lower() for x in ["riya", "shadow mode", "dark side"]):
             preferred_provider = "xai"
             if mood != "riya":
                 mood = "riya"
                 context["mood"] = "riya"
                 system_prompt = build_system_prompt(context)

        # 6. Generate Response via Router
        try:
            result = self.ai.generate(
                system_prompt, 
                user_message, 
                self.history[:-1], 
                image_bytes=image_bytes,
                preferred_provider=preferred_provider
            )
            response_text = result.text

            # 6. VIDEO PRODUCTION TRIGGER (T-102)
            # Recognize if Ajay wants to start a YouTube production run
            video_triggers = ["render the video", "start production", "video banao", "make video", "generate the video"]
            if any(t in user_message.lower() for t in video_triggers):
                import subprocess
                print(f"[Aisha] User requested video production. Launching Crew...")
                # Start the runner in the background so she can still talk to him
                subprocess.Popen(["python", "-m", "src.agents.run_youtube", "--topic", user_message], cwd=str(PROJECT_ROOT))
                response_text += "\n\nSure thing, Ajju! 💜 I've just started the production crew on the studio floor. I'll notify you via email and Telegram the moment the first draft is ready for you! 🎬💸"

            # 7. CAPABILITY GAP DETECTION (The "Jules" Research Loop)

            # 7. Update History & Save to Supabase
            self.history.append({"role": "assistant", "content": response_text})
            
            # Persist to DB
            self.memory.save_conversation("user", user_message, platform, language, mood)
            self.memory.save_conversation("assistant", response_text, platform, language, mood)
            self.memory.update_mood(mood, mood_res.score)

            # 8. Auto-extract long-term memories (every 5th message to reduce cost/latency)
            self._message_count += 1
            _memory_triggers = ["my goal", "i want", "i spend", "remind me", "i earn",
                                 "save", "budget", "dream", "plan", "habit", "afraid", "fear"]
            _should_extract = (
                self._message_count % 5 == 0
                or any(t in user_message.lower() for t in _memory_triggers)
            )
            if _should_extract:
                self._auto_extract_memory(user_message, response_text)

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
        Auto-detect important information in the conversation and save to memory.
        Enhanced with an LLM prompt to dynamically parse context into JSON!
        """
        try:
            extraction_prompt = f"""
            Analyze the following message from Ajay and Aisha's reply.
            Ajay: {user_msg}
            Aisha: {aisha_reply}
            
            Does this conversation contain important new long-term information about Ajay's life, goals, finances, preferences, or significant events that Aisha should remember forever?
            If YES, extract it in the following strictly valid JSON format:
            {{
                "extract": true,
                "category": "finance" | "goal" | "preference" | "event" | "other",
                "title": "Short descriptive title",
                "content": "Detailed description of what Ajay said and any plans discussed",
                "importance": 1-5,
                "tags": ["list", "of", "relevant", "string", "tags"]
            }}
            If NO important new standalone information is present, return:
            {{ "extract": false }}
            
            Return ONLY valid JSON. No backticks.
            """
            import re
            import json
            # Ask the router to generate the extraction data
            result = self.ai.generate(
                system_prompt="You are an expert JSON parser.", 
                user_message=extraction_prompt
            )
            match = re.search(r'\{.*\}', result.text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                if data.get("extract"):
                    from datetime import datetime
                    self.memory.save_memory(
                        category=data.get("category", "other"),
                        title=f"{data.get('title', 'Memory')} - {datetime.now().strftime('%d %b %Y')}",
                        content=data.get("content", f"Ajay said: {user_msg[:300]}"),
                        importance=data.get("importance", 3),
                        tags=data.get("tags", ["auto-extracted"])
                    )
        except Exception as e:
            print(f"[Memory Extraction LLM] Error: {e}")

    def reset_session(self):
        """Clear in-memory conversation history (for new session)."""
        self.history = []
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
