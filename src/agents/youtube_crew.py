"""
youtube_crew.py
==============
Aisha's Content Production Engine.
Generates YouTube Shorts + Instagram Reels for a single channel.
Optimized for human-like, non-AI-sounding content that actually gets views.
"""

import os
import logging
from src.core.ai_router import AIRouter
from src.core.voice_engine import generate_voice_for_content
from src.core.image_engine import generate_image
from src.core.video_engine import render_video, VideoSettings
from src.core.trend_engine import get_trends_for_channel
from src.core.prompts.personality import CHANNEL_PROMPTS
from src.core.config import PRIMARY_YOUTUBE_CHANNEL
from src.core.series_tracker import get_continuity_context

log = logging.getLogger(__name__)

CHANNEL_IDENTITY = {
    "Story With Aisha": {
        "narrator": "Aisha",
        "tone": "warm, emotional, cinematic, heart-touching",
        "themes": "office romance, college love, long-distance, heartbreak, reunion, rain encounters",
        "format_hint": "60-90 second YouTube Short / Instagram Reel with emotional narration",
        "hook_style": "Open with a single emotional sentence that grabs attention in 2 seconds.",
        "voice_style": "Soft, warm, expressive, like telling a friend",
    },
}


class YouTubeCrew:
    def __init__(self):
        self.ai = AIRouter()
        self.results = {}

    def _generate(self, prompt: str, preferred_provider: str = None, nvidia_task_type: str = "writing") -> str:
        if preferred_provider:
            try:
                result = self.ai._call_provider(
                    preferred_provider,
                    "You are a talented Hindi storyteller. You write like a real person — warm, emotional, natural. Never sound like AI or a machine.",
                    prompt,
                    [],
                    None,
                    nvidia_task_type=nvidia_task_type,
                )
                return result.strip()
            except Exception as e:
                log.warning(f"youtube_crew provider error: {e}")

        result = self.ai.generate(
            system_prompt="You are a talented Hindi storyteller. You write like a real person — warm, emotional, natural. Never sound like AI or a machine.",
            user_message=prompt,
            nvidia_task_type=nvidia_task_type,
        )
        return result.text.strip()

    def kickoff(self, inputs: dict) -> str:
        channel = inputs.get("channel", PRIMARY_YOUTUBE_CHANNEL)
        fmt = inputs.get("format", "Short/Reel")
        master_prompt = inputs.get("master_prompt", "")
        render_mp4 = inputs.get("render_video", True)

        identity = CHANNEL_IDENTITY.get(channel, CHANNEL_IDENTITY["Story With Aisha"])

        from src.core.config import CHANNEL_AI_PROVIDER, CHANNEL_AI_TASK_TYPE

        preferred_ai = CHANNEL_AI_PROVIDER.get(channel, "gemini")
        nvidia_task = CHANNEL_AI_TASK_TYPE.get(channel, "writing")

        log.info(f"[Crew] Fetching real-time trends for {channel}...")
        trends = {}
        try:
            trends = get_trends_for_channel(channel)
        except Exception as e:
            log.warning(f"[Crew] Trend fetch failed ({e}), using creative direction")

        raw_topic = inputs.get("topic", "")
        if not raw_topic and trends.get("recommended_topic"):
            topic = trends["recommended_topic"]
            log.info(f"[Crew] Auto-selected trending topic: {topic}")
        else:
            topic = raw_topic or "A Late Night Secret"

        trend_context = ""
        if trends.get("viral_keywords"):
            trend_context = (
                f"\n\nCURRENT TREND DATA:\n"
                f"Viral keywords: {', '.join(trends.get('viral_keywords', []))}\n"
                f"Trending topics: {', '.join(trends.get('trending_topics', []))}\n"
            )

        log.info(f"[Crew] {channel} | {topic} | AI: {preferred_ai.upper()}")

        channel_context = (
            master_prompt
            or CHANNEL_PROMPTS.get(channel)
            or (
                f"Channel: {channel}\n"
                f"Tone: {identity['tone']}\n"
                f"Themes: {identity['themes']}\n"
                f"Format: {identity['format_hint']}\n"
            )
        )

        # Step 1: Research trending angle
        log.info("[Crew] Step 1/5: Researching trending angle...")
        self.results["research"] = self._generate(
            f"""Topic: {topic}
{trend_context}

तुम एक story researcher हो। तुम्हें ६०-९० सेकंड की Hindi love story के लिए एक viral angle ढूंढना है।

सोचो:
- अभी YouTube Shorts और Instagram Reels पर कौन सी Hindi love story themes viral हो रही हैं?
- कौन सा hook first 2 seconds में attention grab करेगा?
- कौन सा emotional moment लोगों को share करने पर मजबूर करेगा?

Output (Hindi देवनागरी में):
१. Story angle (एक लाइन)
२. किरदारों के नाम और setting
३. Opening hook line
४. Core emotional moment
५. Ending twist

सिर्फ ये ५ points दो। ज़्यादा मत लिखो।""",
            preferred_provider=preferred_ai,
            nvidia_task_type=nvidia_task,
        )

        continuity_ctx = ""
        if inputs.get("series_id"):
            continuity_ctx = get_continuity_context(inputs["series_id"])

        # Step 2: Write the actual script
        log.info("[Crew] Step 2/5: Writing script...")
        self.results["script"] = self._generate(
            f"""{channel_context}

Story Brief:
{self.results['research']}
{continuity_ctx + chr(10) if continuity_ctx else ""}

अब इस brief से एक complete narration script लिखो।

CRITICAL RULES:
- Total length: ठीक १५०-२५० शब्द (६०-९० सेकंड narration)
- पूरा script १००% देवनागरी हिंदी में
- ऐसे लिखो जैसे एक लड़की अपनी सहेली को फोन पर कहानी सुना रही है
- "..." natural pause के लिए use करो
- छोटे-छोटे वाक्य — बोलने में आसान
- Opening: एक line जो रुकने पर मजबूर करे
- Middle: दिल छूने वाला moment
- End: ऐसा emotional twist जो याद रहे
- Last line: natural CTA — "तुम्हें कैसी लगी? कमेंट में बताओ..."

ABSOLUTELY PROHIBITED:
- English words, Roman script, emojis
- "एआई", "बॉट", "जनरेट", "कंटेंट", "स्क्रिप्ट" जैसे शब्द
- Scene directions like [PAUSE], [MUSIC] — just write naturally
- Bullet points, numbered lists, headings — just pure narration text
- Anything longer than २५० words""",
            preferred_provider=preferred_ai,
            nvidia_task_type=nvidia_task,
        )

        # Step 3: SEO package
        log.info("[Crew] Step 3/5: Building SEO package...")
        self.results["marketing"] = self._generate(
            f"""Topic: {topic}
Script excerpt: {self.results['script'][:300]}

Create a YouTube Shorts + Instagram Reels SEO package.
ALL in Hindi (Devanagari) except hashtags:

१. YouTube title — catchy, emotional, max 60 chars, Hindi. Include #shorts
२. YouTube description — 2-3 lines Hindi + relevant keywords
३. Instagram caption — emotional one-liner Hindi, max 150 chars
४. 15 hashtags (mix of Hindi and English trending tags like #hindistory #lovestory #shorts #reels #viral)
५. Thumbnail text — 3-4 Hindi words that create curiosity

Format your response exactly like:
TITLE: ...
DESCRIPTION: ...
CAPTION: ...
HASHTAGS: #tag1 #tag2 ...
THUMBNAIL: ...""",
            preferred_provider=preferred_ai,
            nvidia_task_type=nvidia_task,
        )

        # Step 4: Generate voice + thumbnail
        log.info("[Crew] Step 4/5: Generating voice + thumbnail...")
        self.results["voice_path"] = None
        self.results["thumbnail_path"] = None

        try:
            voice_path = generate_voice_for_content(
                self.results["script"],
                language="Hindi",
                channel=channel,
            )
            if voice_path:
                self.results["voice_path"] = voice_path
                log.info(f"[Crew] Voice generated (ElevenLabs primary): {voice_path}")
        except Exception as e:
            log.error(f"[Crew] Voice generation failed: {e}")

        try:
            thumbnail_prompt = (
                f"Cinematic portrait of a beautiful Indian woman, emotional expression, "
                f"warm golden hour lighting, shallow depth of field, "
                f"romantic mood, dramatic shadows. Topic: {topic}. "
                f"Ultra high quality, professional photography style."
            )
            image_bytes = generate_image(thumbnail_prompt)
            if image_bytes:
                assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "temp_assets")
                os.makedirs(assets_dir, exist_ok=True)
                thumb_path = os.path.join(assets_dir, f"thumb_{abs(hash(channel + topic)) % 999999}.png")
                with open(thumb_path, "wb") as f:
                    f.write(image_bytes)
                self.results["thumbnail_path"] = thumb_path
                log.info(f"[Crew] Thumbnail generated: {thumb_path}")
        except Exception as e:
            log.error(f"[Crew] Thumbnail generation failed: {e}")

        # Step 5: Render video (always ON for shorts/reels)
        self.results["video_path"] = None
        if render_mp4 and self.results.get("voice_path"):
            try:
                log.info("[Crew] Step 5/5: Rendering video...")
                video_path = render_video(
                    voice_path=self.results["voice_path"],
                    script=self.results["script"],
                    channel=channel,
                    topic=topic,
                    settings=VideoSettings(
                        thumbnail_path=self.results.get("thumbnail_path"),
                        format="shorts",
                        add_subtitles=True,
                    )
                )
                if video_path:
                    self.results["video_path"] = video_path
                    log.info(f"[Crew] Video rendered: {video_path}")
            except Exception as e:
                log.error(f"[Crew] Video render failed: {e}")
        elif not self.results.get("voice_path"):
            log.warning("[Crew] Skipping video render — no voice audio available")

        # Parse marketing fields for downstream consumers
        self.results["parsed_marketing"] = self._parse_marketing(self.results.get("marketing", ""))

        final = (
            f"{'='*60}\n"
            f"CHANNEL: {channel}\n"
            f"FORMAT: {fmt}\n"
            f"TOPIC: {topic}\n"
            f"{'='*60}\n\n"
            f"[SEO & MARKETING]\n{self.results['marketing']}\n\n"
            f"{'-'*40}\n"
            f"[FULL SCRIPT]\n{self.results['script']}\n\n"
            f"{'-'*40}\n"
            f"[ASSETS]\n"
            f"Voice: {self.results.get('voice_path') or 'Not generated'}\n"
            f"Thumbnail: {self.results.get('thumbnail_path') or 'Not generated'}\n"
            f"Video MP4: {self.results.get('video_path') or 'Not rendered'}\n"
            f"{'='*60}"
        )

        log.info("[Crew] Production complete!")
        return final

    def _parse_marketing(self, text: str) -> dict:
        """Extract structured marketing fields from LLM output."""
        data = {"title": "", "description": "", "caption": "", "hashtags": [], "thumbnail_text": ""}
        if not text:
            return data

        lines = text.strip().splitlines()
        for line in lines:
            line = line.strip()
            upper = line.upper()
            if upper.startswith("TITLE:"):
                data["title"] = line.split(":", 1)[1].strip()[:100]
            elif upper.startswith("DESCRIPTION:"):
                data["description"] = line.split(":", 1)[1].strip()[:2000]
            elif upper.startswith("CAPTION:"):
                data["caption"] = line.split(":", 1)[1].strip()[:220]
            elif upper.startswith("HASHTAGS:"):
                raw = line.split(":", 1)[1].strip()
                data["hashtags"] = [t.strip("#,.;:!? ").lower() for t in raw.split() if "#" in t or len(t) > 2][:30]
            elif upper.startswith("THUMBNAIL:"):
                data["thumbnail_text"] = line.split(":", 1)[1].strip()

        if not data["title"] and lines:
            data["title"] = lines[0][:100]
        if not data["hashtags"]:
            for ln in lines:
                if "#" in ln:
                    data["hashtags"].extend([t.strip("#,.;:!? ").lower() for t in ln.split() if t.startswith("#")])

        return data
