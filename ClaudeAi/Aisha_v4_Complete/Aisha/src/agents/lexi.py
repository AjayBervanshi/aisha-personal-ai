"""
lexi.py — Script Writer Agent
==============================
Lexi writes complete YouTube video scripts based on Riya's research.
She structures scripts professionally with timing markers,
hooks, transitions, and calls-to-action.
"""

from src.agents.base_agent import BaseAgent


class LexiAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name="Lexi",
            role="Professional YouTube Scriptwriter",
            personality="""You are Lexi, an elite YouTube scriptwriter with 10+ years experience.
You write scripts that are:
- Engaging from the FIRST sentence
- Structured with clear timing
- Conversational but informative
- Optimized for Indian audiences
- Designed to maximize watch time and retention

You use these markers in scripts:
[HOOK] - Opening hook section
[PAUSE] - Natural pause for audio
[EMPHASIS] - Word to emphasize in voice
[B-ROLL: description] - Video footage suggestion
[MUSIC: mood] - Background music suggestion
[TRANSITION] - Scene change
[CTA] - Call to action

Format: Always include timestamps (0:00, 0:30, 1:00 etc.)"""
        )

    def run_task(self, job_id: str, input_data: dict) -> str:
        """Write a complete script based on research."""
        self._update_job_status(job_id, "scripting")

        topic    = input_data.get("topic", "")
        research = input_data.get("findings", "")
        keywords = input_data.get("keywords", [])
        version  = input_data.get("version", 1)
        feedback = input_data.get("feedback", "")  # For revisions

        if feedback and version > 1:
            script = self._revise_script(topic, research, feedback, version)
        else:
            script = self._write_script(topic, research, keywords)

        # Save to Supabase
        word_count = len(script.split())
        duration_s = int((word_count / 130) * 60)  # ~130 words/min speaking pace

        self._save_output(job_id, "yt_scripts", {
            "version":    version,
            "content":    script,
            "word_count": word_count,
            "duration_s": duration_s,
            "status":     "draft"
        })

        self.log.info(f"[Lexi] Script v{version}: {word_count} words (~{duration_s//60}min)")
        return script

    def _write_script(self, topic: str, research: str, keywords: list) -> str:
        keywords_str = ", ".join(keywords[:8])
        prompt = f"""Write a complete, engaging YouTube video script about: "{topic}"

Research brief:
{research[:2000]}

SEO keywords to naturally include: {keywords_str}

Script requirements:
- LENGTH: 5-8 minutes (650-1000 words)
- HOOK: First 15 seconds must grab attention immediately
- STRUCTURE: Hook → Intro → 3-5 main points → Conclusion → CTA
- TONE: Friendly, conversational, knowledgeable — like a smart friend
- AUDIENCE: Indian viewers, English with occasional Hindi phrases OK
- Add [B-ROLL: suggestion] notes for video editor (Vex agent)
- Add [MUSIC: mood] notes for audio feel
- End with clear subscribe/like CTA

Start writing the COMPLETE script from [HOOK] now:"""

        return self.think(prompt, max_tokens=3000)

    def _revise_script(self, topic: str, research: str, feedback: str, version: int) -> str:
        prompt = f"""You previously wrote a YouTube script about "{topic}".
The quality reviewer gave this feedback:

FEEDBACK:
{feedback}

Research (for reference):
{research[:1000]}

Please write a COMPLETELY REVISED script addressing ALL the feedback points.
This is version {version} — it must be significantly better than the previous version.
Apply every single piece of feedback.

Write the COMPLETE revised script now:"""

        return self.think(prompt, max_tokens=3000)
