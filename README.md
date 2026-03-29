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

### Splash

Displays the application logo on startup for 3 seconds, then automatically transitions to the Shows screen.

### Shows

Browse your saved Spotify podcasts (up to 50, audiobooks excluded). Shows up to 5 rows at a time with a scrollbar when the list is longer. The selected row is highlighted with inverted colors.

```
┌─────────────────────────────────────┐
│  Podcasts                           │  ← title bar
├─────────────────────────────────────┤
│  Hardcore History                   │
│  ▶ The Daily                        │  ← selected
│  Huberman Lab                       │
│  Lex Fridman Podcast                │
│  Radiolab                           │
└─────────────────────────────────────┘
```

### Episodes

Lists the 20 most recent episodes for the selected podcast. Shows up to 4 rows at a time. Each row displays the episode name (up to 2 lines) plus the release date and duration.

```
┌─────────────────────────────────────┐
│  Hardcore History                   │  ← show name
├─────────────────────────────────────┤
│  Ep 67 - Supernova in the East      │
│  Mar 15  ·  6h 04m                  │
├─────────────────────────────────────┤
│  ▶ Ep 66 - Celtic Holocaust         │  ← selected
│  Jan 02  ·  5h 41m                  │
├─────────────────────────────────────┤
│  Ep 65 - The Destroyer of Worlds    │
│  Nov 20  ·  3h 58m                  │
└─────────────────────────────────────┘
```

### Now Playing

Shows the currently playing episode with playback controls and progress. Auto-refreshes every 10 seconds. If no device is active, displays a message prompting you to start playback on a Spotify device.

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

### Loading

A transient screen with centered text (e.g. "Loading…") shown while fetching data from the Spotify API.

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

The run loop script (`scripts/run_loop.sh`) automatically checks for remote updates every 30 seconds. When a new commit is detected on `main`, it pulls the latest code and restarts the app — no manual intervention needed.

To update manually instead:

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
