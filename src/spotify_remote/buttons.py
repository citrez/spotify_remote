"""
GPIO button handler for the Seengreat/Waveshare 2.7" HAT.

Four buttons fire callbacks via interrupt (no polling).
In mock mode (MOCK_DISPLAY=true) the GPIO setup is skipped entirely —
buttons can be simulated by calling the action callbacks directly.
"""

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


class ButtonHandler:
    def __init__(self, on_action: Callable[[str], None]):
        self._on_action = on_action

        if config.MOCK_DISPLAY:
            return  # no GPIO in mock/dev mode

        import RPi.GPIO as GPIO

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        for pin in _PIN_TO_ACTION:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.remove_event_detect(pin)  # clear any leftover state from previous runs
            GPIO.add_event_detect(
                pin,
                GPIO.FALLING,
                callback=self._gpio_callback,
                bouncetime=300,  # ms debounce
            )

    def _gpio_callback(self, pin: int):
        action = _PIN_TO_ACTION.get(pin)
        if action:
            self._on_action(action)

    def cleanup(self):
        if not config.MOCK_DISPLAY:
            import RPi.GPIO as GPIO
            GPIO.cleanup()
