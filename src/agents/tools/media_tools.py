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
