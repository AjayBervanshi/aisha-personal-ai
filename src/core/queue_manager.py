import os
import json
import logging
from typing import Optional, Dict, Any
from supabase import create_client, Client
from src.config import config

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class QueueManager:
    """
    Manages background jobs via Supabase Postgres using FOR UPDATE SKIP LOCKED.
    """
    def __init__(self):
        # We need the service role key to bypass RLS and perform queue operations reliably.
        # Fall back to config if environment variable isn't immediately available.
        supabase_url = os.environ.get("SUPABASE_URL") or config.SUPABASE_URL
        supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or config.get("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
             log.error("QueueManager initialized without Supabase Service Key. Will fail on DB operations.")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)

    def enqueue_job(self, intent: str, payload: Dict[str, Any], chat_id: Optional[int] = None) -> Optional[str]:
        """
        Inserts a new job into the queue.
        Returns the job UUID as a string if successful.
        """
        try:
            data = {
                "intent": intent,
                "payload": payload,
                "status": "pending",
                "chat_id": chat_id
            }
            response = self.supabase.table("render_jobs").insert(data).execute()
            if response.data and len(response.data) > 0:
                job_id = response.data[0].get('id')
                log.info(f"Enqueued job {job_id} for intent {intent}")
                return job_id
            return None
        except Exception as e:
            log.exception(f"Failed to enqueue job for {intent}: {e}")
            return None

    def dequeue_job(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """
        Atomically fetches and locks the next pending job.
        Implements FOR UPDATE SKIP LOCKED via Supabase RPC.
        """
        try:
            # Note: We must call a custom Postgres function to use SKIP LOCKED safely.
            response = self.supabase.rpc("dequeue_render_job", {"req_worker_id": worker_id}).execute()
            if response.data:
                job = response.data[0] if isinstance(response.data, list) else response.data
                log.info(f"Dequeued job {job.get('id')} for processing by {worker_id}.")
                return job
            return None
        except Exception as e:
            log.error(f"Failed to dequeue job: {e}")
            return None

    def mark_job_completed(self, job_id: str, result_payload: Optional[Dict[str, Any]] = None):
        """Marks a job as successfully completed."""
        try:
            update_data = {"status": "completed"}
            if result_payload:
                # Store result distinctly from input payload to prevent data overwrite
                update_data["result"] = result_payload 
                
            self.supabase.table("render_jobs").update(update_data).eq("id", job_id).execute()
            log.info(f"Job {job_id} marked as completed.")
        except Exception as e:
            log.exception(f"Failed to mark job {job_id} as completed: {e}")

    def mark_job_failed(self, job_id: str, error_msg: str):
        """Marks a job as failed, increments retry count."""
        try:
            # Fetch current to increment retry (PostgREST lacks direct increment on update)
            res = self.supabase.table("render_jobs").select("retry_count").eq("id", job_id).single().execute()
            current_retries = res.data.get("retry_count", 0) if res.data else 0
            
            new_status = "failed"
            # Hardcoded max retries for now
            if current_retries < 3:
                new_status = "pending" # Throw it back into the queue
                
            update_data = {
                "status": new_status,
                "retry_count": current_retries + 1,
                "last_error": str(error_msg)[:1000] # Truncate error
            }
            
            self.supabase.table("render_jobs").update(update_data).eq("id", job_id).execute()
            log.info(f"Job {job_id} marked as {new_status} (Retry {current_retries + 1}). Error: {error_msg}")
        except Exception as e:
            log.exception(f"Failed to update failure state for job {job_id}: {e}")

# Create a singleton instance
queue_manager = QueueManager()
