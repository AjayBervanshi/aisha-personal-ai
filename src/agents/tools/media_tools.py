import os
import requests
from crewai.tools import tool

@tool("Generate Audio")
def generate_audio(text: str, voice_style: str = "casual") -> str:
    """Uses ElevenLabs (via voice_engine) to convert the YouTube script into voice. Provide the text and style (casual/professional/motivational/angry/romantic)."""
    from src.core.voice_engine import generate_voice
    try:
        # Default to English for Youtube scripts
        path = generate_voice(text, language="English", mood=voice_style)
        if path:
            return f"Audio successfully generated and saved to {path}"
        return "Audio generation failed or fell back to EdgeTTS."
    except Exception as e:
        return f"Error generating audio: {e}"

@tool("Generate Image")
def generate_image(prompt: str) -> str:
    """Uses HuggingFace API (via image_engine) to generate visuals for the YouTube video. Provide a descriptive image prompt."""
    from src.core.image_engine import generate_image as gi
    try:
        # Generate image returns bytes, save to file
        image_bytes = gi(prompt)
        if image_bytes:
            filename = f"aisha_video_asset_{hash(prompt) % 10000}.jpg"
            save_path = os.path.join("temp_voice", filename) # Reuse temp dir
            os.makedirs("temp_voice", exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(image_bytes)
            return f"Image successfully generated and saved to {save_path}"
        return "Image generation failed."
    except Exception as e:
        return f"Error generating image: {e}"

@tool("Sync Video")
def sync_video(image_path: str, audio_path: str, output_filename: str) -> str:
    """Uses ffmpeg (via subprocess) to combine a static generated image and an audio file into an .mp4 video. Provide the paths to the image, the audio, and the desired output filename (e.g., 'final_video.mp4')."""
    import subprocess
    import os

    if not os.path.exists(image_path):
        return f"Error: Image '{image_path}' not found."
    if not os.path.exists(audio_path):
        return f"Error: Audio '{audio_path}' not found."

    output_path = os.path.join("temp_voice", output_filename)
    os.makedirs("temp_voice", exist_ok=True)

    try:
        # ffmpeg command: -loop 1 (loop the single image), -i image, -i audio, -c:v libx264 (video codec),
        # -tune stillimage, -c:a aac (audio codec), -b:a 192k (audio bitrate), -pix_fmt yuv420p (pixel format for compatibility),
        # -shortest (end video when the shortest input (the audio) ends)
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", image_path, "-i", audio_path,
            "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-shortest", output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return f"Video successfully synced and saved to {output_path}"
        else:
            return f"ffmpeg failed: {result.stderr}"
    except FileNotFoundError:
        return "Error: ffmpeg is not installed or not in PATH."
    except Exception as e:
        return f"Error syncing video: {e}"
