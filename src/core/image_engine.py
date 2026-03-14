import os
import requests
import io
import logging

log = logging.getLogger("Aisha.ImageEngine")

# Model waterfall — try in order until one works
# HuggingFace Inference API (free tier, serverless)
_HF_MODELS = [
    "black-forest-labs/FLUX.1-dev",           # Best quality (may need approval)
    "stabilityai/stable-diffusion-xl-base-1.0", # Reliable SDXL
    "runwayml/stable-diffusion-v1-5",           # Classic fallback
    "CompVis/stable-diffusion-v1-4",            # Oldest, most reliable
]

def generate_image(prompt: str) -> bytes:
    """
    Generate an image using HuggingFace Inference API.
    Tries multiple models in order — returns bytes on success, None on failure.
    """
    api_key = os.getenv("HUGGINGFACE_API_KEY")
    if not api_key or "your_" in api_key or len(api_key) < 10:
        log.warning("Missing or invalid HuggingFace API key.")
        return None

    headers = {"Authorization": f"Bearer {api_key}"}

    for model in _HF_MODELS:
        url = f"https://api-inference.huggingface.co/models/{model}"
        try:
            resp = requests.post(
                url,
                headers=headers,
                json={
                    "inputs": prompt,
                    "parameters": {
                        "num_inference_steps": 20,
                        "guidance_scale": 7.5,
                    }
                },
                timeout=60
            )
            if resp.status_code == 200 and resp.content and len(resp.content) > 1000:
                log.info(f"Image generated via {model} — {len(resp.content)} bytes")
                return resp.content
            elif resp.status_code == 503:
                log.warning(f"[{model}] Loading (503). Skipping.")
                continue
            elif resp.status_code in (404, 410):
                log.warning(f"[{model}] Not available ({resp.status_code}). Trying next.")
                continue
            else:
                log.warning(f"[{model}] {resp.status_code}: {resp.text[:100]}")
                continue
        except Exception as e:
            log.error(f"[{model}] Error: {e}")
            continue

    log.error("All HuggingFace image models failed.")
    return None
