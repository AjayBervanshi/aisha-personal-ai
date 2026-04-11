import logging
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

log = logging.getLogger(__name__)

class WorkflowSuggester:
    """
    JARVIS Phase 4 (Feature 4.4): Workflow Auto-Suggestions.
    Analyzes daily screen activity (awareness logs) to detect repetitive patterns
    and automatically generates NLP Workflow DAGs to automate them.
    """
    def __init__(self, supabase_client, ai_router):
        self.supabase = supabase_client
        self.ai = ai_router

    def analyze_daily_patterns(self) -> Optional[List[Dict[str, Any]]]:
        """
        Fetches the last 24 hours of awareness logs and runs an LLM heuristic to detect
        repetitive behavior patterns (e.g., opening a specific website at the same time).
        """
        if not self.supabase:
            return None

        try:
            one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)

            # Fetch recent logs
            logs_res = self.supabase.table("aisha_awareness_logs")\
                .select("active_window, created_at")\
                .eq("sidecar_id", "local-laptop")\
                .gte("created_at", one_day_ago.isoformat())\
                .order("created_at", desc=False)\
                .execute()

            if not logs_res.data or len(logs_res.data) < 10:
                # Not enough data to find patterns
                return None

            # Compile a highly condensed timeline of window switches
            condensed_timeline = []
            last_win = ""
            for log_entry in logs_res.data:
                win = log_entry.get('active_window', 'Unknown')
                if win != last_win:
                    ts = log_entry['created_at'].split('.')[0]
                    condensed_timeline.append(f"[{ts}] {win}")
                    last_win = win

            timeline_str = "\n".join(condensed_timeline)

            # LLM Analysis for Patterns
            analysis_prompt = f"""
            Analyze this 24-hour timeline of Ajay's active application windows:

            {timeline_str}

            Detect any highly repetitive, predictable patterns that could be automated.
            (e.g., Opening HackerNews at 9am, or checking Email every 2 hours).

            Return ONLY a valid JSON array of suggested automations with no backticks:
            [
                {{
                    "pattern_detected": "Describe the repetitive behavior",
                    "suggested_workflow_nlp": "A natural language command Aisha can use to build a workflow (e.g., 'Every morning at 9am, open HackerNews and summarize the top 5 posts via Telegram.')",
                    "proactive_message": "A natural, empathetic message Aisha should send him on Telegram to ask if he wants to turn this automation on."
                }}
            ]
            If no strong patterns are found, return an empty array [].
            """

            result = self.ai.generate(
                system_prompt="You are a strict JSON data parser analyzing user behavior for automation opportunities.",
                user_message=analysis_prompt
            )

            match = re.search(r'\[.*\]', result.text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                return data

        except Exception as e:
            log.error(f"Workflow Auto-Suggest Error: {e}")

        return None
