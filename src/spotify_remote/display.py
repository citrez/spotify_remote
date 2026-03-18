"""
E-ink display abstraction.

Real mode  (MOCK_DISPLAY=false): writes PIL images to the Seengreat/Waveshare EPD.
Mock mode  (MOCK_DISPLAY=true):  saves each frame to preview.png — no GPIO needed.
"""

from PIL import Image

from . import config


class Display:
    def __init__(self):
        self._epd = None
        if not config.MOCK_DISPLAY:
            from .drivers.epd2in7 import EPD
            self._epd = EPD()
            self._epd.init()

    def render(self, image: Image.Image):
        """Push a 264×176 PIL image to the display (or save as preview.png)."""
        image = image.convert("1").resize(
            (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT)
        )

        if config.MOCK_DISPLAY:
            image.save("preview.png")
            print("[mock] Rendered to preview.png")
        else:
            # The EPD panel RAM is laid out in portrait (176×264).
            # Rotate landscape→portrait before packing bytes.
            portrait = image.rotate(90, expand=True)
            self._epd.display(portrait.tobytes())

    def clear(self):
        if config.MOCK_DISPLAY:
            img = Image.new("1", (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT), 1)
            img.save("preview.png")
        else:
            self._epd.clear(0xFF)

    def sleep(self):
        if not config.MOCK_DISPLAY and self._epd:
            self._epd.sleep()

    def close(self):
        if not config.MOCK_DISPLAY and self._epd:
            self._epd.close()
