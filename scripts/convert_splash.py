"""
Convert assets/splash.png to a 176x264 1-bit dithered image.

Saves a preview as assets/splash_preview.png (greyscale, easy to view on a Mac)
and assets/splash_converted.png (the actual 1-bit image used by the display).

Usage:
    python scripts/convert_splash.py
"""

from pathlib import Path
from PIL import Image

ASSETS = Path(__file__).parent.parent / "src" / "spotify_remote" / "assets"
SRC = ASSETS / "splash.png"
OUT_1BIT = ASSETS / "splash_converted.png"
OUT_PREVIEW = ASSETS / "splash_preview.png"

W, H = 176, 264


def convert():
    img = Image.open(SRC).convert("RGB")

    # Fit inside 176x264, preserving aspect ratio, centred on white background
    img.thumbnail((W, H), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H), (255, 255, 255))
    x = (W - img.width) // 2
    y = (H - img.height) // 2
    canvas.paste(img, (x, y))

    # Save greyscale preview (easy to inspect on a Mac)
    canvas.convert("L").save(OUT_PREVIEW)
    print(f"Preview saved: {OUT_PREVIEW}")

    # Convert to 1-bit with Floyd-Steinberg dithering
    bw = canvas.convert("1")
    bw.save(OUT_1BIT)
    print(f"1-bit image saved: {OUT_1BIT}")


if __name__ == "__main__":
    convert()
