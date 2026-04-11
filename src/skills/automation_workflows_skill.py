import re
import logging
from typing import Optional
from src.skills.skill_registry import aisha_skill

log = logging.getLogger(__name__)

@aisha_skill
def parse_and_create_workflow(user_message: str, is_owner: bool) -> Optional[str]:
    """
    JARVIS Phase 4: Detects if Ajay wants to create a new background automation (Workflow)
    or set an OKR goal, translating natural language into the respective engines.
    """
    if not is_owner:
        return "*(Guest mode: Workflows and OKR Goal Tracking are disabled for your safety.)*"

    try:
        from src.core.workflow_engine import WorkflowEngine
        from src.core.goal_engine import GoalEngine
        from src.core.aisha_brain import AishaBrain

        # We need a db connection
        brain = AishaBrain()

        workflow_triggers = ["automate this", "every morning at", "every day", "create a workflow", "schedule a task"]
        goal_triggers = ["i want to achieve", "my goal is to", "set a goal to"]

        if any(t in user_message.lower() for t in workflow_triggers):
            engine = WorkflowEngine(brain.supabase, brain.ai)
            summary = engine.build_from_nl(user_message)
            if summary:
                # Add Aisha's personality to the confirmation!
                return f"You got it, Ajju! 💜 I've translated your idea into a background workflow graph in the database.\n\n{summary}"

        if any(t in user_message.lower() for t in goal_triggers):
            g_engine = GoalEngine(brain.supabase, brain.ai)
            summary = g_engine.parse_new_goal(user_message)
            if summary:
                # Add Aisha's personality to the confirmation!
                return f"Yes, let's do this, Ajju! 🔥 I've set up your new OKR goal in the system. I'll be tracking your progress daily!\n\n{summary}"

    except Exception as e:
        log.error(f"[Automation Skill] Error parsing: {e}")
        return f"Ajju, my workflow engine hit a snag while parsing your request: {e} 😅"

    return None
