# Spotify Remote

A minimal Spotify remote control for **Raspberry Pi Zero WH** + **Seengreat 2.7" e-ink display**. Browse your saved podcasts, pick an episode, and control playback — all from a physical device with four buttons.

Playback happens on your phone, speaker, or any active Spotify device. The Pi just acts as the remote.

---

## Hardware

| Component | Detail |
|---|---|
| Board | Raspberry Pi Zero WH |
| Display | Seengreat 2.7" e-ink, 264×176px (Waveshare-compatible SPI) |
| Buttons | 4 tactile buttons built into the HAT |

---

## Screens

**Shows** — browse your saved podcasts
**Episodes** — pick from the 20 most recent episodes
**Now Playing** — see what's playing, track progress, and control playback

```
┌─────────────────────────────────────┐
│  Now Playing                        │  ← title bar
│  ▶  Playing                         │
│  Hardcore History                   │
│  Ep 67 - Supernova in the East      │
│                                     │
│  1h 12m / 6h 04m                    │
│  [████████░░░░░░░░░░░░░░░░░░░░░░]   │
├──────────────┬──────────┬───────────┤
│      ◀       │    ⏸     │     ▶     │
│     Prev     │  Pause   │   Next    │
└──────────────┴──────────┴───────────┘
```

---

## Button Mapping

| Button | GPIO (BCM) | Shows / Episodes | Now Playing |
|---|---|---|---|
| KEY1 | 5 | Move cursor up | Previous track |
| KEY2 | 6 | Move cursor down | Next track |
| KEY3 | 13 | Select / confirm | Play / Pause |
| KEY4 | 19 | Back | Back to episodes |

---

## Navigation

```
[SHOWS] --SELECT--> [EPISODES] --SELECT--> [NOW PLAYING]
           <--BACK--                <--BACK--
```

---

## Setup

### 1. Spotify credentials

Create an app at the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and note your Client ID and Secret. Set the redirect URI to `http://127.0.0.1:8888/callback`.

Copy `.env.example` to `.env` and fill in your values:

```
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
MOCK_DISPLAY=false
```

### 2. Install on the Pi

```bash
sudo apt update && sudo apt install -y python3-pip git pipx
pipx install poetry
pipx ensurepath && source ~/.bashrc

git clone https://github.com/citrez/spotify_remote.git
cd spotify_remote

poetry install --extras pi
cp .env.example .env
nano .env

poetry run spotify-remote
```

### 3. First run — Spotify auth

The app prints an auth URL. Open it on your phone or laptop, authorize, then paste the redirect URL back into the terminal. The token is cached at `~/.spotify_remote_cache` and reused automatically from then on.

---

## Updating

```bash
cd ~/spotify_remote
git pull
poetry install --extras pi   # only if dependencies changed
poetry run spotify-remote
```

---

## Run on boot (systemd)

```bash
sudo cp spotify-remote.service /etc/systemd/system/
sudo systemctl enable spotify-remote
sudo systemctl start spotify-remote
```

---

## Development on Mac

Set `MOCK_DISPLAY=true` to render screens to `preview.png` instead of the real display — no GPIO or SPI hardware needed:

```bash
MOCK_DISPLAY=true poetry run spotify-remote
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `spotipy` | Spotify Web API |
| `Pillow` | Image rendering for e-ink |
| `python-dotenv` | `.env` loading |
| `RPi.GPIO` *(Pi only)* | Button GPIO polling |
| `spidev` *(Pi only)* | SPI display driver |
