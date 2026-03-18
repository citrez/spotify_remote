# Spotify Podcast Remote — Implementation Plan

## Overview

A minimal Python app for Raspberry Pi Zero WH + Seengreat 2.7" e-ink display.
Authenticates with Spotify, shows your saved podcasts, lets you browse episodes, and starts playback.
Acts as a **remote control** — playback happens on your phone, speaker, or any active Spotify device.

---

## Hardware

| Component | Detail |
|---|---|
| Board | Raspberry Pi Zero WH |
| Display | Seengreat 2.7" e-ink (264×176px, Waveshare-compatible SPI) |
| Buttons | 4 tactile buttons built into the HAT |

---

## Project Structure

```
src/spotify_remote/
├── config.py           ✅ done — env vars, display size, GPIO pin numbers
├── spotify_client.py   ✅ done — Spotify API (shows, episodes, playback)
├── drivers/
│   └── epd2in7.py      🔲 to build — low-level SPI driver for the display
├── display.py          🔲 to build — abstraction over driver (real + mock)
├── ui.py               🔲 to build — PIL renderer for all screens (incl. loading)
├── buttons.py          🔲 to build — GPIO button handler
└── main.py             🔲 to build — state machine + event loop

scripts/
└── check_display.py    🔲 to build — diagnostic script (run on Pi before main app)
```

---

## Screens

### Loading (shown while fetching from Spotify API)
```
┌────────────────────────────┐
│                            │
│                            │
│       Loading...           │
│                            │
│                            │
└────────────────────────────┘
```
Shown on startup (fetching shows) and when entering a show (fetching episodes).

### 1. Shows (startup)
```
┌────────────────────────────┐
│  Podcasts                  │  ← title bar
├────────────────────────────┤
│  Hardcore History          │  ← highlighted (selected)
│  Lex Fridman Podcast       │
│  99% Invisible             │
│  Radiolab                  │
│  Darknet Diaries           │
└────────────────────────────┘
```

### 2. Episodes (after selecting a show)
```
┌────────────────────────────┐
│  Hardcore History          │  ← show name as title
├────────────────────────────┤
│  Ep 67 - Supernova in the  │  ← highlighted
│  Mar 12 · 6h 04m           │  ← date + duration subtitle
│  Ep 66 - Wrath of the Kha… │
│  Jan 3 · 3h 55m            │
└────────────────────────────┘
```
Each episode takes 2 rows (name + date/duration), so ~4 episodes visible at a time.

### 3. Player (after selecting an episode)
```
┌────────────────────────────┐
│  ▶  Playing                │  ← auto-refreshes every 10s
│                            │
│  Hardcore History          │
│  Ep 67 - Supernova in...   │
│                            │
│  [████████░░░░░░] 1h12m    │
└────────────────────────────┘
```
SELECT on this screen toggles play/pause. Refreshes every 10s via background thread.

---

## Button Mapping

| Button | GPIO (BCM) | Action |
|---|---|---|
| KEY1 | 5 | UP — move cursor up |
| KEY2 | 6 | DOWN — move cursor down |
| KEY3 | 13 | SELECT — confirm / play / pause |
| KEY4 | 19 | BACK — go to previous screen |

---

## Navigation Flow

```
[LOADING] → [SHOWS] --SELECT--> [LOADING] → [EPISODES] --SELECT--> [PLAYER]
                        <--BACK--                           <--BACK--
```

Lists scroll when there are more than visible items.

---

## Spotify Authentication (headless Pi)

Uses Spotify's **Authorization Code Flow** via `spotipy`. Only needed once.

1. First run: app prints an auth URL to the terminal
2. Visit the URL on your phone or laptop, authorize the app
3. You'll be redirected to `http://127.0.0.1:8888/callback?code=...` — paste that full URL back into the terminal
4. Token is saved to `~/.spotify_remote_cache`
5. All future runs authenticate automatically from the cache

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your credentials from the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard):

```
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
MOCK_DISPLAY=false
```

Set `MOCK_DISPLAY=true` when developing on Mac — renders to `preview.png` instead of the real display, no GPIO needed.

---

## Installation on Pi (clone + update workflow)

```bash
# 1. One-time setup on the Pi
sudo apt update && sudo apt install -y python3-pip git pipx
pipx install poetry
pipx ensurepath && source ~/.bashrc

# 2. Clone the repo
git clone https://github.com/YOUR_USERNAME/spotify_remote.git
cd spotify_remote

# 3. Install dependencies
poetry install --extras pi

# 4. Copy and fill in credentials
cp .env.example .env
nano .env

# 5. (Optional) run diagnostic first
poetry run python scripts/check_display.py

# 6. Run the app
poetry run spotify-remote
```

**To update later** (pull changes and restart):
```bash
cd ~/spotify_remote
git pull
poetry install --extras pi   # only needed if dependencies changed
poetry run spotify-remote
```

**Optional — run on boot with systemd:**
A `spotify-remote.service` file will be included so you can enable auto-start with:
```bash
sudo cp spotify-remote.service /etc/systemd/system/
sudo systemctl enable spotify-remote
sudo systemctl start spotify-remote
```

---

## Diagnostic Script (`scripts/check_display.py`)

A standalone script to verify hardware is working before running the full app. It:

1. Checks SPI is enabled (`/dev/spidev0.0` exists)
2. Initialises the EPD driver
3. Clears the display (goes white)
4. Draws a test pattern: border, "Hello Pi!" text, and a filled rectangle
5. Prints PASS/FAIL for each step to stdout
6. Puts the display to sleep

Run it with: `poetry run python scripts/check_display.py`

---

## Dependencies

```toml
# Always installed
spotipy        # Spotify Web API
Pillow         # image rendering for e-ink
python-dotenv  # .env loading

# Pi only (poetry install --extras pi)
RPi.GPIO
spidev
```

---

## Development on Mac

```bash
MOCK_DISPLAY=true poetry run spotify-remote
# → renders each screen to preview.png, no GPIO needed
```
