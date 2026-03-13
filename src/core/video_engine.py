"""
video_engine.py
===============
Aisha's Video Render Engine.
Converts voice audio + AI-generated scene images into a proper MP4 video.

Flow:
  1. Extract 6-8 scene descriptions from the script using AI
  2. Generate scene images via HuggingFace API (FLUX.1-schnell)
  3. Stitch audio + images into MP4 using moviepy:
     - Ken Burns effect (slow pan/zoom) for visual interest
     - Smooth fade transitions between scenes
     - Audio overlay on image slideshow
  4. Return final video path

This is the standard format for Hindi storytelling YouTube channels.
"""

import os
import uuid
import json
import logging
import requests
import tempfile
from pathlib import Path

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


# ── Scene Extraction ─────────────────────────────────────────

def extract_scene_descriptions(script: str, channel: str, num_scenes: int = 7) -> list[str]:
    """
    Uses AI to extract visual scene descriptions from the script.
    Returns a list of image generation prompts.
    """
    try:
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return _fallback_scenes(channel, num_scenes)

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")

        # Channel-specific visual style
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

        response = model.generate_content(prompt)
        text = response.text.strip()

        # Clean and parse
        import re
        match = re.search(r'\[[\s\S]*\]', text)
        if match:
            scenes = json.loads(match.group(0))
            # Append style suffix to each prompt
            return [f"{s}. Style: {style}. Ultra HD, cinematic, 16:9 aspect ratio." for s in scenes[:num_scenes]]

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
    default = [
        f"Cinematic Indian storytelling scene {i+1}, emotional, high quality"
        for i in range(num_scenes)
    ]
    scenes = fallbacks.get(channel, default)
    return (scenes * ((num_scenes // len(scenes)) + 1))[:num_scenes]


# ── Image Generation ─────────────────────────────────────────

def generate_scene_image(prompt: str) -> bytes | None:
    """
    Generate a single scene image via HuggingFace API.
    Uses FLUX.1-schnell for speed (faster than dev model).
    """
    api_key = os.getenv("HUGGINGFACE_API_KEY")
    if not api_key or "your_" in api_key:
        log.warning("HuggingFace API key not set.")
        return None

    # Try FLUX.1-schnell first (fastest), fall back to SDXL
    models = [
        "black-forest-labs/FLUX.1-schnell",
        "stabilityai/stable-diffusion-xl-base-1.0",
    ]

    for model_url in models:
        try:
            api_url = f"https://api-inference.huggingface.co/models/{model_url}"
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "inputs": prompt,
                "parameters": {"width": 1280, "height": 720}  # 16:9 YouTube resolution
            }
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                return response.content
            log.warning(f"HuggingFace {model_url} returned {response.status_code}")
        except Exception as e:
            log.error(f"Image gen failed for {model_url}: {e}")
            continue

    return None


# ── Video Rendering ──────────────────────────────────────────

def render_video(
    voice_path: str,
    script: str,
    channel: str,
    topic: str,
    thumbnail_path: str = None,
    num_scenes: int = 7,
) -> str | None:
    """
    Main function: render a full MP4 from voice audio + AI scene images.

    Args:
        voice_path:     Path to .mp3 voice file (from voice_engine.py)
        script:         Full script text (for scene extraction)
        channel:        YouTube channel name (for visual style)
        topic:          Video topic (for naming)
        thumbnail_path: Optional pre-generated thumbnail to include as first frame
        num_scenes:     Number of scene images to generate (default 7)

    Returns:
        Path to rendered .mp4 file, or None on failure.
    """
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

    log.info(f"[VideoEngine] Rendering video for '{channel}': {topic}")

    try:
        # Load audio and get duration
        audio = AudioFileClip(voice_path)
        total_duration = audio.duration
        log.info(f"[VideoEngine] Audio duration: {total_duration:.1f}s")

        # Calculate time per scene
        time_per_scene = total_duration / num_scenes

        # Step 1: Extract scene descriptions
        log.info("[VideoEngine] Extracting scene descriptions...")
        scene_descriptions = extract_scene_descriptions(script, channel, num_scenes)

        # Step 2: Generate scene images
        log.info(f"[VideoEngine] Generating {len(scene_descriptions)} scene images via HuggingFace...")
        image_paths = []

        # Use thumbnail as first scene if available
        if thumbnail_path and os.path.exists(thumbnail_path):
            image_paths.append(thumbnail_path)
            scenes_to_generate = scene_descriptions[1:]
        else:
            scenes_to_generate = scene_descriptions

        for i, desc in enumerate(scenes_to_generate):
            log.info(f"[VideoEngine] Scene {i+1}/{len(scenes_to_generate)}: generating...")
            img_bytes = generate_scene_image(desc)
            if img_bytes:
                img_path = os.path.join(ASSETS_DIR, f"scene_{uuid.uuid4().hex[:6]}.png")
                with open(img_path, "wb") as f:
                    f.write(img_bytes)
                image_paths.append(img_path)
            else:
                log.warning(f"[VideoEngine] Scene {i+1} image failed, using color fill")

        # Fallback: if no images generated, use solid color background
        if not image_paths:
            log.warning("[VideoEngine] No images generated. Using gradient background.")
            return _render_with_gradient(voice_path, audio, channel, topic)

        # Step 3: Build video clips with Ken Burns effect
        log.info("[VideoEngine] Stitching clips with Ken Burns effect...")
        clips = []
        clip_duration = total_duration / len(image_paths)

        for i, img_path in enumerate(image_paths):
            try:
                clip = _make_ken_burns_clip(img_path, clip_duration, i)
                if clip:
                    clips.append(clip)
            except Exception as e:
                log.warning(f"[VideoEngine] Clip {i} failed: {e}")
                # Add a colored fill clip as fallback
                color = [20, 20, 30] if "Riya" in channel else [30, 15, 40]
                clips.append(ColorClip(size=(1280, 720), color=color, duration=clip_duration))

        if not clips:
            return None

        # Step 4: Concatenate + add audio
        log.info("[VideoEngine] Concatenating clips and adding audio...")
        video = concatenate_videoclips(clips, method="compose")
        video = video.with_audio(audio)

        # Step 5: Export
        output_filename = f"video_{uuid.uuid4().hex[:8]}.mp4"
        output_path = os.path.join(VIDEO_DIR, output_filename)

        video.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=os.path.join(VIDEO_DIR, f"temp_audio_{uuid.uuid4().hex[:4]}.m4a"),
            remove_temp=True,
            logger=None,  # Suppress verbose moviepy logs
        )

        # Cleanup scene images
        for p in image_paths:
            if p != thumbnail_path:  # Don't delete the original thumbnail
                try:
                    Path(p).unlink(missing_ok=True)
                except Exception:
                    pass

        log.info(f"[VideoEngine] Video rendered: {output_path}")
        return output_path

    except Exception as e:
        log.error(f"[VideoEngine] Render failed: {e}")
        return None


def _make_ken_burns_clip(image_path: str, duration: float, index: int):
    """
    Creates an ImageClip with Ken Burns effect (slow zoom in/out, slight pan).
    Alternates zoom direction for visual variety.
    """
    from moviepy import ImageClip
    import numpy as np
    from PIL import Image as PILImage

    # Load and resize image to 1280x720
    try:
        img = PILImage.open(image_path).convert("RGB")
        img = img.resize((1280, 720), PILImage.LANCZOS)
        img_array = np.array(img)
    except Exception:
        return None

    # Ken Burns: zoom from 1.0 to 1.08 (subtle, not jarring)
    zoom_start = 1.0 if index % 2 == 0 else 1.08
    zoom_end = 1.08 if index % 2 == 0 else 1.0

    def make_frame(t):
        progress = t / duration
        zoom = zoom_start + (zoom_end - zoom_start) * progress
        h, w = img_array.shape[:2]

        new_h = int(h / zoom)
        new_w = int(w / zoom)

        # Center crop
        y1 = (h - new_h) // 2
        x1 = (w - new_w) // 2
        cropped = img_array[y1:y1+new_h, x1:x1+new_w]

        # Resize back to 1280x720
        pil_crop = PILImage.fromarray(cropped).resize((w, h), PILImage.LANCZOS)
        return np.array(pil_crop)

    clip = ImageClip(img_array, duration=duration)
    clip = clip.transform(lambda get_frame, t: make_frame(t), apply_to="mask")

    return clip


def _render_with_gradient(voice_path: str, audio, channel: str, topic: str) -> str | None:
    """
    Fallback: render video with a solid color background + audio when no images available.
    """
    try:
        from moviepy import ColorClip
        color = [20, 10, 30] if "Riya" in channel else [25, 10, 45]
        video = ColorClip(size=(1280, 720), color=color, duration=audio.duration)
        video = video.with_audio(audio)

        output_path = os.path.join(VIDEO_DIR, f"video_{uuid.uuid4().hex[:8]}.mp4")
        video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
        return output_path
    except Exception as e:
        log.error(f"Gradient fallback failed: {e}")
        return None


# ── Quick Test ────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    voice = sys.argv[1] if len(sys.argv) > 1 else "temp_voice/test.mp3"
    script = "A beautiful love story between two people who meet on a train..."
    result = render_video(
        voice_path=voice,
        script=script,
        channel="Story With Aisha",
        topic="Train Romance",
        num_scenes=5,
    )
    print(f"Video: {result}")
