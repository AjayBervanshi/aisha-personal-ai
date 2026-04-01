"""
video_engine.py
===============
Aisha's Hollywood Production Studio.
Takes a Hindi/English script and a master audio track, splits the script into logical scenes,
generates highly-specific images for each scene, burns in TikTok-style subtitles,
and stitches it all together perfectly synced to the audio.
"""

import os
import json
import logging
import subprocess
from typing import List, Dict

log = logging.getLogger("Aisha.VideoEngine")

def _split_script_into_scenes(script: str) -> List[Dict[str, str]]:
    """
    Uses Gemini to analyze the script and break it down into 3-5 second logical scenes.
    For each scene, it extracts the exact Hindi text (for subtitles) and generates an English prompt (for image generation).
    Returns: [{"text": "कुछ खिड़कियाँ...", "image_prompt": "Cinematic shot of a window at night, warm lighting"}, ...]
    """
    from src.core.ai_router import AIRouter

    system_prompt = """
    You are an expert Hollywood Storyboard Director and AI Prompter for YouTube Shorts.
    Break the following Hindi/English script into short, logical, emotional scenes (about 3-5 seconds of speaking time each).

    For each scene:
    1. Extract the EXACT spoken text (to be used as burned-in subtitles). Do not change the original language or words.
    2. Write a highly detailed, photorealistic, cinematic English prompt for an AI Image Generator (like Midjourney/DALL-E) that perfectly matches the emotion and setting of that specific text.

    Output strictly valid JSON in this format:
    {
      "scenes": [
        {
          "text": "The exact spoken words",
          "image_prompt": "A young man looking out a window at night, cinematic lighting, 4k, photorealistic"
        }
      ]
    }
    """

    try:
        router = AIRouter()
        # Use Gemini Pro for the best logical breakdown
        result = router.generate(system_prompt, script)
        import re
        match = re.search(r'\{.*\}', result.text, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            return data.get("scenes", [])
    except Exception as e:
        log.error(f"Failed to split script into scenes: {e}")

    # Fallback if AI fails: split by newlines or full stops
    scenes = []
    lines = [line.strip() for line in script.replace('.', '.|').replace('!', '!|').replace('?', '?|').split('|') if line.strip()]
    for line in lines:
        scenes.append({
            "text": line,
            "image_prompt": "Cinematic shot matching a dramatic romance story, photorealistic, highly detailed"
        })
    return scenes

def _get_audio_duration(audio_path: str) -> float:
    """Uses ffprobe to get the exact duration of an audio file in seconds.
    Falls back to a safe calculation if ffprobe is missing or fails."""

    if not os.path.exists(audio_path):
        log.error(f"File not found: {audio_path}")
        return 0.0

    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of",
        "default=noprint_wrappers=1:nokey=1", audio_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=True)
        return float(result.stdout.strip())
    except Exception as e:
        log.error(f"Failed to get audio duration via ffprobe: {e}")
        # Fallback 1: Try mutagen if installed
        try:
            from mutagen.mp3 import MP3
            audio = MP3(audio_path)
            return float(audio.info.length)
        except Exception as mut_e:
            log.warning(f"Mutagen fallback failed: {mut_e}")

        # Fallback 2: Estimate based on file size (assuming standard 192k mp3)
        # 192 kbps = 24 KB/s. So seconds = size_in_kb / 24
        size_kb = os.path.getsize(audio_path) / 1024
        est_duration = size_kb / 24.0
        if est_duration > 0.5:
            return float(est_duration)

        return 5.0 # Absolute worst-case fallback

def generate_scene_images(scenes: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Generates the image file for each scene using image_engine.py.
    Appends the 'image_path' to each scene dictionary.
    """
    from src.core.image_engine import generate_image

    output_dir = os.path.join("temp_video", "scenes")
    os.makedirs(output_dir, exist_ok=True)

    for i, scene in enumerate(scenes):
        prompt = scene.get("image_prompt", "Beautiful cinematic scene")
        try:
            image_bytes = generate_image(prompt)
            if image_bytes:
                img_path = os.path.join(output_dir, f"scene_{i:03d}.jpg")
                with open(img_path, "wb") as f:
                    f.write(image_bytes)
                scene["image_path"] = img_path
            else:
                log.warning(f"Failed to generate image for scene {i}")
                scene["image_path"] = None
        except Exception as e:
            log.error(f"Error generating image for scene {i}: {e}")
            scene["image_path"] = None

    return scenes

def produce_video(script: str, output_filename: str) -> str:
    """
    The Master Production Pipeline.
    1. Splits the script into scenes.
    2. Generates an image for each scene.
    3. Generates audio for each scene to ensure PERFECT sync.
    4. Burns in the Hindi subtitles over the image.
    5. Stitches the perfectly synced scene-videos into a master .mp4.
    """
    from src.core.voice_engine import generate_voice

    log.info("🎬 Starting Video Production Pipeline...")

    # 1. Break the script into logical chunks and generate prompts
    scenes = _split_script_into_scenes(script)
    if not scenes:
        return "Error: Could not parse script into scenes."

    # 2. Generate the visual assets
    log.info(f"📸 Generating {len(scenes)} cinematic images...")
    scenes = generate_scene_images(scenes)

    # 3 & 4. Process each scene individually (Audio + Image + Subtitles)
    scene_videos = []
    output_dir = os.path.join("temp_video", "renders")
    os.makedirs(output_dir, exist_ok=True)

    for i, scene in enumerate(scenes):
        text = scene.get("text", "")
        img_path = scene.get("image_path")

        if not text or not img_path:
            continue

        log.info(f"🎙️ Generating voiceover for scene {i+1}/{len(scenes)}...")
        # Generate audio for just this sentence
        # (Assuming Hindi/Hinglish romance style for YouTube Shorts)
        audio_path = generate_voice(text, language="Hindi", mood="romantic")
        if not audio_path:
            continue

        # Measure exact duration of the spoken sentence
        duration = _get_audio_duration(audio_path)

        # ffmpeg command to:
        # 1. Loop the image for exact duration of audio
        # 2. Overlay the audio
        # 3. Burn the text as a subtitle (drawtext filter)

        # Escape single quotes and colons for ffmpeg drawtext filter
        safe_text = text.replace("'", "\\'").replace(":", "\\:")

        # Center-bottom text, white with black outline, bold font, wrapped
        # Note: You need a Hindi-compatible TTF font installed (e.g. NotoSansDevanagari-Regular.ttf)
        # Using default Sans for now, assuming system fallback handles it.
        import textwrap
        # Wrap Hindi text so it doesn't overflow a 1080x1920 9:16 mobile screen
        wrapped = "\n".join(textwrap.wrap(safe_text, width=30))
        # ffmpeg drawtext uses carriage returns or multi-line files.
        # For simplicity, we can pass text via file to avoid shell escaping nightmare.
        txt_path = os.path.join(output_dir, f"scene_{i:03d}.txt")
        with open(txt_path, "w", encoding="utf-8") as tf:
            tf.write(wrapped)

        drawtext_filter = (
            f"drawtext=textfile='{txt_path}':"
            "fontcolor=white:"
            "fontsize=64:"
            "fontfile=/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf:" # Assuming Linux server
            "box=1:boxcolor=black@0.7:boxborderw=20:"
            "x=(w-text_w)/2:"
            "y=h-text_h-200" # Bottom third for TikTok/Reels
        )

        out_vid = os.path.join(output_dir, f"render_{i:03d}.mp4")

        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", img_path, "-i", audio_path,
            "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-t", str(duration), "-vf", drawtext_filter,
            out_vid
        ]

        try:
            log.info(f"🎞️ Rendering scene {i+1} video with burned-in subtitles...")
            subprocess.run(cmd, capture_output=True, check=True)
            scene_videos.append(out_vid)
        except subprocess.CalledProcessError as e:
            log.error(f"FFmpeg failed rendering scene {i}: {e.stderr.decode()}")

    # 5. Stitch all scene videos together using ffmpeg concat demuxer
    if not scene_videos:
        return "Error: No scenes were successfully rendered."

    log.info("🎥 Stitching master video together...")
    list_file_path = os.path.join(output_dir, "concat_list.txt")
    with open(list_file_path, "w") as f:
        for vid in scene_videos:
            # ffmpeg concat requires format: file '/path/to/file'
            # Must use absolute paths or paths relative to the text file
            f.write(f"file '{os.path.abspath(vid)}'\n")

    master_output = os.path.join("temp_video", output_filename)

    concat_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file_path,
        "-c", "copy", master_output
    ]

    try:
        subprocess.run(concat_cmd, capture_output=True, check=True)
        log.info(f"✅ Master video successfully produced: {master_output}")
        return master_output
    except subprocess.CalledProcessError as e:
        log.error(f"FFmpeg failed master stitch: {e.stderr.decode()}")
        return f"Error stitching master video: {e}"
