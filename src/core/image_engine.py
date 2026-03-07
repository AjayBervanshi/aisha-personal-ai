import os
import requests
import io
import logging

log = logging.getLogger("Aisha.ImageEngine")

def generate_image(prompt: str) -> bytes:
    """Generate an image using huggingface API and return bytes."""
    api_key = os.getenv("HUGGINGFACE_API_KEY")
    if not api_key or "your_" in api_key:
        log.warning("Missing HuggingFace API key.")
        return None

    # FLUX.1 or Stable Diffusion XL
    # "black-forest-labs/FLUX.1-dev" or "stabilityai/stable-diffusion-xl-base-1.0"
    API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": prompt}, timeout=45)
        response.raise_for_status()
        return response.content
    except Exception as e:
        log.error(f"Image generation failed: {e}")
        return None
