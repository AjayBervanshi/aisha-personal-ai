"""
youtube_crew.py
==============
Aisha's YouTube Content Production Engine.
Handles all channels with unique identity and generates core assets.
"""

import os
import logging
from src.core.ai_router import AIRouter
from src.core.voice_engine import generate_voice
from src.core.image_engine import generate_image
from src.core.video_engine import render_video, VideoSettings
from src.core.trend_engine import get_trends_for_channel
from src.core.prompts.personality import CHANNEL_PROMPTS
from src.core.config import CHANNEL_VOICE_IDS
from src.core.series_tracker import get_continuity_context

log = logging.getLogger(__name__)

CHANNEL_IDENTITY = {
    "Story With Aisha": {
        "narrator": "Aisha",
        "tone": "warm, emotional, cinematic, heart-touching",
        "themes": "office romance, college love, long-distance, heartbreak, reunion",
        "format_hint": "8-15 minute audio storytelling with emotional dialogue",
        "hook_style": "Start with a single emotional sentence that instantly pulls attention.",
        "voice_style": "Soft, warm, expressive",
    },
    "Riya's Dark Whisper": {
        "narrator": "Riya",
        "tone": "mysterious, seductive, psychological, slow-burn",
        "themes": "forbidden love, obsession, betrayal, secret desires, dark relationships",
        "format_hint": "10-20 minute slow-build suspense story",
        "hook_style": "Open with forbidden truth and immediate tension.",
        "voice_style": "Deep, slow, whispering",
    },
    "Riya's Dark Romance Library": {
        "narrator": "Riya",
        "tone": "intense, addictive, dramatic, novel-style",
        "themes": "mafia romance, enemies to lovers, possessive alpha male, morally grey characters",
        "format_hint": "15-25 minute chapter-style story episode",
        "hook_style": "Drop directly into a dangerous emotional moment.",
        "voice_style": "Commanding and intense",
    },
    "Aisha & Him": {
        "narrator": "Aisha",
        "tone": "relatable, funny, sweet, real, everyday couple",
        "themes": "cute fights, jealousy, good morning texts, late night talks, teasing",
        "format_hint": "30 second to 3 minute dialogue-format short/reel",
        "hook_style": "Open mid-conversation in a relatable couple moment.",
        "voice_style": "Casual, playful, real",
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
                    "You are an expert content creator for YouTube and Instagram storytelling channels.",
                    prompt,
                    [],
                    None,
                    nvidia_task_type=nvidia_task_type,
                )
                return result.strip()
            except Exception as e:
                log.warning(f"youtube_crew error: {e}")

        result = self.ai.generate(
            system_prompt="You are an expert content creator for YouTube and Instagram storytelling channels.",
            user_message=prompt,
            nvidia_task_type=nvidia_task_type,
        )
        return result.text.strip()

    def kickoff(self, inputs: dict) -> str:
        channel = inputs.get("channel", "Story With Aisha")
        fmt = inputs.get("format", "Long Form")
        master_prompt = inputs.get("master_prompt", "")
        render_mp4 = inputs.get("render_video", False)  # Set True to also render MP4

        identity = CHANNEL_IDENTITY.get(channel, CHANNEL_IDENTITY["Story With Aisha"])

        from src.core.config import CHANNEL_AI_PROVIDER, CHANNEL_AI_TASK_TYPE

        preferred_ai = CHANNEL_AI_PROVIDER.get(channel, "gemini")
        nvidia_task = CHANNEL_AI_TASK_TYPE.get(channel, "writing")

        # Fetch real-time trends first — then use as topic if none given
        print("[TrendEngine] Fetching real-time trends...")
        trends = {}
        try:
            trends = get_trends_for_channel(channel)
        except Exception as e:
            print(f"[TrendEngine] Warning: trend fetch failed ({e}), using fallback")

        # Use trending topic if none provided, or enhance provided topic with trend data
        raw_topic = inputs.get("topic", "")
        if not raw_topic and trends.get("recommended_topic"):
            topic = trends["recommended_topic"]
            print(f"[TrendEngine] Auto-selected trending topic: {topic}")
        else:
            topic = raw_topic or "A Late Night Secret"

        # Append trend context to enrich research
        trend_context = ""
        if trends.get("viral_keywords"):
            trend_context = (
                f"\n\nCURRENT TREND DATA (real-time):\n"
                f"Viral keywords: {', '.join(trends.get('viral_keywords', []))}\n"
                f"Trending topics: {', '.join(trends.get('trending_topics', []))}\n"
                f"Top angles: {chr(10).join(trends.get('top_angles', []))}\n"
                f"Best hook idea: {trends.get('hook_idea', '')}\n"
            )

        print(f"[Crew] {channel} | {topic} | AI: {preferred_ai.upper()}")

        # Use full channel identity prompt → minimal fallback
        channel_context = (
            master_prompt
            or CHANNEL_PROMPTS.get(channel)
            or (
                f"Channel: {channel}\n"
                f"Tone: {identity['tone']}\n"
                f"Themes: {identity['themes']}\n"
                f"Format: {identity['format_hint']}\n"
                f"Hook style: {identity['hook_style']}\n"
                f"Voice: {identity['voice_style']}"
            )
        )

        print("[Riya] Researching trending angles + story brief...")
        self.results["research"] = self._generate(
            f"""You are Riya, the Story Researcher.
{channel_context}
Topic: {topic}
{trend_context}

STEP 1 — TREND ANALYSIS:
Using the real-time trend data above (if available), identify the single most viral story angle right now for the '{channel}' niche. Consider: titles with high CTR patterns, emotional hooks driving comments, trending tropes in Hindi storytelling channels, popular scenarios in this category.

STEP 2 — STORY BRIEF (using the top trending angle):
- Character names + quick backstory (fresh, never reused)
- Core conflict (what creates the tension/desire)
- Emotional/sensory hook (why viewers will stop scrolling for this)
- Viral potential reasoning (why this gets clicks and watch time)

Output: 300 words max. Be specific and concrete.""",
            preferred_provider=preferred_ai,
                nvidia_task_type=nvidia_task,
        )

        # Inject series continuity context if this is part of an episodic series
        continuity_ctx = ""
        if inputs.get("series_id"):
            continuity_ctx = get_continuity_context(inputs["series_id"])

        print("[Lexi] Writing the pure storytelling script...")
        lexi_prompt = f"""You are Lexi, a top-tier Hollywood screenwriter and director.
{channel_context}
{continuity_ctx + chr(10) + chr(10) if continuity_ctx else ""}Story Brief:
{self.results['research']}

You must write the full story script. To ensure perfect video editing later, you must separate every 30-60 second spoken chunk with the exact text: [SCENE BREAK].
Do NOT use JSON. Do NOT include any intro or conversational text. Just write the story, using [SCENE BREAK] between thoughts.

Rules:
1. The Hook (0-5s): Start immediately with high stakes or raw emotion. Do not say "Welcome back."
2. The Pacing: Use short, punchy sentences. Break up long paragraphs. Use ellipses (...) or em-dashes (—) instead of bracketed [PAUSE] for better natural TTS breathing.
3. Format: {'Vertical Short/Reel script. Maximum 5-7 chunks total. Hyper-fast pacing.' if 'short' in fmt.lower() or 'reel' in fmt.lower() else 'Full cinematic story script. 15-25 chunks. Deep character building.'}

Example format:
The neon lights flickered in the rain... He knew he was being followed. But by who?
[SCENE BREAK]
He turned the alley corner—his heart pounding. A shadow detached itself from the wall...
[SCENE BREAK]
He couldn't breathe. He closed his eyes and waited for the end..."""

        raw_lexi_output = self._generate(
            lexi_prompt,
            preferred_provider=preferred_ai,
            nvidia_task_type=nvidia_task,
        )

        self.results["script"] = raw_lexi_output.replace("```text", "").replace("```", "").strip()

        import json
        raw_script = self.results["script"]
        scenes = [s.strip() for s in raw_script.split("[SCENE BREAK]") if s.strip()]

        master_json_pipeline = []
        batch_size = 5

        print(f"[Mia] Translating {len(scenes)} scenes into Video Engine JSON...")

        for i in range(0, len(scenes), batch_size):
            batch = scenes[i:i + batch_size]

            mia_prompt = f"""
            You are Mia, the elite Visual Director and AI Prompt Engineer.
            Take these {len(batch)} script scenes and format them into our Video Engine JSON array.
            Translate the emotional and visual vibe into an English 'visual_prompt' (Midjourney style).

            Aesthetic: {'Dark, moody, cinematic lighting, neo-noir, deep shadows, 8k resolution, photorealistic, shot on 35mm lens, Unreal Engine 5 render' if 'Riya' in channel else 'Warm golden-hour, highly emotional close-ups, depth of field, photorealistic, 8k resolution, highly detailed cinematic movie still, soft lighting'}

            SCENES TO PROCESS:
            {batch}

            OUTPUT SCHEMA:
            [
              {{ "part": <number>, "narration": "<exact text from scene>", "visual_prompt": "<english keywords>" }}
            ]

            Return ONLY a valid JSON array. Do not include markdown ticks like ```json.
            """

            mia_output = self._generate(mia_prompt, preferred_provider=preferred_ai, nvidia_task_type=nvidia_task)

            cleaned_json = re.sub(r'```json\n?|```', '', mia_output).strip()
            try:
                batch_json = json.loads(cleaned_json)
                master_json_pipeline.extend(batch_json)
                print(f"      ... Processed batch {i // batch_size + 1}")
            except json.JSONDecodeError as e:
                print(f"[Error] Mia failed JSON decode on batch {i // batch_size + 1}: {e}")
                print(f"      Raw output: {cleaned_json[:200]}...")
                # Fallback: just put the raw text in
                for idx, scene in enumerate(batch):
                    master_json_pipeline.append({"part": i + idx + 1, "narration": scene, "visual_prompt": "Cinematic visual for: " + topic})

        self.results["script_chunks"] = master_json_pipeline
        self.results["visuals"] = "\n".join([f"[Scene {c.get('part')}] {c.get('visual_prompt', '')}" for c in master_json_pipeline])


        print("[Cappy] Building SEO package...")
        is_short = ('short' in fmt.lower() or 'reel' in fmt.lower())

        cappy_prompt = f"""You are Cappy, the SEO and Viral Marketing Expert.
{channel_context}
Topic: {topic}
Full Script Overview: {self.results['script'][:1000]}...

Your job is to generate the perfect YouTube/Instagram metadata.

"""
        if is_short:
            cappy_prompt += f"""We are creating a DRIP-FEED series of {len(scenes)} Shorts/Reels based on the script chunks.
You need to generate a unique Title and 5 viral tags for EACH chunk so they can be posted sequentially.

OUTPUT SCHEMA:
[
  {{ "part": 1, "title": "Clickbait Title Part 1", "tags": ["#shorts", "#viral"] }},
  {{ "part": 2, "title": "Clickbait Title Part 2", "tags": ["#shorts", "#trending"] }}
]
"""
        else:
            cappy_prompt += f"""We are creating ONE long-form landscape YouTube video.
You need to generate one viral Title, a 150-word Description, and 15 viral tags.

OUTPUT SCHEMA:
{{ "title": "Epic Clickbait Title", "description": "Full description...", "tags": ["tag1", "tag2"] }}
"""

        cappy_prompt += "Return ONLY a valid JSON object/array. No markdown ticks like ```json."

        self.results["marketing"] = self._generate(
            cappy_prompt,
            preferred_provider=preferred_ai,
            nvidia_task_type=nvidia_task,
        )

        # Merge Cappy's metadata back into the script_chunks if it's a short
        if is_short:
            try:
                import json
                seo_array = json.loads(re.sub(r'```json\n?|```', '', self.results["marketing"]).strip())
                if isinstance(seo_array, list):
                    for idx, chunk in enumerate(self.results["script_chunks"]):
                        if idx < len(seo_array):
                            chunk["title"] = seo_array[idx].get("title", f"{topic} (Part {idx+1})")
                            chunk["tags"] = seo_array[idx].get("tags", ["#shorts", "#viral"])
            except Exception as e:
                print(f"[Cappy] Failed to parse Shorts SEO array: {e}")
        else:
            # We can parse the single JSON block if needed later, for now we just keep the raw marketing string
            pass

        print("[Aria+Mia] Generating voice, visuals, and thumbnail assets per chunk...")
        self.results["voice_path"] = None
        self.results["thumbnail_path"] = None
        self.results["generated_assets"] = []

        mood_for_voice = "romantic" if ("Riya" in channel or "Aisha & Him" in channel) else "personal"
        voice_language = "Hindi" if channel in ("Story With Aisha", "Riya's Dark Whisper", "Riya's Dark Romance Library") else "English"

        script_chunks = self.results.get("script_chunks", [])

        # Fallback to monolithic logic if JSON decoding failed entirely
        if not script_chunks:
            script_chunks = [{"part": 1, "narration": self.results["script"], "visual_prompt": "Cinematic visual for " + topic}]

        for chunk in script_chunks:
            part_num = chunk.get("part", 1)
            narration = chunk.get("narration", "")
            visual_prompt = chunk.get("visual_prompt", "")

            print(f"Processing Scene Part {part_num}...")

            audio_path = None
            try:
                # Generate audio per chunk to force ElevenLabs to reset breathing and pacing per scene
                audio_path = generate_voice(narration, language=voice_language, mood=mood_for_voice, channel=channel)
            except Exception as e:
                print(f"[Aria] Voice generation failed for part {part_num}: {e}")

            image_path = None
            try:
                # Generate image directly linked to the narration! No more regex guessing.
                img_bytes = generate_image(visual_prompt)
                if img_bytes:
                    assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "temp_assets")
                    os.makedirs(assets_dir, exist_ok=True)
                    from src.core.video_engine import _FORMATS
                    # If format is shorts, we typically generate larger images or square ones that we center-crop.
                    # Generate_image handles the sizing natively if we pass width/height, but defaulting to wide works if cropped later.
                    image_path = os.path.join(assets_dir, f"scene_{abs(hash(channel + topic))}_{part_num}.png")
                    with open(image_path, "wb") as f:
                        f.write(img_bytes)
            except Exception as e:
                print(f"[Mia] Image generation failed for part {part_num}: {e}")

            self.results["generated_assets"].append({
                "part": part_num,
                "audio_path": audio_path,
                "image_path": image_path,
                "narration": narration
            })

            # The thumbnail is simply the first scene's image!
            if part_num == 1 and image_path:
                self.results["thumbnail_path"] = image_path

        # Step: Render final MP4 if requested
        self.results["video_path"] = None
        if render_mp4 and self.results.get("voice_path"):
            try:
                from src.core.video_engine import render_video, VideoSettings
                is_short = ("short" in fmt.lower() or "reel" in fmt.lower())
                video_path = render_video(
                    voice_path=self.results["voice_path"],
                    script=self.results["script"],
                    channel=channel,
                    topic=topic,
                    settings=VideoSettings(
                        thumbnail_path=self.results.get("thumbnail_path"),
                        format="shorts" if is_short else "landscape",
                        add_subtitles=True,
                    )
                )
                if video_path:
                    self.results["video_path"] = video_path
                    print(f"[VideoEngine] MP4 ready: {video_path}")
            except Exception as e:
                print(f"[VideoEngine] Video render failed: {e}")

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
            f"[VISUAL DIRECTION]\n{self.results['visuals']}\n\n"
            f"{'-'*40}\n"
            f"[ASSETS]\n"
            f"Voice: {self.results.get('voice_path') or 'Not generated'}\n"
            f"Thumbnail: {self.results.get('thumbnail_path') or 'Not generated'}\n"
            f"Video MP4: {self.results.get('video_path') or 'Not rendered (set render_video=True)'}\n\n"
            f"{'-'*40}\n"
            f"[STORY BRIEF]\n{self.results['research']}\n"
            f"{'='*60}"
        )

        print("[Crew] Production complete!")
        return final
