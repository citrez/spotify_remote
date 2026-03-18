import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SPOTIFY_CLIENT_ID = os.environ["SPOTIFY_CLIENT_ID"]
SPOTIFY_CLIENT_SECRET = os.environ["SPOTIFY_CLIENT_SECRET"]
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

CACHE_PATH = Path(os.getenv("SPOTIFY_CACHE_PATH", str(Path.home() / ".spotify_remote_cache")))

# Seengreat 2.7" display — 264x176 landscape
DISPLAY_WIDTH = 264
DISPLAY_HEIGHT = 176

# GPIO pin numbers (BCM) for Waveshare/Seengreat 2.7" HAT buttons
BTN_UP = 5
BTN_DOWN = 6
BTN_SELECT = 13
BTN_BACK = 19

# Display mock mode: set to True when developing off the Pi
MOCK_DISPLAY = os.getenv("MOCK_DISPLAY", "false").lower() == "true"
