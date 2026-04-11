import re
import logging
from typing import Optional
from src.skills.skill_registry import aisha_skill

log = logging.getLogger(__name__)

@aisha_skill
def dispatch_to_sidecar(user_message: str, is_owner: bool) -> Optional[str]:
    """
    JARVIS Phase 2 & 4: Routes OS-level intents (Terminal, Desktop, Browser, Filesystem, Workflows)
    to the Supabase command queue for the local laptop to execute.
    """
    if not is_owner:
        return "*(Guest mode: OS-level commands and automations are disabled for your safety.)*"

    try:
        from src.api.sidecar_server import sidecar_manager

        target_sidecar = "local-laptop"
        action = None
        args = {}
        command_type = None

        # 1. Desktop Automation
        desktop_triggers = ["what windows", "focus on", "type this"]
        if any(t in user_message.lower() for t in desktop_triggers):
            command_type = "desktop_action"
            action = "list_windows"
            if "focus" in user_message.lower():
                action = "focus_window"
                args = {"title": user_message.split("focus on")[-1].strip()}
            elif "type" in user_message.lower():
                action = "type_text"
                args = {"text": user_message.split("type")[-1].strip()}

        # 2. Browser Automation
        elif any(t in user_message.lower() for t in ["open website", "go to", "read page", "what tabs"]):
            command_type = "browser_action"
            action = "navigate"
            if "what tabs" in user_message.lower():
                action = "list_tabs"
            elif "read page" in user_message.lower():
                action = "extract_text"
            else:
                words = user_message.split()
                url = next((w for w in words if "http" in w or ".com" in w), "https://google.com")
                args = {"url": url}

        # 3. Filesystem Automation
        elif any(t in user_message.lower() for t in ["read my file", "write to file", "what's in my folder", "list directory"]):
            command_type = "fs_action"
            action = "list_dir"
            if "read" in user_message.lower() or "cat" in user_message.lower():
                action = "read_file"
                args = {"path": user_message.split()[-1].strip()}
            elif "write" in user_message.lower():
                action = "write_file"
                args = {"path": "output.txt", "content": user_message}
            else:
                args = {"path": user_message.split()[-1].strip() if len(user_message.split()) > 3 else "."}

        # 4. Raw Shell Commands
        elif any(t in user_message.lower() for t in ["on my laptop", "run command", "on my computer"]):
            from src.core.ai_router import AIRouter
            ai = AIRouter()
            intent_prompt = f"The user wants to execute a command on their local laptop. Request: {user_message}\\nIf you understand the exact terminal command, reply with ONLY the command. Else reply NONE."
            cmd_result = ai.generate(system_prompt="You are a strict command translator.", user_message=intent_prompt)
            if cmd_result and cmd_result.text.strip() != "NONE":
                command_type = "shell_exec"
                action = "shell"
                args = {"command": cmd_result.text.strip()}

        if command_type and action:
            task_id = sidecar_manager.dispatch_command(
                sidecar_id=target_sidecar,
                command_type=command_type,
                payload={"action": action, "args": args, "command": args.get("command", "")}
            )
            if task_id:
                # We inject her persona into the confirmation!
                return f"Got it, Ajju! 💜 I've dispatched that `{command_type}` action to your laptop's sidecar right now. I'll let you know when it finishes executing!"

    except Exception as e:
        log.error(f"[Sidecar Skill] Failed to dispatch: {e}")
        return f"Uh oh, Ajju, my connection to your laptop sidecar hit a snag: {e} 😅"

    return None
