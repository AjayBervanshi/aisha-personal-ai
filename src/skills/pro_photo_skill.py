import os
import cv2
import numpy as np
from PIL import Image, ImageEnhance
from src.skills.skill_registry import aisha_skill

def white_balance_grayworld(img):
    img_float = img.astype(np.float32)
    avg_b = np.mean(img_float[:, :, 0])
    avg_g = np.mean(img_float[:, :, 1])
    avg_r = np.mean(img_float[:, :, 2])
    avg_all = (avg_b + avg_g + avg_r) / 3
    img_float[:, :, 0] = np.clip(img_float[:, :, 0] * (avg_all / avg_b), 0, 255)
    img_float[:, :, 1] = np.clip(img_float[:, :, 1] * (avg_all / avg_g), 0, 255)
    img_float[:, :, 2] = np.clip(img_float[:, :, 2] * (avg_all / avg_r), 0, 255)
    return img_float.astype(np.uint8)

def auto_exposure(img):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

def enhance_vibrance(img, strength=1.3):
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    enhancer = ImageEnhance.Color(pil_img)
    enhanced = enhancer.enhance(strength)
    return cv2.cvtColor(np.array(enhanced), cv2.COLOR_RGB2BGR)

def sharpen_image(img, strength=1.5):
    blur = cv2.GaussianBlur(img, (0, 0), 3)
    sharpened = cv2.addWeighted(img, 1 + strength, blur, -strength, 0)
    return sharpened

@aisha_skill
def auto_correct_photo(input_path: str, output_path: str = "") -> str:
    """
    Performs professional automatic color correction on an image.
    Applies Grayworld White Balance, CLAHE Exposure fixing, Vibrance boost, and Unsharp Mask.
    Provide the input image path, and optionally an output path.
    """
    if not os.path.exists(input_path):
        return f"Error: Image '{input_path}' not found."

    if not output_path:
        name, ext = os.path.splitext(input_path)
        output_path = f"{name}_corrected{ext}"

    try:
        img = cv2.imread(input_path)
        if img is None:
            return f"Error: OpenCV could not read '{input_path}'."

        img = white_balance_grayworld(img)
        img = auto_exposure(img)
        img = enhance_vibrance(img, strength=1.2)
        img = sharpen_image(img, strength=0.8)

        cv2.imwrite(output_path, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return f"Successfully auto-corrected photo: {output_path}"
    except Exception as e:
        return f"Error auto-correcting photo: {e}"

@aisha_skill
def remove_background(input_path: str, output_path: str = "") -> str:
    """
    Professionally removes the background from an image using the rembg AI library.
    Provide the input image path, and optionally an output path.
    """
    from rembg import remove

    if not os.path.exists(input_path):
        return f"Error: Image '{input_path}' not found."

    if not output_path:
        name, ext = os.path.splitext(input_path)
        output_path = f"{name}_nobg.png"

    try:
        with open(input_path, "rb") as f:
            input_data = f.read()
        output_data = remove(input_data)

        with open(output_path, "wb") as f:
            f.write(output_data)

        return f"Successfully removed background and saved to: {output_path}"
    except Exception as e:
        return f"Error removing background: {e}"

def make_curve(gamma=1.0, lift=0, gain=1.0):
    curve = []
    for i in range(256):
        val = ((i / 255.0) ** gamma) * gain * 255 + lift
        curve.append(int(np.clip(val, 0, 255)))
    return curve

def apply_lut_1d(img, r_curve, g_curve, b_curve):
    lut_r = np.array(r_curve, dtype=np.uint8)
    lut_g = np.array(g_curve, dtype=np.uint8)
    lut_b = np.array(b_curve, dtype=np.uint8)
    result = img.copy()
    result[:, :, 2] = cv2.LUT(img[:, :, 2], lut_r)  # R
    result[:, :, 1] = cv2.LUT(img[:, :, 1], lut_g)  # G
    result[:, :, 0] = cv2.LUT(img[:, :, 0], lut_b)  # B
    return result

STYLES = {
    "warm_golden": {
        "r_gamma": 0.9, "r_lift": 10, "r_gain": 1.05,
        "g_gamma": 1.0, "g_lift": 5,  "g_gain": 1.0,
        "b_gamma": 1.1, "b_lift": 0,  "b_gain": 0.88,
        "saturation": 1.2, "contrast": 1.1
    },
    "cinematic": {
        "r_gamma": 0.85, "r_lift": 15, "r_gain": 1.1,
        "g_gamma": 1.0,  "g_lift": 5,  "g_gain": 0.95,
        "b_gamma": 1.15, "b_lift": 20, "b_gain": 0.85,
        "saturation": 1.1, "contrast": 1.2
    },
    "moody": {
        "r_gamma": 1.1, "r_lift": 0,  "r_gain": 0.95,
        "g_gamma": 1.0, "g_lift": 0,  "g_gain": 0.92,
        "b_gamma": 0.9, "b_lift": 5,  "b_gain": 1.05,
        "saturation": 0.75, "contrast": 1.3
    },
    "real_estate": {
        "r_gamma": 0.9, "r_lift": 5, "r_gain": 1.05,
        "g_gamma": 0.9, "g_lift": 5, "g_gain": 1.05,
        "b_gamma": 0.9, "b_lift": 8, "b_gain": 1.08,
        "saturation": 1.15, "contrast": 1.05
    }
}

@aisha_skill
def color_grade_photo(input_path: str, style: str = "cinematic", output_path: str = "") -> str:
    """
    Applies professional cinematic color grading to an image using 1D LUT curves.
    Available styles: 'warm_golden', 'cinematic', 'moody', 'real_estate'.
    """
    if style not in STYLES:
        return f"Error: Unknown style '{style}'. Available: {', '.join(STYLES.keys())}"

    if not os.path.exists(input_path):
        return f"Error: Image '{input_path}' not found."

    if not output_path:
        name, ext = os.path.splitext(input_path)
        output_path = f"{name}_{style}{ext}"

    try:
        s = STYLES[style]
        img = cv2.imread(input_path)
        if img is None:
            return f"Error: OpenCV could not read '{input_path}'."

        r_curve = make_curve(s["r_gamma"], s["r_lift"], s["r_gain"])
        g_curve = make_curve(s["g_gamma"], s["g_lift"], s["g_gain"])
        b_curve = make_curve(s["b_gamma"], s["b_lift"], s["b_gain"])
        img = apply_lut_1d(img, r_curve, g_curve, b_curve)

        pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        pil = ImageEnhance.Color(pil).enhance(s["saturation"])
        pil = ImageEnhance.Contrast(pil).enhance(s["contrast"])
        img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

        cv2.imwrite(output_path, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return f"Successfully applied '{style}' color grade: {output_path}"
    except Exception as e:
        return f"Error grading photo: {e}"
