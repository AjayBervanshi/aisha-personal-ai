#!/usr/bin/env python3
"""
generate_icons.py
=================
Generates PWA icons for Aisha's web app.
Run: python scripts/generate_icons.py
Outputs: src/web/icons/icon-192.png and icon-512.png
"""

import os
import sys
from pathlib import Path

# Fix Windows cp1252 console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def generate_icons():
    """Generate PWA icons using only Python stdlib + optional Pillow."""
    icons_dir = Path(__file__).parent.parent / "src" / "web" / "icons"
    icons_dir.mkdir(exist_ok=True)

    try:
        from PIL import Image, ImageDraw, ImageFont
        _generate_with_pillow(icons_dir)
    except ImportError:
        print("Pillow not installed — generating SVG icons instead.")
        _generate_svg_icons(icons_dir)


def _generate_with_pillow(icons_dir: Path):
    from PIL import Image, ImageDraw

    for size in [192, 512]:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Background circle — deep purple
        margin = size // 10
        draw.ellipse(
            [margin, margin, size - margin, size - margin],
            fill=(26, 10, 46, 255)   # #1a0a2e
        )

        # Gradient ring — accent purple
        ring = size // 20
        draw.ellipse(
            [margin, margin, size - margin, size - margin],
            outline=(155, 89, 245, 255),  # #9b59f5
            width=ring
        )

        # Heart emoji approximation — draw a simple "A" for Aisha
        font_size = size // 2
        try:
            from PIL import ImageFont
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

        text = "A"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (size - text_w) // 2
        y = (size - text_h) // 2
        draw.text((x, y), text, fill=(196, 132, 252, 255), font=font)

        path = icons_dir / f"icon-{size}.png"
        img.save(path, "PNG")
        print(f"  ✅ Generated {path.name} ({size}x{size})")


def _generate_svg_icons(icons_dir: Path):
    """Generate SVG icons as fallback."""
    for size in [192, 512]:
        font_size = size * 0.45
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1a0a2e"/>
      <stop offset="100%" style="stop-color:#2a1645"/>
    </linearGradient>
    <linearGradient id="ring" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#9b59f5"/>
      <stop offset="100%" style="stop-color:#f472b6"/>
    </linearGradient>
  </defs>
  <!-- Background -->
  <circle cx="{size//2}" cy="{size//2}" r="{size//2}" fill="url(#bg)"/>
  <!-- Ring -->
  <circle cx="{size//2}" cy="{size//2}" r="{size//2 - size//20}" 
          fill="none" stroke="url(#ring)" stroke-width="{size//25}"/>
  <!-- Letter A -->
  <text x="50%" y="56%" font-family="Arial, sans-serif" 
        font-size="{font_size}" font-weight="bold"
        fill="#c084fc" text-anchor="middle" dominant-baseline="middle">A</text>
  <!-- Heart dot -->
  <circle cx="{size * 0.65}" cy="{size * 0.35}" r="{size//25}" fill="#f472b6"/>
</svg>"""
        # Save as SVG (rename to .png for manifest compatibility note)
        svg_path = icons_dir / f"icon-{size}.svg"
        png_path = icons_dir / f"icon-{size}.png"
        svg_path.write_text(svg)
        # Copy as .png reference (browser will still use SVG)
        svg_path.rename(png_path)
        print(f"  ✅ Generated {png_path.name} (SVG format, {size}x{size})")

    print("\n  Note: SVG icons generated. For true PNG, run:")
    print("  pip install Pillow && python scripts/generate_icons.py")


if __name__ == "__main__":
    print("\n🎨 Generating Aisha PWA icons...\n")
    generate_icons()
    print("\n✅ Icons ready! They're in src/web/icons/\n")
