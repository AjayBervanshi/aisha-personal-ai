import os
import base64
import requests
import logging

log = logging.getLogger("Aisha.ImageEngine")

# ── Gemini Imagen models (primary — requires paid plan) ──────────────────────
_IMAGEN_MODELS = [
    "imagen-4.0-generate-preview-06-06",
    "imagen-4.0-ultra-generate-preview-06-06",
    "imagen-3.0-generate-002",
    "imagen-3.0-generate-001",
]

# ── HuggingFace fallback models ──────────────────────────────────────────────
_HF_MODELS = [
    "black-forest-labs/FLUX.1-dev",
    "stabilityai/stable-diffusion-xl-base-1.0",
    "runwayml/stable-diffusion-v1-5",
    "CompVis/stable-diffusion-v1-4",
]


def _generate_via_gemini(prompt: str) -> bytes | None:
    """Try Gemini Imagen 4 first — requires paid Gemini plan."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    for model in _IMAGEN_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateImages?key={api_key}"
        try:
            resp = requests.post(
                url,
                json={
                    "prompt": {"text": prompt},
                    "number_of_images": 1,
                    "aspect_ratio": "16:9",
                    "safety_filter_level": "BLOCK_ONLY_HIGH",
                },
                timeout=60,
            )
            if resp.status_code == 200:
                data = resp.json()
                images = data.get("generatedImages") or data.get("predictions", [])
                for img in images:
                    b64 = img.get("bytesBase64Encoded") or img.get("image", {}).get("bytesBase64Encoded")
                    if b64:
                        log.info(f"Image generated via Gemini {model}")
                        return base64.b64decode(b64)
            elif resp.status_code == 400 and "paid" in resp.text.lower():
                log.warning("Gemini Imagen requires paid plan — skipping to HuggingFace")
                return None
            elif resp.status_code in (404, 429):
                log.warning(f"Gemini {model}: {resp.status_code} — trying next")
                continue
            else:
                log.warning(f"Gemini {model}: {resp.status_code} — {resp.text[:120]}")
                continue
        except Exception as e:
            log.error(f"Gemini {model} error: {e}")
            continue

    return None


def _generate_via_openai(prompt: str) -> bytes | None:
    """OpenAI DALL-E 3 — works on existing key, best quality after Gemini."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or "your_" in api_key:
        return None

    try:
        resp = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "dall-e-3",
                "prompt": prompt[:4000],
                "n": 1,
                "size": "1792x1024",  # 16:9 landscape
                "response_format": "b64_json",
                "quality": "standard",
            },
            timeout=90,
        )
        if resp.status_code == 200:
            data = resp.json()
            b64 = data["data"][0]["b64_json"]
            log.info("Image generated via OpenAI DALL-E 3")
            return base64.b64decode(b64)
        elif resp.status_code == 400:
            # Content policy — return None so we fall back to placeholder
            log.warning(f"DALL-E 3 content policy: {resp.json().get('error', {}).get('message', '')[:100]}")
            return None
        else:
            log.warning(f"DALL-E 3: {resp.status_code} — {resp.text[:100]}")
            return None
    except Exception as e:
        log.error(f"DALL-E 3 error: {e}")
        return None


def _generate_via_huggingface(prompt: str) -> bytes | None:
    """HuggingFace Inference API fallback."""
    api_key = os.getenv("HUGGINGFACE_API_KEY")
    if not api_key or "your_" in api_key or len(api_key) < 20:
        return None

    headers = {"Authorization": f"Bearer {api_key}"}

    for model in _HF_MODELS:
        url = f"https://api-inference.huggingface.co/models/{model}"
        try:
            resp = requests.post(
                url,
                headers=headers,
                json={"inputs": prompt, "parameters": {"num_inference_steps": 20, "guidance_scale": 7.5}},
                timeout=60,
            )
            if resp.status_code == 200 and resp.content and len(resp.content) > 1000:
                log.info(f"Image generated via HuggingFace {model} — {len(resp.content)} bytes")
                return resp.content
            elif resp.status_code in (503, 404, 410, 401):
                log.warning(f"HuggingFace {model}: {resp.status_code}")
                continue
            else:
                log.warning(f"HuggingFace {model}: {resp.status_code} — {resp.text[:100]}")
                continue
        except Exception as e:
            log.error(f"HuggingFace {model} error: {e}")
            continue

    return None


def _generate_placeholder(prompt: str, width: int = 1280, height: int = 720) -> bytes:
    """Generate a styled gradient placeholder image via Pillow — always works."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io
        import hashlib

        # Deterministic pastel color from prompt hash
        h = int(hashlib.md5(prompt.encode()).hexdigest()[:6], 16)
        r = (h >> 16) & 0xFF
        g = (h >> 8) & 0xFF
        b = h & 0xFF
        bg = (max(40, r // 2), max(40, g // 2), max(40, b // 2))
        accent = (min(255, r + 80), min(255, g + 80), min(255, b + 80))

        img = Image.new("RGB", (width, height), bg)
        draw = ImageDraw.Draw(img)

        # Gradient-style bands
        for i in range(height):
            t = i / height
            cr = int(bg[0] + (accent[0] - bg[0]) * t)
            cg = int(bg[1] + (accent[1] - bg[1]) * t)
            cb = int(bg[2] + (accent[2] - bg[2]) * t)
            draw.line([(0, i), (width, i)], fill=(cr, cg, cb))

        # Text overlay
        text = prompt[:80] + ("…" if len(prompt) > 80 else "")
        try:
            font = ImageFont.truetype("arial.ttf", 32)
        except Exception:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((width - tw) // 2, (height - th) // 2), text, fill=(255, 255, 255), font=font)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        log.info(f"Placeholder image generated ({width}x{height})")
        return buf.getvalue()
    except Exception as e:
        log.error(f"Placeholder generation failed: {e}")
        return b""


def generate_image(prompt: str, width: int = 1280, height: int = 720) -> bytes:
    """
    Generate an image for the given prompt.
    Priority: Gemini Imagen → HuggingFace → Pillow placeholder.
    Returns bytes (PNG/JPEG). Returns empty bytes only if everything fails.
    """
    # 1. Try Gemini Imagen (best quality, needs paid plan)
    result = _generate_via_gemini(prompt)
    if result:
        return result

    # 2. Try OpenAI DALL-E 3 (working key, high quality)
    result = _generate_via_openai(prompt)
    if result:
        return result

    # 3. Try HuggingFace (free, needs valid key)
    result = _generate_via_huggingface(prompt)
    if result:
        return result

    # 4. Pillow placeholder — always works, keeps video pipeline alive
    log.warning("All image APIs failed — using placeholder")
    return _generate_placeholder(prompt, width, height)


# ── Video Generation ─────────────────────────────────────────────────────────

def generate_video(prompt: str, duration_seconds: int = 8, output_path: str = None) -> str | None:
    """
    Generate a short video clip from a text prompt.
    Priority: Gemini Veo 2 (paid) → OpenAI Sora (paid) → None
    Returns path to saved video file, or None if unavailable.

    Note: Both require paid plan upgrades.
    - Gemini Veo 2/3: upgrade at https://ai.dev/projects
    - OpenAI Sora: available on ChatGPT Plus/Pro tier
    When neither is available, use video_engine.py to stitch images + voice → MP4.
    """
    import tempfile, time

    # Try Gemini Veo
    result = _generate_video_via_gemini(prompt, duration_seconds)
    if result:
        if output_path:
            with open(output_path, "wb") as f:
                f.write(result)
            return output_path
        path = tempfile.mktemp(suffix=".mp4")
        with open(path, "wb") as f:
            f.write(result)
        return path

    log.warning("Video generation not available — use video_engine.py to stitch voice+images into MP4")
    return None


def _generate_video_via_gemini(prompt: str, duration_seconds: int = 8) -> bytes | None:
    """
    Gemini Veo 2/3 video generation (requires paid plan).
    Uses long-running operation polling.
    """
    import time

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    veo_models = ["veo-2.0-generate-001", "veo-3.0-generate-preview"]

    for model in veo_models:
        try:
            # Submit generation job
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateVideo?key={api_key}",
                json={
                    "prompt": {"text": prompt},
                    "video_generation_config": {
                        "duration_seconds": duration_seconds,
                        "aspect_ratio": "16:9",
                        "resolution": "720p",
                    },
                },
                timeout=30,
            )

            if resp.status_code == 400 and "paid" in resp.text.lower():
                log.warning("Gemini Veo requires paid plan")
                return None
            if resp.status_code not in (200, 202):
                log.warning(f"Veo {model}: {resp.status_code}")
                continue

            data = resp.json()
            op_name = data.get("name")
            if not op_name:
                continue

            # Poll for completion (max 5 minutes)
            for _ in range(60):
                time.sleep(5)
                poll = requests.get(
                    f"https://generativelanguage.googleapis.com/v1beta/{op_name}?key={api_key}",
                    timeout=15,
                )
                if poll.status_code != 200:
                    break
                op = poll.json()
                if op.get("done"):
                    # Download video URI
                    video_uri = (
                        op.get("response", {})
                        .get("videos", [{}])[0]
                        .get("video", {})
                        .get("uri")
                    )
                    if video_uri:
                        vresp = requests.get(video_uri, timeout=120)
                        if vresp.status_code == 200:
                            log.info(f"Video generated via Gemini {model} ({len(vresp.content)} bytes)")
                            return vresp.content
                    break

        except Exception as e:
            log.error(f"Gemini {model} video error: {e}")
            continue

    return None
