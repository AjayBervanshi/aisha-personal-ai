import time
import logging
import traceback
import uuid
import os
import sys
import requests
from typing import Dict, Any

from src.core.queue_manager import queue_manager
from src.config import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("BackgroundWorker")

# Unique ID for this worker instance
WORKER_ID = f"worker-{uuid.uuid4().hex[:8]}"

def notify_telegram(chat_id: int, message: str):
    """Sends a stateless callback notification directly to Telegram API."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN") or config.TELEGRAM_BOT_TOKEN
    if not bot_token or not chat_id:
        log.error("Missing TELEGRAM_BOT_TOKEN or chat_id. Cannot send notification.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        log.error(f"Failed to send Telegram notification: {e}")

def process_video_job(job: Dict[str, Any]):
    """Handler for the 'create_video' intent."""
    job_id = job.get("id")
    topic = job.get("payload", {}).get("topic", "General AI Trend")
    chat_id = job.get("chat_id")
    
    # Idempotency check
    if job.get("result") and job.get("result") != {}:
        log.info(f"[JOB:{job_id}] Skipping already processed job.")
        return
        
    log.info(f"[JOB:{job_id}] Starting video generation for topic: {topic}")
    
    # Send a warm-up message
    if chat_id:
         notify_telegram(chat_id, "<i>🎬 Aisha Background Worker spinning up FFmpeg engines...</i>")
         
    try:
        # Corrected import path based on repo topology
        from src.agents.youtube_crew import YouTubeCrew
        crew = YouTubeCrew(topic=topic)
        final_video_path = crew.run()
        
        # If run() successfully returns a path, the job is a success.
        if final_video_path and os.path.exists(final_video_path):
             log.info(f"[JOB:{job_id}] Video generation successful: {final_video_path}")
             queue_manager.mark_job_completed(job_id, {"video_path": final_video_path})
             if chat_id:
                 notify_telegram(chat_id, f"✅ <b>Video Render Complete!</b>\n\nYour video is ready on the server at:\n<code>{final_video_path}</code>\n\nIt has been added to the drip-feed Queue!")
        else:
             raise Exception("YouTubeCrew completed but returned an invalid or empty video path.")
             
    except Exception as e:
        error_trace = traceback.format_exc()
        log.error(f"[JOB:{job_id}] Video generation failed: {error_trace}")
        queue_manager.mark_job_failed(job_id, str(e))
        if chat_id:
             notify_telegram(chat_id, f"⚠️ <b>Render Failed!</b>\n\nA background worker encountered an error:\n<code>{str(e)[:150]}</code>\n\nI'll automatically retry if under the limit!")

def run_worker_loop():
    """Continuous polling loop."""
    log.info(f"🚀 {WORKER_ID} Online. Listening for Render Jobs via Supabase SKIP LOCKED...")
    
    active_job_id = None
    
    try:
        while True:
            try:
                job = queue_manager.dequeue_job(WORKER_ID)
                
                if not job:
                    # Idle state: Dynamic backoff
                    time.sleep(3)
                    continue
                    
                active_job_id = job.get("id")
                intent = job.get("intent")
                log.info(f"[{WORKER_ID}] Picked up Job ID {active_job_id} | Intent: {intent}")

                # Enforce max runtime for worker loop sanity (Job level timeout is handled by RPC)
                start_time = time.time()
                MAX_RUNTIME = 600 # 10 minutes

                # Router based on intent
                if intent == "create_video":
                    process_video_job(job)
                else:
                    log.warning(f"[{WORKER_ID}] Unknown intent '{intent}'. Marking as failed.")
                    queue_manager.mark_job_failed(active_job_id, f"Unknown intent router: {intent}")
                
                active_job_id = None
                
                # Dynamic backoff (poll faster when busy)
                time.sleep(1)
                    
            except KeyboardInterrupt:
                log.info(f"[{WORKER_ID}] Shutting down gracefully...")
                if active_job_id:
                    queue_manager.mark_job_failed(active_job_id, "Worker interrupted during execution.")
                break
            except Exception as e:
                log.error(f"[{WORKER_ID}] Critical error in worker loop: {e}")
                if active_job_id:
                    queue_manager.mark_job_failed(active_job_id, str(e))
                    active_job_id = None
                time.sleep(5) # Backoff on critical error
    finally:
        log.info(f"[{WORKER_ID}] Worker process exited.")

if __name__ == "__main__":
    run_worker_loop()
