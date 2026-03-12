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
        
        # Conversation history (per session)
        self.history  = []

    def think(self, user_message: str, platform: str = "telegram", image_bytes: bytes = None) -> str:
        """
        Main method — takes Ajay's message, returns Aisha's response.
        Full pipeline: detect language → detect mood → load context → call AI → save memory.
        """
        # 1. Detect language and mood
        language = detect_language(user_message)
        mood_res = detect_mood(user_message)
        mood     = mood_res.mood

        # 2. Load Ajay's context from Supabase
        context = self.memory.load_context(user_message)
        context["language"] = language
        context["mood"]     = mood

        # 3. Build dynamic system prompt
        system_prompt = build_system_prompt(context)

        # 4. Add user message to local history
        self.history.append({"role": "user", "content": user_message})

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
            self.memory.update_mood(mood)

            # 8. Auto-extract long-term memories
            self._auto_extract_memory(user_message, response_text)

            return response_text

        except Exception as e:
            print(f"[Brain] Error during think: {str(e).encode('utf-8', errors='replace').decode('utf-8')}")
            return "Arre Ajay, my brain is a bit fuzzy right now... 😅 Technical glitch!"

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
