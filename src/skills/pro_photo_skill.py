"""
pro_photo_skill.py
==================
Professional photo editing skills for Aisha.
Provides auto-correction, background removal, and cinematic colour grading
as @aisha_skill tools callable from Telegram or the agent pipeline.

All heavy imports (cv2, rembg, PIL) are lazy so the module loads safely
even if optional packages are missing on the deployment server.
"""
from pathlib import Path

from src.skills.skill_registry import aisha_skill


@aisha_skill
def auto_correct_photo(image_path: str) -> str:
    """Auto-correct a photo: grey-world white balance, CLAHE exposure, unsharp-mask sharpening. Returns path to corrected file."""
    try:
        import cv2
        import numpy as np

        img = cv2.imread(image_path)
        if img is None:
            return f"Error: could not read image at {image_path}"

        # ── Grey-world white balance ──────────────────────────────────
        b, g, r = cv2.split(img.astype(np.float32))
        mean_b, mean_g, mean_r = b.mean(), g.mean(), r.mean()
        overall_mean = (mean_b + mean_g + mean_r) / 3.0
        b = np.clip(b * (overall_mean / (mean_b + 1e-6)), 0, 255)
        g = np.clip(g * (overall_mean / (mean_g + 1e-6)), 0, 255)
        r = np.clip(r * (overall_mean / (mean_r + 1e-6)), 0, 255)
        img = cv2.merge([b, g, r]).astype(np.uint8)

        # ── CLAHE on L channel in LAB ──────────────────────────────────
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l_ch, a_ch, b_ch = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_ch = clahe.apply(l_ch)
        img = cv2.cvtColor(cv2.merge([l_ch, a_ch, b_ch]), cv2.COLOR_LAB2BGR)

        # ── Unsharp mask ───────────────────────────────────────────────
        blurred = cv2.GaussianBlur(img, (0, 0), 1.0)
        img = cv2.addWeighted(img, 1.5, blurred, -0.5, 0)

        stem = Path(image_path).stem
        out_path = str(Path(image_path).parent / f"{stem}_corrected.jpg")
        cv2.imwrite(out_path, img)
        return out_path

    except Exception as e:
        return f"auto_correct_photo error: {e}"


@aisha_skill
def remove_background(image_path: str) -> str:
    """Remove background from a photo using rembg (U-2-Net). Returns path to PNG with transparent background."""
    try:
        from rembg import remove
        from PIL import Image

        input_image = Image.open(image_path).convert("RGBA")
        output_image = remove(input_image)

        stem = Path(image_path).stem
        out_path = str(Path(image_path).parent / f"{stem}_nobg.png")
        output_image.save(out_path)
        return out_path

    except Exception as e:
        return f"remove_background error: {e}"


@aisha_skill
def color_grade_photo(image_path: str, style: str = "cinematic") -> str:
    """Apply cinematic color grading via 1D LUT curves. Styles: cinematic, warm_golden, moody_blue, real_estate. Returns path to graded file."""
    try:
        import cv2
        import numpy as np

        img = cv2.imread(image_path)
        if img is None:
            return f"Error: could not read image at {image_path}"

        # ── LUT definitions (B, G, R channel control points) ──────────
        luts = {
            "cinematic": {          # Orange & Teal
                "r": ([0, 64, 128, 192, 255], [0, 80, 148, 210, 255]),
                "g": ([0, 64, 128, 192, 255], [0, 60, 120, 185, 255]),
                "b": ([0, 64, 128, 192, 255], [20, 70, 110, 165, 210]),
            },
            "warm_golden": {
                "r": ([0, 128, 255], [0, 148, 255]),
                "g": ([0, 128, 255], [0, 128, 240]),
                "b": ([0, 128, 255], [0, 100, 200]),
            },
            "moody_blue": {
                "r": ([0, 128, 255], [0, 110, 220]),
                "g": ([0, 128, 255], [0, 115, 230]),
                "b": ([0, 128, 255], [30, 148, 255]),
            },
            "real_estate": {        # Bright, clean, daylight
                "r": ([0, 128, 255], [10, 140, 255]),
                "g": ([0, 128, 255], [10, 138, 255]),
                "b": ([0, 128, 255], [10, 130, 245]),
            },
        }

        grade = luts.get(style, luts["cinematic"])
        x_in = np.arange(256, dtype=np.float32)

        def build_lut(x_pts, y_pts):
            return np.clip(
                np.interp(x_in, x_pts, y_pts), 0, 255
            ).astype(np.uint8)

        lut_b = build_lut(*grade["b"])
        lut_g = build_lut(*grade["g"])
        lut_r = build_lut(*grade["r"])

        b_ch, g_ch, r_ch = cv2.split(img)
        b_ch = cv2.LUT(b_ch, lut_b)
        g_ch = cv2.LUT(g_ch, lut_g)
        r_ch = cv2.LUT(r_ch, lut_r)
        graded = cv2.merge([b_ch, g_ch, r_ch])

        stem = Path(image_path).stem
        out_path = str(Path(image_path).parent / f"{stem}_graded.jpg")
        cv2.imwrite(out_path, graded)
        return out_path

    except Exception as e:
        return f"color_grade_photo error: {e}"
