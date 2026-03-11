"""
mia.py — SEO Specialist Agent
===============================
Mia generates optimized YouTube titles, descriptions, tags, and hashtags.
Uses Ollama (free local AI) for all generation.
"""

from src.agents.base_agent import BaseAgent


class MiaAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name="Mia",
            role="YouTube SEO Specialist",
            personality="""You are Mia, a YouTube SEO expert who understands
search algorithms, click-through rates, and what titles make people click.
You specialize in Indian YouTube audiences and know what keywords rank.
Your titles are specific, benefit-driven, and include numbers when possible.
You never write clickbait that misleads — only honest titles that deliver on their promise."""
        )

    def run_task(self, job_id: str, input_data: dict) -> dict:
        topic    = input_data.get("topic", "")
        script   = input_data.get("script", "")
        keywords = input_data.get("keywords", [])

        seo = self.think_structured(f"""Create complete YouTube SEO package for:

Topic: {topic}
Script excerpt: {script[:800]}
Target keywords: {", ".join(keywords[:10])}

Return ONLY this JSON (no other text):
{{
  "title": "Compelling title under 70 chars with number or power word",
  "title_alternatives": ["alt 1", "alt 2", "alt 3"],
  "description": "300 word description. First 150 chars most important. Include 5+ keywords naturally. End with subscribe CTA.",
  "tags": ["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10","tag11","tag12","tag13","tag14","tag15"],
  "hashtags": ["#hashtag1","#hashtag2","#hashtag3","#hashtag4","#hashtag5"],
  "category": "Science & Technology or Education or etc",
  "thumbnail_text": "3-5 words for thumbnail text overlay"
}}""")

        self._save_output(job_id, "yt_seo", {
            "title":       seo.get("title", topic[:70]),
            "description": seo.get("description", ""),
            "tags":        seo.get("tags", []),
            "hashtags":    seo.get("hashtags", []),
            "category":    seo.get("category", "Education"),
            "thumbnail_text": seo.get("thumbnail_text", "")
        })

        self.log.info(f"[Mia] SEO ready: '{seo.get('title', '')}'")
        return seo


# ════════════════════════════════════════════════════════════════
"""
sync_bot.py — Audio+Video Sync Agent
======================================
Sync merges the audio from Aria with the video from Vex.
Uses FFmpeg — completely free, industry standard tool.
Also creates: YouTube Shorts version, Instagram Reel version.
"""

import os
import subprocess
import time
from pathlib import Path
from src.agents.base_agent import BaseAgent


class SyncAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="Sync", role="Audio-Video Synchronizer")
        self.output_dir = Path("data/synced")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_task(self, job_id: str, input_data: dict) -> dict:
        audio_path = input_data.get("audio_path", "")
        video_path = input_data.get("video_path", "")

        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        output_path = self.output_dir / f"final_{job_id}_{int(time.time())}.mp4"

        # If no video yet, create a simple video from audio + black bg
        if not video_path or not os.path.exists(video_path):
            video_path = self._create_placeholder_video(audio_path, str(job_id))

        # Merge with FFmpeg (free)
        success = self._merge_av(audio_path, video_path, str(output_path))
        if not success:
            raise RuntimeError("FFmpeg merge failed")

        # Create Shorts version (vertical, 60s max)
        shorts_path = self._create_shorts(str(output_path), job_id)

        self.log.info(f"[Sync] ✅ Merged: {output_path.name}")
        return {
            "final_path":  str(output_path),
            "shorts_path": shorts_path,
            "status":      "synced"
        }

    def _merge_av(self, audio: str, video: str, output: str) -> bool:
        cmd = [
            "ffmpeg", "-y",
            "-i", video,
            "-i", audio,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            return result.returncode == 0
        except FileNotFoundError:
            self.log.error("[Sync] FFmpeg not found. Install from https://ffmpeg.org")
            return False

    def _create_placeholder_video(self, audio_path: str, job_id: str) -> str:
        """Create black background video matching audio length."""
        out = f"data/videos/placeholder_{job_id}.mp4"
        os.makedirs("data/videos", exist_ok=True)
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=1920x1080:r=24",
            "-i", audio_path,
            "-c:v", "libx264", "-c:a", "copy",
            "-shortest", out
        ]
        subprocess.run(cmd, capture_output=True, timeout=120)
        return out

    def _create_shorts(self, video_path: str, job_id: str) -> str:
        """Create YouTube Shorts version (1080x1920, max 60s)."""
        try:
            shorts_path = str(self.output_dir / f"shorts_{job_id}.mp4")
            cmd = [
                "ffmpeg", "-y", "-i", video_path,
                "-vf", "crop=ih*9/16:ih,scale=1080:1920",
                "-c:v", "libx264", "-c:a", "aac",
                "-t", "60",  # Max 60 seconds for Shorts
                shorts_path
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            if result.returncode == 0:
                self.log.info(f"[Sync] Shorts version created")
                return shorts_path
        except Exception as e:
            self.log.warning(f"[Sync] Shorts creation failed: {e}")
        return ""


# ════════════════════════════════════════════════════════════════
"""
cappy.py — Caption Creator Agent
==================================
Cappy uses OpenAI Whisper (free, local) to generate accurate captions/subtitles.
Whisper runs on your PC — no API key, completely free, works in Hindi too.
"""

import subprocess
import os
from pathlib import Path
from src.agents.base_agent import BaseAgent


class CappyAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="Cappy", role="Caption & Subtitle Creator")
        self.output_dir = Path("data/captions")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_task(self, job_id: str, input_data: dict) -> dict:
        audio_path = input_data.get("audio_path", "")
        language   = input_data.get("language", "en")

        if not os.path.exists(audio_path):
            self.log.warning("[Cappy] Audio not found — skipping captions")
            return {"srt_path": "", "vtt_path": ""}

        srt_path = self._generate_captions(audio_path, language)
        vtt_path = self._srt_to_vtt(srt_path) if srt_path else ""

        self.log.info(f"[Cappy] ✅ Captions ready: {os.path.basename(srt_path)}")
        return {"srt_path": srt_path, "vtt_path": vtt_path}

    def _generate_captions(self, audio_path: str, language: str) -> str:
        """Use Whisper locally — free, accurate, supports Hindi."""
        output_name = self.output_dir / f"captions_{os.path.basename(audio_path).split('.')[0]}"
        try:
            # Whisper via command line (pip install openai-whisper)
            model = "medium"  # Good balance of speed/accuracy
            cmd = [
                "whisper", audio_path,
                "--model", model,
                "--language", language,
                "--output_format", "srt",
                "--output_dir", str(self.output_dir)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            # Whisper saves as original_filename.srt
            expected = self.output_dir / (Path(audio_path).stem + ".srt")
            if expected.exists():
                return str(expected)
        except FileNotFoundError:
            self.log.info("[Cappy] Installing Whisper...")
            os.system("pip install openai-whisper --break-system-packages -q")
        except Exception as e:
            self.log.warning(f"[Cappy] Whisper failed: {e}")
        return ""

    def _srt_to_vtt(self, srt_path: str) -> str:
        """Convert SRT to WebVTT format for web players."""
        if not srt_path or not os.path.exists(srt_path):
            return ""
        vtt_path = srt_path.replace(".srt", ".vtt")
        try:
            with open(srt_path) as f:
                content = f.read()
            vtt_content = "WEBVTT\n\n" + content.replace(",", ".")
            with open(vtt_path, "w") as f:
                f.write(vtt_content)
            return vtt_path
        except Exception:
            return ""
