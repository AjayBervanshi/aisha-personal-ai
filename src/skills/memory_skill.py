import logging
from src.skills.skill_registry import aisha_skill

log = logging.getLogger("Aisha.Skills.Memory")

@aisha_skill
def learn_new_rule(rule_description: str, reason: str = "") -> str:
    """
    CRITICAL SKILL: If Ajay corrects you, scolds you for a mistake, or explicitly tells you a new rule about how you should behave, CALL THIS IMMEDIATELY to learn it forever.
    Provide a clear, concise rule description.
    """
    from src.core.aisha_brain import MemoryManager
    from src.core.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
    from supabase import create_client

    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        mm = MemoryManager(sb)

        # Save it as an ultra-high importance rule memory
        title = "BEHAVIORAL RULE"
        content = f"RULE: {rule_description}. REASON: {reason}"

        # Save to semantic memory
        mm.save_memory(
            category="rule",
            title=title,
            content=content,
            importance=5, # Highest importance
            tags=["core-directive", "self-learning", "correction"]
        )

        log.info(f"Learned new rule: {rule_description}")
        return f"Successfully committed new behavioral rule to core memory: {rule_description}"

    except Exception as e:
        log.error(f"Failed to learn rule: {e}")
        return f"Error committing rule to memory: {e}"

@aisha_skill
def memorize_fact(fact: str, context: str = "") -> str:
    """
    If Ajay tells you a specific fact, piece of data, or preference that you MUST remember for later, CALL THIS to save it explicitly to your semantic database immediately.
    """
    from src.core.aisha_brain import MemoryManager
    from src.core.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
    from supabase import create_client

    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        mm = MemoryManager(sb)

        mm.save_memory(
            category="preference",
            title="EXPLICIT FACT",
            content=f"FACT: {fact}. CONTEXT: {context}",
            importance=4,
            tags=["explicit-fact", "preference"]
        )

        log.info(f"Memorized fact: {fact}")
        return f"Successfully memorized fact: {fact}"

    except Exception as e:
        log.error(f"Failed to memorize fact: {e}")
        return f"Error committing fact to memory: {e}"
