"""
aria.py — Audio/Voice Generator Agent
=======================================
Aria converts approved scripts to professional audio narration.

Free tools used (in order of priority):
1. edge-tts   — Microsoft voices, completely FREE, unlimited usage
2. ElevenLabs — Premium quality, FREE: 10,000 chars/month
3. pyttsx3    — Local fallback, totally offline

Indian English voices available:
- en-IN-NeerjaExpressiveNeural (female, expressive) ← DEFAULT
- en-IN-PrabhatNeural (male, professional)
- hi-IN-SwaraNeural (Hindi female)
- mr-IN-AarohiNeural (Marathi female)
"""

import os
import re
import time
import asyncio
from pathlib import Path
from src.agents.base_agent import BaseAgent


class AriaAgent(BaseAgent):

    VOICES = {
        "english_female": "en-IN-NeerjaExpressiveNeural",
        "english_male":   "en-IN-PrabhatNeural",
        "hindi_female":   "hi-IN-SwaraNeural",
        "marathi_female": "mr-IN-AarohiNeural",
        "english_calm":   "en-IN-NeerjaNeural",
    }

    def __init__(self):
        super().__init__(
            name="Aria",
            role="Professional Voice & Audio Generator"
        )
        self.output_dir = Path("data/audio")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_task(self, job_id: str, input_data: dict) -> dict:
        """
        Generate audio from an approved script.
        Returns: {path: str, duration_s: float, provider: str}
        """
        script   = input_data.get("script", "")
        language = input_data.get("language", "english_female")
        voice    = self.VOICES.get(language, self.VOICES["english_female"])

        # Clean script — remove stage direction markers
        clean_text = self._clean_script_for_tts(script)
        self.log.info(f"[Aria] Generating audio: {len(clean_text)} chars, voice: {voice}")

        output_path = self.output_dir / f"audio_{job_id}_{int(time.time())}.mp3"

        # Try providers in order (free first)
        provider = None

        # Option 1: edge-tts (completely FREE, unlimited)
        if not provider:
            result = self._try_edge_tts(clean_text, str(output_path), voice)
            if result:
                provider = "edge_tts"

        # Option 2: ElevenLabs (FREE: 10K chars/month)
        if not provider:
            result = self._try_elevenlabs(clean_text, str(output_path))
            if result:
                provider = "elevenlabs"

        # Option 3: pyttsx3 (fully offline fallback)
        if not provider:
            result = self._try_pyttsx3(clean_text, str(output_path))
            if result:
                provider = "pyttsx3_local"

        if not provider:
            raise RuntimeError("[Aria] All TTS providers failed")

        # Get audio duration using ffprobe
        duration = self._get_duration(str(output_path))

        # Save to Supabase
        self._save_output(job_id, "yt_audio", {
            "provider":   provider,
            "voice_id":   voice,
            "file_path":  str(output_path),
            "duration_s": duration,
            "status":     "ready"
        })

        self.log.info(f"[Aria] ✅ Audio ready: {output_path.name} ({duration:.0f}s via {provider})")
        return {"path": str(output_path), "duration_s": duration, "provider": provider}

    def _clean_script_for_tts(self, script: str) -> str:
        """Remove stage directions and markers, keep the spoken words."""
        # Remove [B-ROLL: ...], [MUSIC: ...], [PAUSE], [EMPHASIS] etc.
        clean = re.sub(r'\[B-ROLL[^\]]*\]', '', script)
        clean = re.sub(r'\[MUSIC[^\]]*\]', '', clean)
        clean = re.sub(r'\[TRANSITION[^\]]*\]', '', clean)
        clean = re.sub(r'\[EMPHASIS\]', '', clean)
        # Convert [PAUSE] to actual pause (comma)
        clean = re.sub(r'\[PAUSE\]', ',', clean)
        # Remove timestamps like (0:00) or 0:00 -
        clean = re.sub(r'\d+:\d+\s*[-–]?\s*', '', clean)
        # Clean up extra whitespace
        clean = re.sub(r'\n{3,}', '\n\n', clean)
        clean = re.sub(r' {2,}', ' ', clean)
        return clean.strip()

    def _try_edge_tts(self, text: str, output_path: str, voice: str) -> bool:
        """
        Use Microsoft edge-tts — completely free, unlimited, no API key.
        Install: pip install edge-tts
        """
        try:
            import edge_tts

            async def generate():
                communicate = edge_tts.Communicate(text[:4000], voice)
                await communicate.save(output_path)

            asyncio.run(generate())
            return os.path.exists(output_path) and os.path.getsize(output_path) > 1000

        except ImportError:
            self.log.info("[Aria] Installing edge-tts...")
            os.system("pip install edge-tts --break-system-packages -q")
            try:
                import edge_tts
                async def generate():
                    communicate = edge_tts.Communicate(text[:4000], voice)
                    await communicate.save(output_path)
                asyncio.run(generate())
                return True
            except Exception:
                return False
        except Exception as e:
            self.log.warning(f"[Aria] edge-tts failed: {e}")
            return False

    def _try_elevenlabs(self, text: str, output_path: str) -> bool:
        """
        ElevenLabs API — FREE tier: 10,000 chars/month.
        Best quality Indian English voices.
        """
        import requests
        api_key  = os.getenv("ELEVENLABS_API_KEY", "")
        voice_id = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")

        if not api_key or "your_" in api_key:
            return False

        try:
            url  = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
            data = {
                "text": text[:2500],  # Stay within free tier limit
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.75, "similarity_boost": 0.85}
            }
            r = requests.post(url, headers=headers, json=data, timeout=60)
            if r.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(r.content)
                return True
            else:
                self.log.warning(f"[Aria] ElevenLabs: {r.status_code} {r.text[:100]}")
                return False
        except Exception as e:
            self.log.warning(f"[Aria] ElevenLabs failed: {e}")
            return False

    def _try_pyttsx3(self, text: str, output_path: str) -> bool:
        """pyttsx3 — fully offline fallback, completely free."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)
            engine.setProperty('volume', 0.9)
            # Save to file
            engine.save_to_file(text[:5000], output_path)
            engine.runAndWait()
            return os.path.exists(output_path)
        except Exception as e:
            self.log.warning(f"[Aria] pyttsx3 failed: {e}")
            return False

    def _get_duration(self, filepath: str) -> float:
        """Get audio duration using ffprobe (part of FFmpeg, free)."""
        try:
            import subprocess
            result = subprocess.run([
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", filepath
            ], capture_output=True, text=True, timeout=10)
            import json
            data = json.loads(result.stdout)
            return float(data["format"]["duration"])
        except Exception:
            # Estimate from word count if ffprobe not available
            word_count = len(open(filepath, "rb").read()) // 1000
            return word_count * 0.5  # Rough estimate
