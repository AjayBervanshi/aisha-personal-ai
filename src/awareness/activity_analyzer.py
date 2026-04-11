import logging
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

log = logging.getLogger(__name__)

class ActivityAnalyzer:
    """
    JARVIS Phase 3 (Feature 3.2): Activity & Struggle Detection.
    Periodically analyzes the latest awareness logs from the Sidecar to infer what the user
    is doing and if they are struggling with a task (e.g., staring at an error).
    """
    def __init__(self, supabase_client, ai_router):
        self.supabase = supabase_client
        self.ai = ai_router

    def analyze_recent_activity(self) -> Optional[Dict[str, Any]]:
        """
        Fetches the last 5 minutes of awareness logs and runs an LLM heuristic to determine
        the user's primary activity and if they are struggling.
        """
        if not self.supabase:
            return None

        try:
            five_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=5)

            # Fetch recent logs
            logs_res = self.supabase.table("aisha_awareness_logs")\
                .select("active_window, screen_text, created_at")\
                .eq("sidecar_id", "local-laptop")\
                .gte("created_at", five_mins_ago.isoformat())\
                .order("created_at", desc=False)\
                .execute()

            if not logs_res.data or len(logs_res.data) < 2:
                # Not enough data to determine a struggle
                return None

            # Compile context
            context_timeline = "Recent Screen Activity Timeline:\n"
            for log_entry in logs_res.data:
                ts = log_entry['created_at'].split('.')[0]
                win = log_entry.get('active_window', 'Unknown')
                text = log_entry.get('screen_text', '')[:200] # Snippet
                context_timeline += f"[{ts}] Window: {win} | Snippet: {text}...\n"

            # LLM Analysis
            analysis_prompt = f"Analyze this 5-minute timeline of Ajay's screen activity:\n\n{context_timeline}\n\nDetermine:\n1. The primary activity (e.g., 'Coding', 'Watching YouTube', 'Writing Email').\n2. Is Ajay struggling or stuck? (e.g., repeatedly looking at an error log, failing builds, or searching for the same bug over and over).\n\nReturn ONLY a valid JSON object with no backticks:\n{{\n    \"activity\": \"String describing the activity\",\n    \"is_struggling\": true/false,\n    \"struggle_reason\": \"If true, explain exactly what the error or problem is\",\n    \"proactive_suggestion\": \"If true, a natural, empathetic 1-sentence message Aisha should send him on Telegram to offer help.\"\n}}"

            result = self.ai.generate(
                system_prompt="You are a strict JSON data parser analyzing user behavior.",
                user_message=analysis_prompt
            )

            match = re.search(r'\{.*\}', result.text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                return data

        except Exception as e:
            log.error(f"Activity Analysis Error: {e}")

        return None
