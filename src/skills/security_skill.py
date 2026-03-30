import logging
import os
import requests
import json
from src.skills.skill_registry import aisha_skill

log = logging.getLogger("Aisha.Skills.Security")

@aisha_skill
def ask_ajay_for_permission(guest_name: str, request_description: str, guest_id: int = 0) -> str:
    """
    CRITICAL SECURITY SKILL: When a guest asks you to do something that might be restricted (like checking Ajay's calendar, writing code, or generating a video), CALL THIS FIRST to ask Ajay for permission.
    Provide the guest's name and exactly what they are asking you to do.
    You MUST wait for this tool to return 'APPROVED' or 'DENIED' before proceeding with their request.
    """
    from supabase import create_client

    try:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        if not url or not key:
            return "Error: Database credentials missing."

        sb = create_client(url, key)

        # 1. Log the request in the DB
        res = sb.table("aisha_guest_requests").insert({
            "guest_name": guest_name,
            "guest_telegram_id": guest_id,
            "request_description": request_description,
            "status": "pending"
        }).execute()

        if not res.data:
            return "Error: Could not save the request."

        req_id = res.data[0]["id"]

        # 2. Ping Ajay on Telegram
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        ajay_id = os.getenv("AJAY_TELEGRAM_ID")

        if not bot_token or not ajay_id:
            return "Error: Telegram credentials missing. Tell the guest you can't reach Ajay right now."

        tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        msg = (
            f"⚠️ **Guest Request Alert** ⚠️\n\n"
            f"**{guest_name}** wants me to do something:\n"
            f"_{request_description}_\n\n"
            f"Should I allow this?"
        )

        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Approve", "callback_data": f"approve_req_{req_id}"},
                    {"text": "❌ Deny", "callback_data": f"deny_req_{req_id}"}
                ]
            ]
        }

        req = requests.post(tg_url, json={
            "chat_id": ajay_id,
            "text": msg,
            "parse_mode": "Markdown",
            "reply_markup": json.dumps(keyboard)
        }, timeout=10)
        req.raise_for_status()

        # 3. We use long-polling here to wait for Ajay's response, because the LLM needs to know NOW.
        # We will poll the DB for up to 60 seconds.
        import time
        for _ in range(12): # 12 * 5s = 60s
            time.sleep(5)
            check_res = sb.table("aisha_guest_requests").select("status").eq("id", req_id).execute()
            if check_res.data:
                status = check_res.data[0]["status"]
                if status == "approved":
                    return "APPROVED: Ajay said yes! You may now fulfill the guest's request."
                elif status == "denied":
                    return "DENIED: Ajay said no. You must politely tell the guest that Ajay did not approve."

        # Timeout
        return "TIMEOUT: Ajay didn't respond in time. Tell the guest to try again later."

    except Exception as e:
        log.error(f"Failed to ask permission: {e}")
        return f"Error: Could not reach Ajay. ({e})"
