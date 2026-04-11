"""
quality_crew.py
===============
Aisha's Quality Review Crew — a multi-agent review loop.

After content is produced (script + voice + thumbnail + video), this crew
runs a structured discussion where agents review, critique, and improve
the content until it meets release quality.

Agents:
  - Script Editor:    Checks script for human-likeness, emotional impact, flow
  - Visual Director:  Validates thumbnail matches script mood, checks image trends
  - SEO Analyst:      Reviews title/hashtags for discoverability and CTR
  - Quality Director: Final approval gate — coherence check across all assets

The crew runs in a discussion loop (max 2 rounds). Each round:
  1. Each agent reviews independently and provides scores + feedback
  2. If any agent scores below threshold, issues are collected
  3. The Script Editor rewrites / Visual Director regenerates as needed
  4. Final round: Quality Director gives APPROVE or REJECT

This prevents publishing low-quality or mismatched content.
"""

import logging
import os
from typing import Optional

from src.core.ai_router import AIRouter

log = logging.getLogger("Aisha.QualityCrew")

# Minimum scores (1-10) for each dimension. Below = needs revision.
QUALITY_THRESHOLDS = {
    "script_human_likeness": 7,
    "script_engagement": 7,
    "script_length": 6,
    "thumbnail_relevance": 6,
    "seo_quality": 6,
    "overall_coherence": 7,
}

MAX_REVIEW_ROUNDS = 2


class QualityReviewCrew:
    """Multi-agent quality review with discussion loop."""

    def __init__(self):
        self.ai = AIRouter()
        self.review_log = []

    def _ask(self, system: str, prompt: str) -> str:
        """Generate a response from an AI agent with a specific role."""
        result = self.ai.generate(system_prompt=system, user_message=prompt)
        return result.text.strip()

    def review_script(self, script: str, topic: str, channel: str) -> dict:
        """Script Editor reviews the narration script."""
        response = self._ask(
            system=(
                "तुम एक experienced Hindi content editor हो। तुम्हारा काम है script को review करना। "
                "तुम बहुत strict हो quality के बारे में — अगर script AI जैसा लगता है, "
                "boring है, या natural नहीं है, तो तुम clearly बताओगे।"
            ),
            prompt=f"""Review this Hindi narration script for a YouTube Short / Instagram Reel.
Topic: {topic}
Channel: {channel}

SCRIPT:
{script}

Rate each dimension (1-10) and explain briefly:

1. HUMAN_LIKENESS (does it sound like a real person talking, NOT like AI?)
   - Check: No generic AI phrases, no "इस कहानी में", no lecture tone
   - Check: Natural pauses (...), conversational flow, emotional authenticity
   
2. ENGAGEMENT (will viewers watch till the end?)
   - Check: Hook in first line, emotional peak in middle, twist/payoff at end
   - Check: Would YOU stop scrolling for this?

3. LENGTH (is it 150-250 words for 60-90 seconds?)
   - Count approximate words

4. DEVANAGARI_PURITY (100% Hindi Devanagari, zero English/Roman?)
   - Flag any English words or Roman characters

5. TTS_READINESS (will it sound good when spoken by voice AI?)
   - Check: Short sentences, no complex punctuation, natural rhythm

FORMAT YOUR RESPONSE EXACTLY LIKE:
HUMAN_LIKENESS: [score]/10 — [one line reason]
ENGAGEMENT: [score]/10 — [one line reason]
LENGTH: [score]/10 — [word count estimate]
DEVANAGARI: [score]/10 — [issues if any]
TTS_READY: [score]/10 — [issues if any]
VERDICT: PASS or NEEDS_REVISION
FEEDBACK: [specific actionable improvements if NEEDS_REVISION, else "Approved"]""",
        )
        self.review_log.append({"agent": "ScriptEditor", "response": response})
        return self._parse_review(response)

    def review_thumbnail(self, thumbnail_prompt: str, script_excerpt: str, topic: str) -> dict:
        """Visual Director reviews thumbnail concept against script and trends."""
        response = self._ask(
            system=(
                "You are a Visual Director for Indian YouTube content. You understand "
                "what thumbnails get clicks in the Hindi storytelling niche. You check "
                "if the visual matches the story mood and follows current design trends."
            ),
            prompt=f"""Review this thumbnail for a Hindi story YouTube Short.

TOPIC: {topic}
THUMBNAIL IMAGE PROMPT: {thumbnail_prompt}
SCRIPT EXCERPT: {script_excerpt[:400]}

Rate each dimension (1-10):

1. SCRIPT_MATCH (does the visual match the story's mood and theme?)
   - A romantic rain story should NOT have a sunny beach thumbnail
   
2. CLICK_APPEAL (would Indian viewers aged 18-35 click this?)
   - Check: Emotional face, dramatic lighting, curiosity element
   
3. TREND_ALIGNMENT (does it follow current YouTube Shorts thumbnail trends?)
   - Current trends: close-up emotional faces, warm/moody color grading,
     minimal text overlay, cinematic aspect ratio

4. TECHNICAL_QUALITY (prompt will produce a good image?)
   - Check: Specific enough for AI image gen, not too abstract

FORMAT YOUR RESPONSE EXACTLY LIKE:
SCRIPT_MATCH: [score]/10 — [reason]
CLICK_APPEAL: [score]/10 — [reason]
TREND_ALIGNMENT: [score]/10 — [reason]
TECHNICAL: [score]/10 — [reason]
VERDICT: PASS or NEEDS_REVISION
BETTER_PROMPT: [improved thumbnail prompt if NEEDS_REVISION, else "Original is fine"]""",
        )
        self.review_log.append({"agent": "VisualDirector", "response": response})
        return self._parse_review(response)

    def review_seo(self, marketing_text: str, script_excerpt: str, topic: str) -> dict:
        """SEO Analyst reviews title, description, hashtags for discoverability."""
        response = self._ask(
            system=(
                "You are a YouTube Shorts and Instagram Reels SEO expert specializing "
                "in Hindi content. You know exactly what titles get clicks, what hashtags "
                "trend, and what descriptions drive discovery in the Indian market."
            ),
            prompt=f"""Review this SEO package for a Hindi story Short/Reel.

TOPIC: {topic}
SEO PACKAGE:
{marketing_text}

SCRIPT EXCERPT: {script_excerpt[:300]}

Rate each dimension (1-10):

1. TITLE_CTR (will the title make people click?)
   - Must be emotional, curiosity-driven, Hindi, under 60 chars
   - Must include #shorts for YouTube

2. HASHTAG_QUALITY (right mix of trending + niche tags?)
   - Need: broad (#shorts #reels #viral) + niche (#hindistory #lovestory)
   - 15-20 hashtags total

3. DESCRIPTION_SEO (keywords for YouTube/Instagram search?)

4. CAPTION_HOOK (Instagram caption — emotional, scroll-stopping?)

FORMAT YOUR RESPONSE EXACTLY LIKE:
TITLE_CTR: [score]/10 — [reason]
HASHTAGS: [score]/10 — [reason]  
DESCRIPTION: [score]/10 — [reason]
CAPTION: [score]/10 — [reason]
VERDICT: PASS or NEEDS_REVISION
IMPROVED_TITLE: [better title if needed, else "Original is fine"]
IMPROVED_HASHTAGS: [better hashtags if needed, else "Original is fine"]""",
        )
        self.review_log.append({"agent": "SEOAnalyst", "response": response})
        return self._parse_review(response)

    def final_approval(self, script: str, marketing_text: str, thumbnail_prompt: str,
                       topic: str, voice_path: str, video_path: str,
                       review_history: list) -> dict:
        """Quality Director — final gate before publishing."""
        assets_status = []
        if voice_path and os.path.exists(voice_path):
            size_kb = os.path.getsize(voice_path) / 1024
            assets_status.append(f"Voice: {size_kb:.0f}KB")
        else:
            assets_status.append("Voice: MISSING")

        if video_path and os.path.exists(video_path):
            size_mb = os.path.getsize(video_path) / (1024 * 1024)
            assets_status.append(f"Video: {size_mb:.1f}MB")
        else:
            assets_status.append("Video: MISSING")

        previous_feedback = "\n".join(
            f"[{r.get('agent', '?')}] {r.get('response', '')[:200]}"
            for r in review_history[-6:]
        )

        response = self._ask(
            system=(
                "You are the Quality Director. You make the FINAL decision on whether "
                "content gets published. You are strict but fair. You check that everything "
                "is coherent: script matches thumbnail, voice matches script mood, SEO matches "
                "content. If anything is off, you REJECT."
            ),
            prompt=f"""FINAL QUALITY CHECK before publishing.

TOPIC: {topic}
SCRIPT (full): {script}
MARKETING/SEO: {marketing_text}
THUMBNAIL PROMPT: {thumbnail_prompt}
ASSETS: {', '.join(assets_status)}

PREVIOUS REVIEWS:
{previous_feedback}

Check:
1. Does the script tell a complete, compelling 60-90 second story?
2. Does the thumbnail prompt match the script's mood and setting?
3. Does the title accurately represent the content (no clickbait that doesn't match)?
4. Are all assets present (voice + video)?
5. Is everything coherent as a package?

FORMAT YOUR RESPONSE EXACTLY LIKE:
COHERENCE: [score]/10 — [does everything fit together?]
COMPLETENESS: [score]/10 — [all assets present and viable?]
PUBLISH_READY: [score]/10 — [overall readiness]
DECISION: APPROVE or REJECT
REASON: [one line explanation]
FIXES_NEEDED: [specific fixes if REJECT, else "None"]""",
        )
        self.review_log.append({"agent": "QualityDirector", "response": response})
        return self._parse_review(response)

    def _parse_review(self, text: str) -> dict:
        """Parse structured review response into a dict."""
        result = {"raw": text, "scores": {}, "verdict": "PASS", "feedback": ""}
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            # Parse score lines like "HUMAN_LIKENESS: 8/10 — looks natural"
            if "/10" in line and ":" in line:
                key_part = line.split(":")[0].strip().upper().replace(" ", "_")
                try:
                    score_part = line.split(":")[1].strip()
                    score = int(score_part.split("/")[0].strip())
                    result["scores"][key_part] = score
                except (ValueError, IndexError):
                    pass

            upper = line.upper()
            if upper.startswith("VERDICT:") or upper.startswith("DECISION:"):
                val = line.split(":", 1)[1].strip().upper()
                if "REJECT" in val or "NEEDS" in val or "REVISION" in val:
                    result["verdict"] = "NEEDS_REVISION"
                else:
                    result["verdict"] = "PASS"

            elif upper.startswith("FEEDBACK:") or upper.startswith("FIXES_NEEDED:"):
                result["feedback"] = line.split(":", 1)[1].strip()

            elif upper.startswith("BETTER_PROMPT:"):
                val = line.split(":", 1)[1].strip()
                if val.lower() not in ("original is fine", "none", ""):
                    result["better_prompt"] = val

            elif upper.startswith("IMPROVED_TITLE:"):
                val = line.split(":", 1)[1].strip()
                if val.lower() not in ("original is fine", "none", ""):
                    result["improved_title"] = val

            elif upper.startswith("IMPROVED_HASHTAGS:"):
                val = line.split(":", 1)[1].strip()
                if val.lower() not in ("original is fine", "none", ""):
                    result["improved_hashtags"] = val

            elif upper.startswith("REASON:"):
                if not result["feedback"]:
                    result["feedback"] = line.split(":", 1)[1].strip()

        return result

    def run_review_loop(
        self,
        script: str,
        marketing_text: str,
        thumbnail_prompt: str,
        topic: str,
        channel: str,
        voice_path: str = None,
        video_path: str = None,
        rewrite_callback=None,
        regen_thumbnail_callback=None,
    ) -> dict:
        """
        Run the full quality review loop.

        Args:
            script: The narration script
            marketing_text: SEO package text
            thumbnail_prompt: The prompt used for thumbnail generation
            topic: Content topic
            channel: YouTube channel name
            voice_path: Path to generated voice file
            video_path: Path to rendered video
            rewrite_callback: Function(script, feedback) -> new_script (optional)
            regen_thumbnail_callback: Function(new_prompt) -> new_thumb_path (optional)

        Returns:
            dict with:
                approved: bool
                final_script: str (possibly revised)
                final_marketing: str
                final_thumbnail_prompt: str
                review_rounds: int
                review_log: list of all agent reviews
        """
        current_script = script
        current_marketing = marketing_text
        current_thumbnail_prompt = thumbnail_prompt

        for round_num in range(1, MAX_REVIEW_ROUNDS + 1):
            log.info(f"[QualityCrew] Review round {round_num}/{MAX_REVIEW_ROUNDS}")
            needs_revision = False

            # 1. Script Editor reviews
            log.info("[QualityCrew] Script Editor reviewing...")
            script_review = self.review_script(current_script, topic, channel)
            log.info(f"[QualityCrew] Script verdict: {script_review['verdict']}")

            if script_review["verdict"] == "NEEDS_REVISION" and rewrite_callback and round_num < MAX_REVIEW_ROUNDS:
                log.info("[QualityCrew] Script needs revision — rewriting...")
                feedback = script_review.get("feedback", "Improve human-likeness and engagement")
                new_script = rewrite_callback(current_script, feedback)
                if new_script and len(new_script.strip()) > 50:
                    current_script = new_script
                    needs_revision = True

            # 2. Visual Director reviews thumbnail
            log.info("[QualityCrew] Visual Director reviewing thumbnail...")
            visual_review = self.review_thumbnail(current_thumbnail_prompt, current_script[:400], topic)
            log.info(f"[QualityCrew] Thumbnail verdict: {visual_review['verdict']}")

            if visual_review.get("better_prompt") and regen_thumbnail_callback and round_num < MAX_REVIEW_ROUNDS:
                log.info("[QualityCrew] Thumbnail needs revision — regenerating...")
                new_prompt = visual_review["better_prompt"]
                new_path = regen_thumbnail_callback(new_prompt)
                if new_path:
                    current_thumbnail_prompt = new_prompt
                    needs_revision = True

            # 3. SEO Analyst reviews marketing
            log.info("[QualityCrew] SEO Analyst reviewing...")
            seo_review = self.review_seo(current_marketing, current_script[:300], topic)
            log.info(f"[QualityCrew] SEO verdict: {seo_review['verdict']}")

            if seo_review.get("improved_title"):
                current_marketing = current_marketing.replace(
                    current_marketing.split("\n")[0],
                    f"TITLE: {seo_review['improved_title']}",
                    1,
                )

            # 4. Quality Director final check
            log.info("[QualityCrew] Quality Director doing final check...")
            final_review = self.final_approval(
                script=current_script,
                marketing_text=current_marketing,
                thumbnail_prompt=current_thumbnail_prompt,
                topic=topic,
                voice_path=voice_path,
                video_path=video_path,
                review_history=self.review_log,
            )
            log.info(f"[QualityCrew] Final decision: {final_review['verdict']}")

            if final_review["verdict"] == "PASS":
                log.info(f"[QualityCrew] APPROVED after {round_num} round(s)")
                return {
                    "approved": True,
                    "final_script": current_script,
                    "final_marketing": current_marketing,
                    "final_thumbnail_prompt": current_thumbnail_prompt,
                    "review_rounds": round_num,
                    "review_log": self.review_log,
                }

            if not needs_revision:
                break

        log.warning(f"[QualityCrew] Content not fully approved after {MAX_REVIEW_ROUNDS} rounds — publishing with best version")
        return {
            "approved": False,
            "final_script": current_script,
            "final_marketing": current_marketing,
            "final_thumbnail_prompt": current_thumbnail_prompt,
            "review_rounds": MAX_REVIEW_ROUNDS,
            "review_log": self.review_log,
        }
