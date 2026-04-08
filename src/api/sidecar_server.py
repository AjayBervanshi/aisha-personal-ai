import logging
from typing import Dict, Any, Optional, List
import os
from supabase import create_client

log = logging.getLogger(__name__)

class SidecarManager:
    """
    Manages connections from local Sidecar instances using Supabase as a message broker.
    Allows Aisha's cloud brain to send commands to a local laptop.
    """
    def __init__(self):
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        try:
            self.supabase = create_client(url, key)
        except Exception:
            self.supabase = None

    def dispatch_command(self, sidecar_id: str, command_type: str, payload: dict) -> Optional[str]:
        """Aisha calls this to send a command to the laptop."""
        if not self.supabase:
            return None

        try:
            res = self.supabase.table("sidecar_commands").insert({
                "sidecar_id": sidecar_id,
                "command_type": command_type,
                "payload": payload,
                "status": "pending"
            }).execute()

            if res.data:
                task_id = res.data[0]["id"]
                log.info(f"[Sidecar] Dispatched task {task_id} to {sidecar_id}")
                return task_id
        except Exception as e:
            log.error(f"[Sidecar] Failed to dispatch command: {e}")
        return None

    def get_result(self, task_id: str) -> Optional[dict]:
        """Aisha checks this to see if the laptop finished the task."""
        if not self.supabase: return None
        try:
            res = self.supabase.table("sidecar_commands").select("status, result").eq("id", task_id).execute()
            if res.data and res.data[0]["status"] in ["completed", "failed"]:
                return res.data[0]["result"]
        except Exception as e:
            log.error(f"[Sidecar] Failed to get result: {e}")
        return None

sidecar_manager = SidecarManager()
