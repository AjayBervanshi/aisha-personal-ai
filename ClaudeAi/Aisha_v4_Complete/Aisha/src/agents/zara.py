"""
zara.py — Quality Reviewer Agent
==================================
Zara reviews every script before it proceeds to audio/video production.
She checks: hook quality, structure, accuracy, tone, engagement.
Returns: approved=True/False + specific feedback for revision.
"""

import re
from src.agents.base_agent import BaseAgent


class ZaraAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name="Zara",
            role="Senior YouTube Content Quality Reviewer",
            personality="""You are Zara, a strict but fair YouTube quality reviewer.
You have reviewed thousands of viral YouTube videos and know exactly what works.
You REJECT scripts that are:
- Generic or boring (no unique hook)
- Too long or too short (under 400 or over 1500 words)
- Factually questionable without caveats
- Poorly structured
- Missing a strong CTA

You APPROVE scripts that:
- Have a genuinely compelling hook
- Flow naturally when spoken aloud
- Will keep viewers watching till the end
- Include proper B-roll suggestions
- End with an effective CTA

Be SPECIFIC in your feedback — not vague."""
        )

    def run_task(self, job_id: str, script: str) -> dict:
        """Review a script. Returns {approved, feedback, score}"""
        result = self.think_structured(
            f"""Review this YouTube script for quality:

---SCRIPT START---
{script[:3000]}
---SCRIPT END---

Score each category 1-10 and give your verdict:

Return ONLY this JSON:
{{
  "approved": true or false,
  "score": 0-100,
  "hook_score": 0-10,
  "structure_score": 0-10,
  "engagement_score": 0-10,
  "cta_score": 0-10,
  "feedback": "Specific detailed feedback for the writer",
  "fixes_needed": ["fix 1", "fix 2", "fix 3"]
}}

APPROVE if total score >= 70. REJECT if below 70."""
        )

        approved = result.get("approved", False)
        score    = result.get("score", 50)

        # Update script status in DB
        try:
            from src.agents.base_agent import get_db
            db = get_db()
            db.table("yt_scripts").update({
                "status":          "approved" if approved else "rejected",
                "reviewer_notes":  result.get("feedback", "")
            }).eq("job_id", str(job_id)).eq("status", "draft").execute()
        except Exception:
            pass

        self.log.info(f"[Zara] Review: {'✅ APPROVED' if approved else '❌ REJECTED'} (score: {score})")
        return result
