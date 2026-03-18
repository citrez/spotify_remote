#!/usr/bin/env python3
"""
Diagnostic script for Seengreat/Waveshare 2.7" e-ink display.

Run this on the Pi before starting the main app to verify the display
is wired correctly and the driver is working.

Usage:
    poetry run python scripts/check_display.py

Expected outcome: display clears to white, then shows a test pattern
with a border, "Hello Pi!" text, and a filled bar.
"""

import sys
import os
import time

# Allow running from the repo root without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

PASS = "\033[92m  PASS\033[0m"
FAIL = "\033[91m  FAIL\033[0m"
INFO = "\033[94m  INFO\033[0m"


def check(label: str, fn):
    print(f"  {label}...", end=" ", flush=True)
    try:
        result = fn()
        print(PASS)
        return result
    except Exception as e:
        print(f"{FAIL} — {e}")
        return None


def main():
    print("\n=== Spotify Remote — Display Diagnostic ===\n")

    # ── 1. SPI device ────────────────────────────────────────────────────────
    print("[ System checks ]")

    def check_spi():
        assert os.path.exists("/dev/spidev0.0"), (
            "/dev/spidev0.0 not found. Enable SPI via: sudo raspi-config → "
            "Interface Options → SPI → Enable, then reboot."
        )

    check("SPI device /dev/spidev0.0 present", check_spi)

    def check_gpio():
        import RPi.GPIO  # noqa: F401

    check("RPi.GPIO importable", check_gpio)

    def check_spidev():
        import spidev  # noqa: F401

    check("spidev importable", check_spidev)

    def check_pillow():
        from PIL import Image, ImageDraw, ImageFont  # noqa: F401

    check("Pillow importable", check_pillow)

    # ── 2. Driver init ───────────────────────────────────────────────────────
    print("\n[ Display hardware ]")

    from spotify_remote.drivers.epd2in7 import EPD, EPD_WIDTH, EPD_HEIGHT

    epd = check("EPD driver instantiated", EPD)
    if epd is None:
        print("\nCannot continue — driver failed to instantiate.")
        sys.exit(1)

    check("EPD init (reset + LUT upload)", epd.init)

    # ── 3. Clear ─────────────────────────────────────────────────────────────
    def do_clear():
        epd.clear(0xFF)  # white

    check("Clear display to white", do_clear)
    time.sleep(1)

    # ── 4. Test pattern ──────────────────────────────────────────────────────
    print("\n[ Test pattern ]")

    def draw_test_pattern():
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("1", (EPD_WIDTH, EPD_HEIGHT), 1)  # white background
        draw = ImageDraw.Draw(img)

        # Border
        draw.rectangle([0, 0, EPD_WIDTH - 1, EPD_HEIGHT - 1], outline=0)

        # Title bar
        draw.rectangle([0, 0, EPD_WIDTH - 1, 22], fill=0)

        # Try to load a font, fall back to default
        try:
            font_large = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14
            )
            font_small = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11
            )
        except OSError:
            font_large = ImageFont.load_default()
            font_small = font_large

        draw.text((6, 4), "Display Check", font=font_large, fill=1)

        draw.text((6, 30), "Hello, Pi!", font=font_large, fill=0)
        draw.text((6, 50), f"Resolution: {EPD_WIDTH} x {EPD_HEIGHT}", font=font_small, fill=0)
        draw.text((6, 65), "SPI: OK", font=font_small, fill=0)
        draw.text((6, 80), "GPIO: OK", font=font_small, fill=0)

        # Filled bar
        draw.rectangle([6, 100, EPD_WIDTH - 6, 116], outline=0)
        draw.rectangle([6, 100, (EPD_WIDTH - 6) // 2, 116], fill=0)
        draw.text((6, 120), "Progress bar test", font=font_small, fill=0)

        # Button labels
        draw.text((6, 145), "KEY1=UP  KEY2=DN  KEY3=SEL  KEY4=BCK", font=font_small, fill=0)

        # Convert to bytes (1-bit, packed)
        return img.tobytes()

    img_bytes = check("Render test pattern with PIL", draw_test_pattern)

    if img_bytes:
        def send_image():
            epd.display(img_bytes)

        check("Send test pattern to display", send_image)
        print(f"{INFO} Test pattern is now on the display — inspect it visually.")
        time.sleep(3)

    # ── 5. Sleep ─────────────────────────────────────────────────────────────
    check("Put display to sleep", epd.sleep)

    print("\n=== Done ===\n")
    print("If all checks passed and the test pattern looks correct,")
    print("the display is ready. Run the main app with:")
    print("  poetry run spotify-remote\n")


if __name__ == "__main__":
    main()
