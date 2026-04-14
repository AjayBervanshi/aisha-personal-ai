import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

log = logging.getLogger(__name__)

class GoalEngine:
    """
    JARVIS Phase 4 (Feature 4.1): OKR Goal Engine.
    Parses user goals into Objectives, Key Results, and Daily Actions.
    Evaluates progress autonomously using continuous awareness logs.
    """
    def __init__(self, supabase_client, ai_router):
        self.supabase = supabase_client
        self.ai = ai_router

    def parse_new_goal(self, user_message: str) -> Optional[str]:
        """Uses LLM to break down a high-level goal into an OKR schema and save to DB."""
        if not self.supabase:
            return None

        prompt = f"""
        Ajay wants to start a new goal: "{user_message}"

        Break this down into an OKR (Objective, Key Results, Daily Actions) format.
        Return ONLY valid JSON with no backticks:
        {{
            "objective": "The overarching goal title",
            "deadline_days": 30, // Approximate days if unspecified
            "key_results": [
                {{
                    "title": "Measurable milestone",
                    "target_value": 100, // e.g., 5 for "Run 5k", or 1.0 for binary completion
                    "unit": "e.g., kg, km, completion",
                    "daily_actions": ["Specific habit 1", "Specific habit 2"]
                }}
            ]
        }}
        """

        try:
            result = self.ai.generate(
                system_prompt="You are a strict JSON data parser mapping goals to OKRs.",
                user_message=prompt
            )

            match = re.search(r'\{.*\}', result.text, re.DOTALL)
            if not match:
                return None

            data = json.loads(match.group(0))

            # Save to Database
            deadline = datetime.now(timezone.utc) + timedelta(days=data.get("deadline_days", 30))
            obj_res = self.supabase.table("aisha_objectives").insert({
                "title": data["objective"],
                "deadline": deadline.isoformat()
            }).execute()

            obj_id = obj_res.data[0]["id"]

            for kr in data.get("key_results", []):
                kr_res = self.supabase.table("aisha_key_results").insert({
                    "objective_id": obj_id,
                    "title": kr["title"],
                    "target_value": kr.get("target_value", 1.0),
                    "unit": kr.get("unit", "completion")
                }).execute()
                kr_id = kr_res.data[0]["id"]

                for act in kr.get("daily_actions", []):
                    self.supabase.table("aisha_daily_actions").insert({
                        "key_result_id": kr_id,
                        "title": act
                    }).execute()

            # Return a natural language summary to the user
            summary = f"🎯 *Objective Set:* {data['objective']}\n"
            for kr in data.get("key_results", []):
                summary += f"  - *KR:* {kr['title']}\n"
                for act in kr.get("daily_actions", []):
                    summary += f"    • {act} (Daily)\n"
            return summary

        except Exception as e:
            log.error(f"Goal Engine Parsing Error: {e}")
            return None

    def evening_review(self) -> str:
        """
        Runs during the evening check-in. Evaluates if Ajay did his daily actions
        by searching his awareness logs for proof. Escalates if falling behind.
        """
        if not self.supabase:
            return ""

        try:
            # 1. Fetch active daily actions
            actions_res = self.supabase.table("aisha_daily_actions")\
                .select("id, title, last_completed_at, key_result_id(title, objective_id(title))")\
                .execute()

            if not actions_res.data:
                return ""

            # 2. Fetch today's awareness logs
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
            logs_res = self.supabase.table("aisha_awareness_logs")\
                .select("active_window, screen_text")\
                .gte("created_at", today_start.isoformat())\
                .execute()

            # 3. Ask LLM to grade performance based on awareness evidence
            awareness_dump = "\\n".join([f"App: {l['active_window']} Text: {str(l['screen_text'])[:100]}" for l in logs_res.data])

            actions_dump = "\\n".join([f"ID: {a['id']}, Action: {a['title']}" for a in actions_res.data])

            prompt = f"""
            Ajay's Daily Habits/Actions:
            {actions_dump}

            Today's Laptop Screen Awareness Log (Sample):
            {awareness_dump[:3000]} # Trimmed to save tokens

            Did Ajay likely complete any of his habits today based on his screen activity?
            Return JSON:
            {{
                "completed_action_ids": ["uuid1", "uuid2"],
                "drill_sergeant_message": "A strict, motivating message if he missed things, or praise if he did them."
            }}
            """

            result = self.ai.generate(
                system_prompt="You are a strict JSON parser acting as a performance coach.",
                user_message=prompt
            )

            match = re.search(r'\{.*\}', result.text, re.DOTALL)
            if not match:
                return ""

            data = json.loads(match.group(0))

            # Update DB for completed actions
            completed_ids = data.get("completed_action_ids", [])
            if isinstance(completed_ids, list) and completed_ids:
                # Deduplicate and filter out empty values to ensure clean batching
                unique_ids = list(set(str(a_id) for a_id in completed_ids if a_id))
                now_iso = datetime.now(timezone.utc).isoformat()
                for i in range(0, len(unique_ids), 100):
                    batch = unique_ids[i:i+100]
                    self.supabase.table("aisha_daily_actions")\
                        .update({"last_completed_at": now_iso})\
                        .in_("id", batch)\
                        .execute()

            return data.get("drill_sergeant_message", "")

        except Exception as e:
            log.error(f"Evening Review Error: {e}")
            return ""
