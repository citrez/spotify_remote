"""
Waveshare 2.7" e-Paper display driver (SSD1680 controller).
Compatible with Seengreat 2.7" e-ink HAT.

Wiring (BCM pin numbers):
  VCC  → 3.3V
  GND  → GND
  DIN  → GPIO 10  (SPI0 MOSI)
  CLK  → GPIO 11  (SPI0 SCLK)
  CS   → GPIO 8   (SPI0 CE0)
  DC   → GPIO 25
  RST  → GPIO 17
  BUSY → GPIO 24
"""

import time
import RPi.GPIO as GPIO
import spidev

# Display resolution
EPD_WIDTH = 176
EPD_HEIGHT = 264

# GPIO pins (BCM)
RST_PIN = 17
DC_PIN = 25
CS_PIN = 8
BUSY_PIN = 24

# SSD1680 commands
_DRIVER_OUTPUT_CONTROL = 0x01
_BOOSTER_SOFT_START = 0x0C
_DEEP_SLEEP_MODE = 0x10
_DATA_ENTRY_MODE = 0x11
_SW_RESET = 0x12
_MASTER_ACTIVATION = 0x20
_DISPLAY_UPDATE_CTRL1 = 0x21
_DISPLAY_UPDATE_CTRL2 = 0x22
_WRITE_RAM_BW = 0x24
_WRITE_VCOM = 0x2C
_WRITE_LUT = 0x32
_BORDER_WAVEFORM = 0x3C
_SET_RAM_X = 0x44
_SET_RAM_Y = 0x45
_SET_RAM_X_COUNTER = 0x4E
_SET_RAM_Y_COUNTER = 0x4F

# Full-refresh LUT (waveform timing table)
_LUT_FULL = [
    0x80, 0x60, 0x40, 0x00, 0x00, 0x00, 0x00,
    0x10, 0x60, 0x20, 0x00, 0x00, 0x00, 0x00,
    0x80, 0x60, 0x40, 0x00, 0x00, 0x00, 0x00,
    0x10, 0x60, 0x20, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x03, 0x03, 0x00, 0x00, 0x02,
    0x09, 0x09, 0x00, 0x00, 0x02,
    0x03, 0x03, 0x00, 0x00, 0x02,
    0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00,
    0x15, 0x41, 0xA8, 0x32, 0x30,
    0x0A,
]


class EPD:
    def __init__(self):
        self._spi = spidev.SpiDev()
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(RST_PIN, GPIO.OUT)
        GPIO.setup(DC_PIN, GPIO.OUT)
        GPIO.setup(CS_PIN, GPIO.OUT)
        GPIO.setup(BUSY_PIN, GPIO.IN)

    # ── Low-level SPI helpers ────────────────────────────────────────────────

    def _spi_open(self):
        self._spi.open(0, 0)
        self._spi.max_speed_hz = 4000000
        self._spi.mode = 0b00

    def _send_command(self, command: int):
        GPIO.output(DC_PIN, GPIO.LOW)
        GPIO.output(CS_PIN, GPIO.LOW)
        self._spi.writebytes([command])
        GPIO.output(CS_PIN, GPIO.HIGH)

    def _send_data(self, data):
        GPIO.output(DC_PIN, GPIO.HIGH)
        GPIO.output(CS_PIN, GPIO.LOW)
        if isinstance(data, int):
            self._spi.writebytes([data])
        else:
            # send in chunks to avoid SPI buffer limits
            for i in range(0, len(data), 4096):
                self._spi.writebytes(data[i:i + 4096])
        GPIO.output(CS_PIN, GPIO.HIGH)

    def _wait_busy(self):
        while GPIO.input(BUSY_PIN) == GPIO.HIGH:
            time.sleep(0.01)

    def _reset(self):
        GPIO.output(RST_PIN, GPIO.HIGH)
        time.sleep(0.2)
        GPIO.output(RST_PIN, GPIO.LOW)
        time.sleep(0.002)
        GPIO.output(RST_PIN, GPIO.HIGH)
        time.sleep(0.2)

    # ── Public API ───────────────────────────────────────────────────────────

    def init(self):
        self._spi_open()
        self._reset()

        self._send_command(_SW_RESET)
        self._wait_busy()

        # Driver output: gate lines = EPD_HEIGHT - 1, scan direction
        self._send_command(_DRIVER_OUTPUT_CONTROL)
        self._send_data((EPD_HEIGHT - 1) & 0xFF)
        self._send_data(((EPD_HEIGHT - 1) >> 8) & 0xFF)
        self._send_data(0x00)

        # Data entry: X increment, Y increment, update in X direction
        self._send_command(_DATA_ENTRY_MODE)
        self._send_data(0x03)

        # Set RAM X range: 0 to (EPD_WIDTH/8 - 1)
        self._send_command(_SET_RAM_X)
        self._send_data(0x00)
        self._send_data((EPD_WIDTH // 8) - 1)

        # Set RAM Y range: 0 to (EPD_HEIGHT - 1)
        self._send_command(_SET_RAM_Y)
        self._send_data(0x00)
        self._send_data(0x00)
        self._send_data((EPD_HEIGHT - 1) & 0xFF)
        self._send_data(((EPD_HEIGHT - 1) >> 8) & 0xFF)

        self._send_command(_BORDER_WAVEFORM)
        self._send_data(0x05)

        self._send_command(_WRITE_VCOM)
        self._send_data(0x36)

        self._send_command(_WRITE_LUT)
        self._send_data(_LUT_FULL)

        # Set RAM counters to origin
        self._send_command(_SET_RAM_X_COUNTER)
        self._send_data(0x00)
        self._send_command(_SET_RAM_Y_COUNTER)
        self._send_data(0x00)
        self._send_data(0x00)

    def display(self, image_bytes: bytes):
        """Write a 1-bit image buffer to the display and trigger a refresh."""
        self._send_command(_SET_RAM_X_COUNTER)
        self._send_data(0x00)
        self._send_command(_SET_RAM_Y_COUNTER)
        self._send_data(0x00)
        self._send_data(0x00)

        self._send_command(_WRITE_RAM_BW)
        self._send_data(list(image_bytes))

        self._send_command(_DISPLAY_UPDATE_CTRL2)
        self._send_data(0xF7)
        self._send_command(_MASTER_ACTIVATION)
        self._wait_busy()

    def clear(self, color: int = 0xFF):
        """Fill the display with white (0xFF) or black (0x00)."""
        buf = [color] * (EPD_WIDTH // 8 * EPD_HEIGHT)
        self.display(bytes(buf))

    def sleep(self):
        """Put the display into deep sleep. Call init() to wake."""
        self._send_command(_DEEP_SLEEP_MODE)
        self._send_data(0x01)
        time.sleep(0.2)
        self._spi.close()

    def close(self):
        self.sleep()
        GPIO.cleanup()
