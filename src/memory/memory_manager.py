"""
memory_manager.py
=================
Handles Aisha's persistent memory in Supabase.
Now enhanced with pgvector for Semantic, Emotional, Episodic, and Skill Memory!
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from supabase import create_client, Client
import json

class MemoryManager:
    """Manages Aisha's persistent memory in Supabase."""

    def __init__(self, supabase: Optional[Client] = None):
        if supabase:
            self.db = supabase
        else:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_KEY")
            if not url or not key:
                raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
            self.db = create_client(url, key)

    # ── Profile ────────────────────────────────────────────────

    def get_profile(self) -> Dict[str, Any]:
        """Load Ajay's full profile."""
        try:
            res = self.db.table("ajay_profile").select("*").limit(1).execute()
            return res.data[0] if res.data else {}
        except Exception as e:
            print(f"[Memory] Error loading profile: {e}")
            return {}

    def update_mood(self, mood: str, score: Optional[int] = None):
        """Update Ajay's current mood in profile."""
        try:
            self.db.table("ajay_profile").update({
                "current_mood": mood,
                "updated_at": datetime.now().isoformat()
            }).eq("name", "Ajay").execute()

            if score is not None:
                self.db.table("aisha_mood_tracker").insert({
                    "mood": mood,
                    "mood_score": score
                }).execute()
        except Exception as e:
            print(f"[Memory] Error updating mood: {e}")

    # ── Memory (CRUD & Vector) ─────────────────────────────────

    def get_top_memories(self, limit: int = 12) -> List[Dict[str, Any]]:
        """Get the highest importance static memories."""
        try:
            res = (
                self.db.table("aisha_memory")
                .select("category, title, content, importance")
                .eq("is_active", True)
                .order("importance", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []
        except Exception as e:
            print(f"[Memory] Error getting top memories: {e}")
            return []

    def get_semantic_memories(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for relevant memories using pgvector!
        (Requires an embedding of the query first)
        """
        embedding = self._generate_embedding(query)
        if not embedding:
            return []

        try:
            res = self.db.rpc(
                'match_memories',
                {
                    'query_embedding': embedding,
                    'match_threshold': 0.7,
                    'match_count': limit
                }
            ).execute()
            return res.data or []
        except Exception as e:
            print(f"[Memory] Error fetching semantic memories: {e}")
            return []

    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embeddings using Google Gemini's text-embedding-004 model.
        Includes a retry loop with exponential backoff for rate limiting.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or "your_" in api_key.lower():
            return None

        import time
        max_retries = 3
        base_delay = 2

        for attempt in range(max_retries):
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=text,
                    task_type="retrieval_document",
                )
                return result['embedding']
            except Exception as e:
                # If rate limited (often 429) or other API error
                print(f"[Memory] Embedding attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(base_delay * (2 ** attempt)) # 2, 4, 8s backoff
                else:
                    print(f"[Memory] Fatal: Failed after {max_retries} attempts.")
                    return None

    def save_memory(self, category: str, title: str, content: str, importance: int = 3, tags: Optional[List[str]] = None):
        """Save a new memory to Supabase with embeddings."""
        embedding = self._generate_embedding(content)
        try:
            self.db.table("aisha_memory").insert({
                "category": category,
                "title": title,
                "content": content,
                "importance": importance,
                "tags": tags or [],
                "source": "conversation",
                "embedding": embedding
            }).execute()
        except Exception as e:
            print(f"[Memory] Error saving memory: {e}")

    # ── Specialized Memory Types (Emotional, Skill, Episodic) ──

    def save_emotional_memory(self, mood: str, trigger: str, context: str):
        """Save a specific emotional trigger and pattern."""
        embedding = self._generate_embedding(context)
        try:
            self.db.table("aisha_emotional_memory").insert({
                "mood_state": mood,
                "trigger": trigger,
                "context_text": context,
                "embedding": embedding
            }).execute()
        except Exception as e:
            print(f"[Memory] Error saving emotional memory: {e}")

    def save_skill_memory(self, skill_name: str, description: str):
        """Save a learned skill for self-improvement."""
        embedding = self._generate_embedding(description)
        try:
            self.db.table("aisha_skill_memory").insert({
                "skill_name": skill_name,
                "description": description,
                "embedding": embedding
            }).execute()
        except Exception as e:
            print(f"[Memory] Error saving skill memory: {e}")

    def save_episodic_memory(self, entity: str, description: str, date_occurred: str):
        """Save an event or relationship memory."""
        embedding = self._generate_embedding(description)
        try:
            self.db.table("aisha_episodic_memory").insert({
                "entity": entity,
                "event_description": description,
                "event_date": date_occurred,
                "embedding": embedding
            }).execute()
        except Exception as e:
            print(f"[Memory] Error saving episodic memory: {e}")

    # ── Conversations ──────────────────────────────────────────

    def save_conversation(self, role: str, message: str, platform: str = "telegram", language: str = "English", mood: str = "casual"):
        """Log conversation turn to Supabase."""
        embedding = self._generate_embedding(message)
        try:
            self.db.table("aisha_conversations").insert({
                "platform": platform,
                "role": role,
                "message": message,
                "language": language,
                "mood_detected": mood,
                "embedding": embedding
            }).execute()
        except Exception as e:
            print(f"[Memory] Error saving conversation: {e}")

    def get_recent_conversation(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation history for context continuity."""
        try:
            res = (
                self.db.table("aisha_conversations")
                .select("role, message, created_at")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return list(reversed(res.data or []))
        except Exception as e:
            print(f"[Memory] Error loading conversation: {e}")
            return []

    # ── Context Loader ─────────────────────────────────────────

    def load_context(self, user_message: str = "") -> Dict[str, Any]:
        """Load full context from Supabase for Aisha's system prompt."""
        try:
            profile = self.get_profile()

            # Combine top static memories and semantic memories
            memories_list = self.get_top_memories(limit=5)

            # If user message is provided, fetch 3 semantic memories related to it
            if user_message:
                semantic_mems = self.get_semantic_memories(user_message, limit=3)
                # Deduplicate by title
                existing_titles = {m.get('title') for m in memories_list}
                for sm in semantic_mems:
                    if sm.get('title') not in existing_titles:
                        memories_list.append(sm)

            memories_text = "\n".join(
                f"[{m.get('category', 'OTHER').upper()}] {m.get('title', 'Memory')}: {m.get('content', '')}"
                for m in memories_list
            )

            # Get today's tasks
            today = datetime.now().date().isoformat()
            tasks_res = (
                self.db.table("aisha_schedule")
                .select("title, priority")
                .eq("due_date", today)
                .eq("status", "pending")
                .execute()
            )
            tasks_text = "\n".join(
                f"- [{t['priority'].upper()}] {t['title']}"
                for t in (tasks_res.data or [])
            ) or "No tasks for today"

            return {
                "profile": profile,
                "memories": memories_text,
                "today_tasks": tasks_text,
            }
        except Exception as e:
            print(f"[Memory] Error loading context: {e}")
            return {}

    def get_today_tasks(self) -> List[Dict[str, Any]]:
        """Get today's pending tasks."""
        try:
            today = datetime.now().date().isoformat()
            res = (
                self.db.table("aisha_schedule")
                .select("*")
                .eq("due_date", today)
                .eq("status", "pending")
                .execute()
            )
            return res.data or []
        except Exception as e:
            print(f"[Memory] Error fetching today's tasks: {e}")
            return []
