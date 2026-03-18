"""
GPIO button handler for the Seengreat/Waveshare 2.7" HAT.

Uses a polling loop in a background thread — more reliable than edge-detection
interrupts on newer Raspberry Pi OS kernels.

In mock mode (MOCK_DISPLAY=true) GPIO setup is skipped entirely.
"""

import threading
import time
from typing import Callable

from . import config

# Action constants
UP = "UP"
DOWN = "DOWN"
SELECT = "SELECT"
BACK = "BACK"

_PIN_TO_ACTION = {
    config.BTN_UP: UP,
    config.BTN_DOWN: DOWN,
    config.BTN_SELECT: SELECT,
    config.BTN_BACK: BACK,
}

_POLL_INTERVAL = 0.05   # seconds between reads
_DEBOUNCE_READS = 3     # consecutive LOW reads required to register a press


class ButtonHandler:
    def __init__(self, on_action: Callable[[str], None]):
        self._on_action = on_action
        self._running = False

        if config.MOCK_DISPLAY:
            return

        import RPi.GPIO as GPIO

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in _PIN_TO_ACTION:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def _poll_loop(self):
        import RPi.GPIO as GPIO

        # Track how many consecutive LOW reads each pin has seen
        counts = {pin: 0 for pin in _PIN_TO_ACTION}
        # Track whether the button is currently considered "held"
        held = {pin: False for pin in _PIN_TO_ACTION}

        while self._running:
            for pin, action in _PIN_TO_ACTION.items():
                if GPIO.input(pin) == GPIO.LOW:
                    counts[pin] += 1
                    if counts[pin] == _DEBOUNCE_READS and not held[pin]:
                        held[pin] = True
                        self._on_action(action)
                else:
                    counts[pin] = 0
                    held[pin] = False
            time.sleep(_POLL_INTERVAL)

    def cleanup(self):
        self._running = False
        if not config.MOCK_DISPLAY:
            import RPi.GPIO as GPIO
            GPIO.cleanup()
