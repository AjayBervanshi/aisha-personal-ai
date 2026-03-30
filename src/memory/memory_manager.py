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

    def get_top_memories(self, limit: int = 12, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get the highest importance static memories."""
        try:
            query = (
                self.db.table("aisha_memory")
                .select("category, title, content, importance")
                .eq("is_active", True)
            )
            if workspace_id:
                query = query.eq("workspace_id", workspace_id)

            res = query.order("importance", desc=True).limit(limit).execute()
            return res.data or []
        except Exception as e:
            print(f"[Memory] Error getting top memories: {e}")
            return []

    def get_semantic_memories(self, query: str, limit: int = 5, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for relevant memories using pgvector!
        (Requires an embedding of the query first)
        """
        embedding = self._generate_embedding(query)
        if not embedding:
            return []

        try:
            # Note: match_memories RPC doesn't currently support filtering in SQL.
            # We fetch more then filter in Python to ensure enough results after filter.
            res = self.db.rpc(
                'match_memories',
                {
                    'query_embedding': embedding,
                    'match_threshold': 0.6, # lower threshold for raw pull
                    'match_count': limit * 4
                }
            ).execute()

            data = res.data or []
            # Filter by workspace if provided
            if workspace_id:
                # Need to ensure match_memories returns workspace_id.
                # If it doesn't, this will fail gracefully but return unfiltered data.
                data = [m for m in data if not m.get("workspace_id") or str(m.get("workspace_id")) == str(workspace_id)]

            return data[:limit]
        except Exception as e:
            print(f"[Memory] Error fetching semantic memories: {e}")
            return []

    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embeddings using Gemini text-embedding-004 via REST API.
        Produces 768-dim vectors matching the DB vector(768) column.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or "your_" in api_key.lower():
            return None

        import time
        import requests as _req
        max_retries = 3
        base_delay = 2
        # gemini-embedding-001 is the available model via v1beta
        # outputDimensionality=768 uses Matryoshka scaling to match DB vector(768)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={api_key}"

        for attempt in range(max_retries):
            try:
                resp = _req.post(url, json={
                    "content": {"parts": [{"text": text}]},
                    "taskType": "RETRIEVAL_DOCUMENT",
                    "outputDimensionality": 768,
                }, timeout=30)
                resp.raise_for_status()
                return resp.json()["embedding"]["values"]
            except Exception as e:
                print(f"[Memory] Embedding attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(base_delay * (2 ** attempt))
                else:
                    print(f"[Memory] Fatal: Failed after {max_retries} attempts.")
                    return None

    def save_memory(self, category: str, title: str, content: str, importance: int = 3,
                    tags: Optional[List[str]] = None, workspace_id: Optional[str] = None):
        """Save a new memory to Supabase. Embedding is best-effort — memory saves even if embedding fails."""
        embedding = self._generate_embedding(content)
        row: Dict[str, Any] = {
            "category": category,
            "title": title,
            "content": content,
            "importance": importance,
            "tags": tags or [],
            "workspace_id": workspace_id,
            "source": "conversation",
        }
        if embedding is not None:
            row["embedding"] = embedding
        try:
            self.db.table("aisha_memory").insert(row).execute()
            print(f"[Memory] Saved: [{category}] {title}")
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

    def save_conversation(self, role: str, message: str, platform: str = "telegram",
                          language: str = "English", mood: str = "casual",
                          user_id: Optional[int] = None, workspace_id: Optional[str] = None):
        """Log conversation turn to Supabase.

        Args:
            user_id: When provided and not None, the row is tagged with
                     ``guest_user_id`` so guest conversations are stored
                     separately and never surface in Ajay's warm-start query.
                     Pass ``None`` (default) for owner/system turns.
        """
        try:
            row: Dict[str, Any] = {
                "platform": platform,
                "role": role,
                "message": message,
                "language": language,
                "mood_detected": mood,
                "workspace_id": workspace_id,
            }
            if user_id is not None:
                row["guest_user_id"] = user_id
            self.db.table("aisha_conversations").insert(row).execute()
        except Exception as e:
            print(f"[Memory] Error saving conversation: {e}")

    def get_recent_conversation(self, limit: int = 10,
                                user_id: Optional[int] = None,
                                workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent conversation history for context continuity.

        When ``user_id`` is None (default), only owner turns are returned
        (rows where ``guest_user_id`` is NULL).  This prevents guest messages
        from polluting the owner warm-start.
        """
        try:
            query = (
                self.db.table("aisha_conversations")
                .select("role, message, created_at, workspace_id")
            )
            if user_id is None:
                # Owner warm-start: exclude guest-tagged rows
                query = query.is_("guest_user_id", "null")
            else:
                query = query.eq("guest_user_id", user_id)

            if workspace_id:
                query = query.eq("workspace_id", workspace_id)

            res = (
                query
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return list(reversed(res.data or []))
        except Exception as e:
            print(f"[Memory] Error loading conversation: {e}")
            return []

    # ── Context Loader ─────────────────────────────────────────

    def load_context(self, user_message: str = "", workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """Load full context from Supabase for Aisha's system prompt."""
        try:
            profile = self.get_profile()

            # Combine top static memories and semantic memories
            memories_list = self.get_top_memories(limit=5, workspace_id=workspace_id)

            # If user message is provided, fetch 3 semantic memories related to it
            if user_message:
                semantic_mems = self.get_semantic_memories(user_message, limit=3, workspace_id=workspace_id)
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
            tasks_query = (
                self.db.table("aisha_schedule")
                .select("title, priority")
                .eq("due_date", today)
                .eq("status", "pending")
            )
            if workspace_id:
                tasks_query = tasks_query.eq("workspace_id", workspace_id)

            tasks_res = tasks_query.execute()
            tasks_text = "\n".join(
                f"- [{t['priority'].upper()}] {t['title']}"
                for t in (tasks_res.data or [])
            ) or "No tasks for today"

            # Get today's expenses (from aisha_finance, date-filtered to today)
            today_expenses_text = "No expenses logged today"
            try:
                exp_query = (
                    self.db.table("aisha_finance")
                    .select("amount, category, description, date")
                    .eq("type", "expense")
                    .eq("date", today)
                )
                if workspace_id:
                    exp_query = exp_query.eq("workspace_id", workspace_id)

                exp_res = exp_query.order("id", desc=True).limit(20).execute()
                if exp_res.data:
                    total = sum(r.get("amount", 0) for r in exp_res.data)
                    lines = [
                        f"  ₹{r['amount']} — {r.get('description','?')} ({r.get('category','misc')})"
                        for r in exp_res.data
                    ]
                    today_expenses_text = f"Total today: ₹{total:.0f}\n" + "\n".join(lines)
            except Exception:
                pass

            return {
                "profile": profile,
                "memories": memories_text,
                "today_tasks": tasks_text,
                "today_expenses": today_expenses_text,
            }
        except Exception as e:
            print(f"[Memory] Error loading context: {e}")
            return {}

    def get_today_tasks(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get today's pending tasks."""
        try:
            today = datetime.now().date().isoformat()
            query = (
                self.db.table("aisha_schedule")
                .select("*")
                .eq("due_date", today)
                .eq("status", "pending")
            )
            if workspace_id:
                query = query.eq("workspace_id", workspace_id)
            res = query.execute()
            return res.data or []
        except Exception as e:
            print(f"[Memory] Error fetching today's tasks: {e}")
            return []
