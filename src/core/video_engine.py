"""
video_engine.py
===============
Aisha's Video Render Engine.
Converts voice audio + AI-generated scene images into a proper MP4 video.

Flow:
  1. Extract 6-8 scene descriptions from the script using AI
  2. Generate scene images via image_engine.py fallback chain
  3. Stitch audio + images into MP4 using moviepy:
     - Ken Burns effect (slow pan/zoom) for visual interest
     - Smooth fade transitions between scenes
     - Audio overlay on image slideshow
  4. Burn Hindi subtitles via ffmpeg (proportional timing from script)
  5. Return final video path

Formats:
  - "landscape" → 1280×720  (16:9) for standard YouTube uploads
  - "shorts"    → 1080×1920 (9:16) for YouTube Shorts / Instagram Reels
"""

import os
import re
import uuid
import json
import logging
import subprocess
import tempfile
from pathlib import Path
import requests
from dataclasses import dataclass

log = logging.getLogger("Aisha.VideoEngine")

VIDEO_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "temp_videos"
)
os.makedirs(VIDEO_DIR, exist_ok=True)

ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "temp_assets"
)
os.makedirs(ASSETS_DIR, exist_ok=True)

# Format → (width, height)
_FORMATS = {
    "landscape": (1280, 720),
    "shorts":    (1080, 1920),
}

# Devanagari font for Hindi subtitles — bundled or system
_HINDI_FONTS = [
    os.path.join(os.path.dirname(__file__), "fonts", "NotoSansDevanagari-Regular.ttf"),
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    "NotoSansDevanagari-Regular.ttf",
    "C:/Windows/Fonts/Aparajita.ttf",
    "C:/Windows/Fonts/Mangal.ttf",
]


# ── Scene Extraction ─────────────────────────────────────────

def extract_scene_descriptions(script: str, channel: str, num_scenes: int = 7) -> list[str]:
    """
    Uses Gemini to extract visual scene descriptions from the script.
    Returns a list of image generation prompts.
    """
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return _fallback_scenes(channel, num_scenes)

        style_map = {
            "Story With Aisha":            "warm golden hour, soft bokeh, Indian romantic aesthetic, emotional close-ups",
            "Riya's Dark Whisper":         "dark cinematic noir, dramatic shadows, Mumbai night, moody atmospheric",
            "Riya's Dark Romance Library": "dark mafia aesthetic, luxury interiors, intense dramatic lighting",
            "Aisha & Him":                 "bright relatable everyday Indian couple, natural light, candid moments",
        }
        style = style_map.get(channel, "cinematic Indian aesthetic, high quality, emotional")

        prompt = f"""You are a visual director for a YouTube channel called '{channel}'.

Script excerpt:
{script[:2000]}

Extract exactly {num_scenes} distinct visual scenes from this script.
For each scene, write a detailed image generation prompt (1-2 sentences).
Style guide: {style}

Return ONLY a valid JSON array of {num_scenes} strings. Example:
["A woman in a red saree standing by rain-soaked window...", "Two people sharing an umbrella..."]

No explanation, no extra text. Just the JSON array."""

        _url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        _resp = requests.post(_url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
        _resp.raise_for_status()
        text = _resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

        match = re.search(r'\[[\s\S]*\]', text)
        if match:
            scenes = json.loads(match.group(0))
            return [f"{s}. Style: {style}. Ultra HD, cinematic." for s in scenes[:num_scenes]]

    except Exception as e:
        log.error(f"Scene extraction failed: {e}")

    return _fallback_scenes(channel, num_scenes)


def _fallback_scenes(channel: str, num_scenes: int) -> list[str]:
    """Fallback generic scene prompts when AI extraction fails."""
    fallbacks = {
        "Story With Aisha": [
            "Beautiful Indian woman with expressive eyes, soft golden light, emotional portrait",
            "Two people meeting at a busy Mumbai train station, romantic atmosphere",
            "Rain falling on a windowpane, warm interior light, lonely and hopeful mood",
            "A handwritten letter on wooden table, dried flowers beside it",
            "Couple walking on a foggy road in the hills at dawn",
            "Close-up of intertwined hands, soft focus background",
            "Indian woman looking at the sunset from a rooftop, silhouette",
        ],
        "Riya's Dark Whisper": [
            "Mysterious dark-haired woman in Mumbai night, neon reflections, cinematic noir",
            "Dark luxury apartment, dramatic shadows, tension in the air",
            "Rain-soaked Mumbai street at 2AM, lone figure, moody atmosphere",
            "Close-up intense eye contact, dark dramatic lighting",
            "Hands on a whiskey glass, dark bar interior, desire and danger",
            "Silhouette of a woman at a window, city lights below, forbidden thoughts",
            "Black rose on dark silk sheets, symbolic and mysterious",
        ],
    }
    default = [f"Cinematic Indian storytelling scene {i+1}, emotional, high quality" for i in range(num_scenes)]
    scenes = fallbacks.get(channel, default)
    return (scenes * ((num_scenes // len(scenes)) + 1))[:num_scenes]


# ── Image Generation ─────────────────────────────────────────

def generate_scene_image(prompt: str, width: int = 1280, height: int = 720) -> bytes | None:
    """Generate a scene image using image_engine.py fallback chain."""
    try:
        from src.core.image_engine import generate_image
        result = generate_image(prompt=prompt, width=width, height=height)
        if result:
            return result
    except Exception as e:
        log.error(f"[video_engine] generate_scene_image failed: {e}")
    return None


# ── Subtitle Generation ──────────────────────────────────────

def _split_into_subtitle_lines(script: str, max_chars: int = 40) -> list[str]:
    """
    Split a Hindi/Hinglish script into subtitle lines.
    Splits on sentence boundaries (। | . | ? | !) then wraps long lines.
    """
    # Split on Devanagari danda (।), period, question mark, exclamation
    raw_sentences = re.split(r'[।\.!\?]+', script)
    lines = []
    for s in raw_sentences:
        s = s.strip()
        if not s:
            continue
        # Wrap long sentences into chunks of max_chars
        while len(s) > max_chars:
            # Find a space or comma near the limit
            cut = s.rfind(' ', 0, max_chars)
            if cut == -1:
                cut = max_chars
            lines.append(s[:cut].strip())
            s = s[cut:].strip()
        if s:
            lines.append(s)
    return lines


def _generate_ass_subtitles(
    script: str,
    audio_duration: float,
    width: int,
    height: int,
    output_path: str,
) -> bool:
    """
    Generate an ASS subtitle file with proportional timing.
    Returns True on success.
    """
    lines = _split_into_subtitle_lines(script, max_chars=35 if width > height else 28)
    if not lines:
        return False

    # Find a Hindi-capable font
    font_name = "Noto Sans Devanagari"
    for fp in _HINDI_FONTS:
        if os.path.exists(fp):
            font_name = Path(fp).stem.split("-")[0].replace("Noto", "Noto ").strip()
            break

    # Font size based on resolution
    font_size = 48 if width < height else 36  # bigger for vertical Shorts

    time_per_line = audio_duration / max(len(lines), 1)

    def _ts(seconds: float) -> str:
        """Convert seconds to ASS timestamp H:MM:SS.cc"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h}:{m:02d}:{int(s):02d}.{int((s % 1) * 100):02d}"

    # ASS header
    ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
Collisions: Normal

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,20,20,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    for i, line in enumerate(lines):
        start = i * time_per_line
        end = start + time_per_line - 0.05
        end = min(end, audio_duration)
        # Escape special ASS characters
        safe_line = line.replace("\\", "\\\\").replace("{", "\\{")
        ass += f"Dialogue: 0,{_ts(start)},{_ts(end)},Default,,0,0,0,,{safe_line}\n"

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass)
        return True
    except Exception as e:
        log.error(f"ASS subtitle write failed: {e}")
        return False


def _burn_subtitles_ffmpeg(video_path: str, ass_path: str, output_path: str) -> bool:
    """
    Use ffmpeg to burn ASS subtitles into the video.
    Returns True on success.
    """
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", video_path,
                "-vf", f"ass={ass_path}",
                "-c:a", "copy",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                output_path,
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            log.info(f"[VideoEngine] Subtitles burned in: {output_path}")
            return True
        log.error(f"[VideoEngine] ffmpeg subtitle burn failed: {result.stderr[-500:]}")
        return False
    except FileNotFoundError:
        log.warning("[VideoEngine] ffmpeg not found — skipping subtitle burn")
        return False
    except subprocess.TimeoutExpired:
        log.error("[VideoEngine] ffmpeg subtitle burn timed out")
        return False


# ── Video Rendering ──────────────────────────────────────────

@dataclass
class VideoSettings:
    thumbnail_path: str | None = None
    num_scenes: int = 7
    format: str = "shorts"
    add_subtitles: bool = True

def render_video(
    voice_path: str,
    script: str,
    channel: str,
    topic: str,
    settings: VideoSettings | None = None,
) -> str | None:
    """
    Main function: render a full MP4 from voice audio + AI scene images.

    Args:
        voice_path:     Path to .mp3 voice file (from voice_engine.py)
        script:         Full script text (for scene extraction + subtitles)
        channel:        YouTube channel name (for visual style)
        topic:          Video topic (for naming)
        settings:       Video settings containing format, scenes, subtitles configuration.

    Returns:
        Path to rendered .mp4 file, or None on failure.
    """
    if settings is None:
        settings = VideoSettings()
    try:
        from moviepy import (
            AudioFileClip, ImageClip, CompositeVideoClip,
            concatenate_videoclips, ColorClip
        )
    except ImportError:
        log.error("moviepy not installed. Run: pip install moviepy")
        return None

    if not voice_path or not os.path.exists(voice_path):
        log.error(f"Voice file not found: {voice_path}")
        return None

    width, height = _FORMATS.get(settings.format, _FORMATS["shorts"])
    log.info(f"[VideoEngine] Rendering {settings.format} ({width}×{height}) for '{channel}': {topic}")

    try:
        audio = AudioFileClip(voice_path)
        total_duration = audio.duration
        if not total_duration or total_duration <= 0:
            log.error("[VideoEngine] Audio file has no duration — cannot render video")
            try:
                audio.close()
            except Exception:
                pass
            return None
        log.info(f"[VideoEngine] Audio duration: {total_duration:.1f}s")

        # Step 1: Extract scene descriptions
        log.info("[VideoEngine] Extracting scene descriptions...")
        scene_descriptions = extract_scene_descriptions(script, channel, settings.num_scenes)

        # Step 2: Generate scene images
        log.info(f"[VideoEngine] Generating {len(scene_descriptions)} scene images...")
        image_paths = []

        if settings.thumbnail_path and os.path.exists(settings.thumbnail_path):
            image_paths.append(settings.thumbnail_path)
            scenes_to_generate = scene_descriptions[1:]
        else:
            scenes_to_generate = scene_descriptions

        for i, desc in enumerate(scenes_to_generate):
            log.info(f"[VideoEngine] Scene {i+1}/{len(scenes_to_generate)}: generating...")
            img_bytes = generate_scene_image(desc, width=width, height=height)
            if img_bytes:
                img_path = os.path.join(ASSETS_DIR, f"scene_{uuid.uuid4().hex[:6]}.png")
                with open(img_path, "wb") as f:
                    f.write(img_bytes)
                image_paths.append(img_path)
            else:
                log.warning(f"[VideoEngine] Scene {i+1} image failed, using color fill")

        if not image_paths:
            log.warning("[VideoEngine] No images generated. Using gradient background.")
            return _render_with_gradient(voice_path, audio, channel, topic, width, height)

        # Step 3: Build video clips with Ken Burns effect
        log.info("[VideoEngine] Stitching clips with Ken Burns effect...")
        clips = []
        clip_duration = total_duration / len(image_paths)

        for i, img_path in enumerate(image_paths):
            try:
                clip = _make_ken_burns_clip(img_path, clip_duration, i, width, height)
                if clip:
                    clips.append(clip)
            except Exception as e:
                log.warning(f"[VideoEngine] Clip {i} failed: {e}")
                color = [20, 20, 30] if "Riya" in channel else [30, 15, 40]
                clips.append(ColorClip(size=(width, height), color=color, duration=clip_duration))

        if not clips:
            return None

        # Step 4: Concatenate + add audio
        log.info("[VideoEngine] Concatenating clips and adding audio...")
        video = concatenate_videoclips(clips, method="compose")
        video = video.with_audio(audio)

        # Step 5: Export base video
        base_filename = f"video_{uuid.uuid4().hex[:8]}_base.mp4"
        base_path = os.path.join(VIDEO_DIR, base_filename)

        video.write_videofile(
            base_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=os.path.join(VIDEO_DIR, f"temp_audio_{uuid.uuid4().hex[:4]}.m4a"),
            remove_temp=True,
            logger=None,
        )

        # Cleanup scene images
        for p in image_paths:
            if p != settings.thumbnail_path:
                try:
                    Path(p).unlink(missing_ok=True)
                except Exception:
                    pass

        # Step 6: Burn Hindi subtitles via ffmpeg
        output_filename = f"video_{uuid.uuid4().hex[:8]}.mp4"
        output_path = os.path.join(VIDEO_DIR, output_filename)

        if settings.add_subtitles and script.strip():
            ass_path = os.path.join(VIDEO_DIR, f"subs_{uuid.uuid4().hex[:6]}.ass")
            subtitle_ok = _generate_ass_subtitles(script, total_duration, width, height, ass_path)
            if subtitle_ok:
                burned = _burn_subtitles_ffmpeg(base_path, ass_path, output_path)
                try:
                    Path(ass_path).unlink(missing_ok=True)
                except Exception:
                    pass
                if burned:
                    try:
                        Path(base_path).unlink(missing_ok=True)
                    except Exception:
                        pass
                    log.info(f"[VideoEngine] Final video with subtitles: {output_path}")
                    return output_path
            # Subtitle generation or burn failed — use base video
            log.warning("[VideoEngine] Subtitle burn failed — returning base video without subtitles")

        # No subtitles — rename base to final
        try:
            Path(base_path).rename(output_path)
        except Exception:
            output_path = base_path

        log.info(f"[VideoEngine] Video rendered: {output_path}")
        return output_path

    except Exception as e:
        log.error(f"[VideoEngine] Render failed: {e}")
        return None


def _make_ken_burns_clip(image_path: str, duration: float, index: int, width: int = 1280, height: int = 720):
    """
    Creates a VideoClip with Ken Burns effect (slow zoom in/out).
    Alternates zoom direction for visual variety.
    Supports both landscape (1280×720) and vertical (1080×1920).
    """
    import numpy as np
    from PIL import Image as PILImage

    try:
        img = PILImage.open(image_path).convert("RGB")
        img = img.resize((width, height), PILImage.LANCZOS)
        img_array = np.array(img)
    except Exception:
        return None

    zoom_start = 1.0 if index % 2 == 0 else 1.08
    zoom_end = 1.08 if index % 2 == 0 else 1.0

    def make_frame(t):
        progress = t / duration if duration > 0 else 0
        zoom = zoom_start + (zoom_end - zoom_start) * progress
        h, w = img_array.shape[:2]

        new_h = int(h / zoom)
        new_w = int(w / zoom)

        y1 = (h - new_h) // 2
        x1 = (w - new_w) // 2
        cropped = img_array[y1:y1+new_h, x1:x1+new_w]

        pil_crop = PILImage.fromarray(cropped).resize((w, h), PILImage.LANCZOS)
        return np.array(pil_crop)

    try:
        from moviepy import VideoClip
        clip = VideoClip(make_frame, duration=duration)
    except Exception:
        try:
            from moviepy.video.VideoClip import VideoClip as VideoClipV1
            clip = VideoClipV1(make_frame, duration=duration)
        except Exception:
            return None

    return clip


def _render_with_gradient(
    voice_path: str,
    audio,
    channel: str,
    topic: str,
    width: int = 1080,
    height: int = 1920,
) -> str | None:
    """
    Fallback: render video with a solid color background + audio when no images available.
    """
    try:
        from moviepy import ColorClip
        color = [20, 10, 30] if "Riya" in channel else [25, 10, 45]
        video = ColorClip(size=(width, height), color=color, duration=audio.duration)
        video = video.with_audio(audio)

        output_path = os.path.join(VIDEO_DIR, f"video_{uuid.uuid4().hex[:8]}.mp4")
        video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
        return output_path
    except Exception as e:
        log.error(f"Gradient fallback failed: {e}")
        return None


# ── Pro Post-Processing (FFmpeg) ─────────────────────────────
#
# Channel presets — call apply_channel_grade(video_path, channel) after render.
#
# "Story With Aisha" / "Aisha & Him" → warm_golden LUT, vignette 0.4, grain 8
# "Riya's Dark Whisper" / "Riya's Dark Romance Library" → cinematic LUT, vignette 0.7, grain 18

_CHANNEL_GRADE: dict = {
    "Story With Aisha":            {"lut": "warm_golden",  "vignette": 0.4, "grain": 8},
    "Aisha & Him":                 {"lut": "warm_golden",  "vignette": 0.4, "grain": 8},
    "Riya's Dark Whisper":         {"lut": "cinematic",    "vignette": 0.7, "grain": 18},
    "Riya's Dark Romance Library": {"lut": "cinematic",    "vignette": 0.7, "grain": 18},
}

# Inline 1D LUT curves stored as (r_pts, g_pts, b_pts) for ffmpeg curves filter
_LUT_CURVES: dict = {
    "cinematic": (
        "0/0 0.25/0.314 0.502/0.580 0.753/0.824 1/1",   # R
        "0/0 0.25/0.235 0.502/0.471 0.753/0.725 1/1",   # G
        "0.078/0.078 0.25/0.275 0.502/0.431 0.753/0.647 0.824/0.824",  # B — teal shadows
    ),
    "warm_golden": (
        "0/0 0.502/0.580 1/1",       # R — warm boost
        "0/0 0.502/0.502 1/0.941",   # G — slight pull
        "0/0 0.502/0.392 1/0.784",   # B — cool reduction
    ),
    "moody_blue": (
        "0/0 0.502/0.431 1/0.863",   # R — desaturate
        "0/0 0.502/0.451 1/0.902",   # G
        "0.118/0.118 0.502/0.580 1/1",  # B — boost blues
    ),
}


def add_film_grain(video_path: str, sigma: int = 10, output_path: str = None) -> str | None:
    """Add subtle film grain to video using ffmpeg geq filter. Returns output path."""
    try:
        out = output_path or video_path.replace(".mp4", "_grain.mp4")
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", (
                f"geq=lum='lum(X,Y)+({sigma}*(random(1)-0.5))':"
                f"cb='cb(X,Y)':"
                f"cr='cr(X,Y)'"
            ),
            "-c:a", "copy", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            out,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode == 0:
            return out
        log.warning(f"[VideoEngine] film grain failed: {result.stderr.decode()[:200]}")
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        log.warning(f"[VideoEngine] film grain error: {e}")
        return None


def add_vignette(video_path: str, opacity: float = 0.5, output_path: str = None) -> str | None:
    """Add cinematic vignette overlay using ffmpeg. opacity 0.0–1.0. Returns output path."""
    try:
        out = output_path or video_path.replace(".mp4", "_vignette.mp4")
        angle = 3.14159 / 5  # ~36° — classic cinema vignette angle
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"vignette=angle={angle}:mode=forward:eval=init",
            "-c:a", "copy", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            out,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode == 0:
            return out
        log.warning(f"[VideoEngine] vignette failed: {result.stderr.decode()[:200]}")
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        log.warning(f"[VideoEngine] vignette error: {e}")
        return None


def apply_lut_curves(video_path: str, lut_name: str = "cinematic", output_path: str = None) -> str | None:
    """Apply colour grading LUT curves via ffmpeg curves filter. Returns output path."""
    curves = _LUT_CURVES.get(lut_name, _LUT_CURVES["cinematic"])
    try:
        out = output_path or video_path.replace(".mp4", f"_{lut_name}.mp4")
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"curves=red='{curves[0]}':green='{curves[1]}':blue='{curves[2]}'",
            "-c:a", "copy", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            out,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode == 0:
            return out
        log.warning(f"[VideoEngine] LUT curves failed: {result.stderr.decode()[:200]}")
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        log.warning(f"[VideoEngine] LUT curves error: {e}")
        return None


def stabilize_video(video_path: str, output_path: str = None) -> str | None:
    """
    Apply ffmpeg vidstab two-pass stabilization.
    Requires ffmpeg compiled with libvidstab. Falls back gracefully if not available.
    """
    try:
        trf_path = video_path.replace(".mp4", ".trf")
        out = output_path or video_path.replace(".mp4", "_stable.mp4")

        # Pass 1: analyse
        pass1 = subprocess.run(
            ["ffmpeg", "-y", "-i", video_path,
             "-vf", f"vidstabdetect=stepsize=6:shakiness=5:result={trf_path}",
             "-f", "null", "-"],
            capture_output=True, timeout=180,
        )
        if pass1.returncode != 0:
            log.warning("[VideoEngine] vidstab pass1 failed (libvidstab may not be installed)")
            return None

        # Pass 2: apply
        pass2 = subprocess.run(
            ["ffmpeg", "-y", "-i", video_path,
             "-vf", f"vidstabtransform=input={trf_path}:smoothing=10,unsharp=5:5:0.8:3:3:0.4",
             "-c:a", "copy", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
             out],
            capture_output=True, timeout=180,
        )
        Path(trf_path).unlink(missing_ok=True)
        if pass2.returncode == 0:
            return out
        log.warning(f"[VideoEngine] vidstab pass2 failed: {pass2.stderr.decode()[:200]}")
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        log.warning(f"[VideoEngine] stabilize error: {e}")
        return None


def apply_channel_grade(video_path: str, channel: str) -> str:
    """
    Apply the full cinematic post-processing stack for a given channel.
    Runs: LUT curves → vignette → film grain (sequentially via ffmpeg).
    Falls back to the previous step's output if any ffmpeg call fails.
    Returns the best available output path.
    """
    preset = _CHANNEL_GRADE.get(channel, {"lut": "cinematic", "vignette": 0.5, "grain": 10})
    current = video_path

    # Step 1 — LUT colour grade
    lut_out = current.replace(".mp4", "_grade.mp4")
    result = apply_lut_curves(current, preset["lut"], lut_out)
    if result:
        current = result

    # Step 2 — Vignette
    vig_out = current.replace(".mp4", "_vig.mp4")
    result = add_vignette(current, preset["vignette"], vig_out)
    if result:
        current = result

    # Step 3 — Film grain
    grain_out = current.replace(".mp4", "_final.mp4")
    result = add_film_grain(current, preset["grain"], grain_out)
    if result:
        current = result

    log.info(f"[VideoEngine] Channel grade applied ({channel}): {current}")
    return current


# ── Quick Test ────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    voice = sys.argv[1] if len(sys.argv) > 1 else "temp_voice/test.mp3"
    fmt = sys.argv[2] if len(sys.argv) > 2 else "shorts"
    script = "एक खूबसूरत प्रेम कहानी जो ट्रेन में शुरू हुई। दो दिल, दो आत्माएं, एक सफर।"
    result = render_video(
        voice_path=voice,
        script=script,
        channel="Story With Aisha",
        topic="Train Romance",
        settings=VideoSettings(
            num_scenes=5,
            format=fmt,
            add_subtitles=True,
        )
    )
    print(f"Video: {result}")
