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

    def _generate(self, prompt: str, preferred_provider: str = None, nvidia_task_type: str = "writing", max_tokens: int = 8192) -> str:
        import concurrent.futures

        def run_ai():
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

        # Execute AI generation directly.
        # Note: Do not enforce a generic 60-second wrapper timeout here.
        # The AIRouter's fallback chain needs time to try multiple providers.
        # If Gemini fails (1s), Nvidia times out (60s), and Groq works (2s), the total time is 63s.
        # A 60s hard wrapper timeout would prematurely kill the fallback chain!
        return run_ai()

    def kickoff(self, inputs: dict, status_callback=None) -> str:
        def _status(msg):
            print(msg)
            if status_callback:
                status_callback(msg)
        channel = inputs.get("channel", "Story With Aisha")
        fmt = inputs.get("format", "Long Form")
        master_prompt = inputs.get("master_prompt", "")
        render_mp4 = inputs.get("render_video", False)  # Set True to also render MP4

        identity = CHANNEL_IDENTITY.get(channel, CHANNEL_IDENTITY["Story With Aisha"])

        from src.core.config import CHANNEL_AI_PROVIDER, CHANNEL_AI_TASK_TYPE

        preferred_ai = CHANNEL_AI_PROVIDER.get(channel, "gemini")
        nvidia_task = CHANNEL_AI_TASK_TYPE.get(channel, "writing")

        # Fetch real-time trends first — then use as topic if none given
        _status("🔍 [TrendEngine] Fetching real-time trends...")
        trends = {}
        try:
            trends = get_trends_for_channel(channel)
        except Exception as e:
            _status(f"⚠️ [TrendEngine] Warning: trend fetch failed ({e}), using fallback")

        # Use trending topic if none provided, or enhance provided topic with trend data
        raw_topic = inputs.get("topic", "")
        if not raw_topic and trends.get("recommended_topic"):
            topic = trends["recommended_topic"]
            _status(f"📈 [TrendEngine] Auto-selected trending topic: {topic}")
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

        _status(f"🎬 [Crew] {channel} | {topic} | AI: {preferred_ai.upper()}")

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

        _status("🧠 [Riya] Researching trending angles + story brief...")
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

        _status("✍️ [Lexi] Writing the pure storytelling script...")
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

        _status(f"🎥 [Mia] Translating {len(scenes)} scenes into Video Engine JSON...")

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
                _status(f"      ... Processed batch {i // batch_size + 1}")
            except json.JSONDecodeError as e:
                _status(f"❌ [Error] Mia failed JSON decode on batch {i // batch_size + 1}: {e}")
                print(f"      Raw output: {cleaned_json[:200]}...")
                # Fallback: just put the raw text in
                for idx, scene in enumerate(batch):
                    master_json_pipeline.append({"part": i + idx + 1, "narration": scene, "visual_prompt": "Cinematic visual for: " + topic})

        self.results["script_chunks"] = master_json_pipeline
        self.results["visuals"] = "\n".join([f"[Scene {c.get('part')}] {c.get('visual_prompt', '')}" for c in master_json_pipeline])


        _status("📈 [Cappy] Building SEO package...")
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
                _status(f"❌ [Cappy] Failed to parse Shorts SEO array: {e}")
        else:
            # We can parse the single JSON block if needed later, for now we just keep the raw marketing string
            pass

        _status("🗣️🎨 [Aria+Mia] Generating voice, visuals, and thumbnail assets per chunk...")
        self.results["voice_path"] = None
        self.results["thumbnail_path"] = None
        self.results["generated_assets"] = []

        mood_for_voice = "romantic" if ("Riya" in channel or "Aisha & Him" in channel) else "personal"
        voice_language = "Hindi" if channel in ("Story With Aisha", "Riya's Dark Whisper", "Riya's Dark Romance Library") else "English"

        script_chunks = self.results.get("script_chunks", [])

        # Fallback to monolithic logic if JSON decoding failed entirely
        if not script_chunks:
            script_chunks = [{"part": 1, "narration": self.results["script"], "visual_prompt": "Cinematic visual for " + topic}]

        # --- HUMAN IN THE LOOP APPROVAL GATE ---
        require_approval = inputs.get("require_approval", False)
        if require_approval:
            import uuid

            job_id = str(uuid.uuid4())
            preview_text = f"🎬 *Script Ready for {channel}*\n"
            preview_text += f"Topic: {topic}\n\n"

            for chunk in script_chunks[:3]:
                preview_text += f"*{chunk.get('part')}*: {chunk.get('narration')[:100]}...\n"

            preview_text += f"\nTotal Chunks: {len(script_chunks)}"

            try:
                import telebot
                from src.core.config import _get
                token = _get("TELEGRAM_BOT_TOKEN")
                ajay_id = _get("AJAY_TELEGRAM_ID")
                if token and ajay_id:
                    bot = telebot.TeleBot(token)
                    markup = telebot.types.InlineKeyboardMarkup()
                    btn_approve = telebot.types.InlineKeyboardButton("✅ Approve & Render", callback_data=f"render_job_{job_id}")
                    btn_rewrite = telebot.types.InlineKeyboardButton("🔄 Rewrite", callback_data=f"rewrite_job_{job_id}")
                    markup.add(btn_approve, btn_rewrite)

                    bot.send_message(ajay_id, preview_text, reply_markup=markup, parse_mode="Markdown")

                    # Store job state temporarily so the callback can pick it up
                    import pickle, os
                    assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "temp_assets")
                    os.makedirs(assets_dir, exist_ok=True)
                    with open(os.path.join(assets_dir, f"job_{job_id}.pkl"), "wb") as pf:
                        pickle.dump({
                            "channel": channel,
                            "topic": topic,
                            "fmt": fmt,
                            "script_chunks": script_chunks,
                            "render_mp4": render_mp4,
                            "marketing": self.results.get("marketing", "")
                        }, pf)

                    _status(f"⏸️ [Approval Gate] Sent to Telegram. Pausing pipeline for job {job_id}.")
                    return f"Script generated and sent for approval. Job ID: {job_id}"
            except Exception as e:
                _status(f"❌ [Approval Gate] Failed to send to Telegram: {e}")

        return self.render_assets(channel, topic, fmt, script_chunks, render_mp4, voice_language, mood_for_voice, self.results.get("marketing", ""))

    def render_assets(self, channel, topic, fmt, script_chunks, render_mp4, voice_language, mood_for_voice, marketing):
        import os
        from src.core.voice_engine import generate_voice
        from src.core.image_engine import generate_image
        import time
        from tenacity import retry, stop_after_attempt, wait_exponential

        self.results = getattr(self, "results", {})
        self.results["marketing"] = marketing
        self.results["generated_assets"] = []

        # Define retry decorators for the APIs
        @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
        def _safe_generate_voice(text_chunk, lang, mood_val, chan):
            from src.core.voice_engine import generate_voice
            return generate_voice(text_chunk, language=lang, mood=mood_val, channel=chan)

        @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
        def _safe_generate_image(prompt_text):
            from src.core.image_engine import generate_image
            return generate_image(prompt_text)

        for chunk in script_chunks:
            part_num = chunk.get("part", 1)
            narration = chunk.get("narration", "")
            visual_prompt = chunk.get("visual_prompt", "")

            _status(f"🔄 Processing Scene Part {part_num}...")

            # 1. Stateful Checkpointing Paths
            assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "temp_assets")
            os.makedirs(assets_dir, exist_ok=True)

            # Use a deterministic hash based on the narration text so it uniquely identifies the chunk
            chunk_hash = abs(hash(narration + channel))
            expected_audio = os.path.join(assets_dir, f"audio_{chunk_hash}.mp3")
            expected_image = os.path.join(assets_dir, f"scene_{chunk_hash}.png")

            # 2. AUDIO GENERATION (Skip if exists)
            audio_path = None
            if os.path.exists(expected_audio) and os.path.getsize(expected_audio) > 1000:
                print(f"   [Aria] Checkpoint found: Audio for part {part_num} already exists. Skipping.")
                audio_path = expected_audio
            else:
                try:
                    # Retry wrapper for API
                    gen_path = _safe_generate_voice(narration, voice_language, mood_for_voice, channel)
                    if gen_path:
                        # Move to deterministic path
                        import shutil
                        shutil.move(gen_path, expected_audio)
                        audio_path = expected_audio
                except Exception as e:
                    print(f"   [Aria] Voice generation permanently failed for part {part_num} after retries: {e}")

            # 3. IMAGE GENERATION (Skip if exists)
            image_path = None
            if os.path.exists(expected_image) and os.path.getsize(expected_image) > 1000:
                print(f"   [Mia] Checkpoint found: Image for part {part_num} already exists. Skipping.")
                image_path = expected_image
            else:
                try:
                    img_bytes = _safe_generate_image(visual_prompt)
                    if img_bytes:
                        with open(expected_image, "wb") as img_f:
                            img_f.write(img_bytes)
                        image_path = expected_image
                except Exception as e:
                    print(f"   [Mia] Image generation permanently failed for part {part_num} after retries: {e}")

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
                    _status(f"✅ [VideoEngine] MP4 ready: {video_path}")
            except Exception as e:
                _status(f"❌ [VideoEngine] Video render failed: {e}")

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

        _status("🎉 [Crew] Production complete!")
        return final
