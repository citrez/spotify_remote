"""Spotify API wrapper for podcast browsing and playback control."""

from dataclasses import dataclass
from typing import Optional
import spotipy
from spotipy.oauth2 import SpotifyOAuth

from . import config

SCOPES = [
    "user-library-read",
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
]


class NoActiveDeviceError(Exception):
    """Raised when no Spotify device is currently open."""


@dataclass
class Show:
    id: str
    name: str
    publisher: str
    total_episodes: int


@dataclass
class Episode:
    id: str
    name: str
    duration_ms: int
    release_date: str
    resume_point_ms: int  # 0 if not started


@dataclass
class PlaybackState:
    is_playing: bool
    episode_name: str
    show_name: str
    progress_ms: int
    duration_ms: int


class SpotifyClient:
    def __init__(self):
        auth = SpotifyOAuth(
            client_id=config.SPOTIFY_CLIENT_ID,
            client_secret=config.SPOTIFY_CLIENT_SECRET,
            redirect_uri=config.SPOTIFY_REDIRECT_URI,
            scope=" ".join(SCOPES),
            cache_path=str(config.CACHE_PATH),
            open_browser=False,
        )
        self._sp = spotipy.Spotify(auth_manager=auth)

    def get_saved_shows(self, limit: int = 50) -> list[Show]:
        """Return the user's saved podcast shows."""
        results = self._sp.current_user_saved_shows(limit=limit)
        shows = []
        for item in results["items"]:
            s = item["show"]
            shows.append(Show(
                id=s["id"],
                name=s["name"],
                publisher=s["publisher"],
                total_episodes=s["total_episodes"],
            ))
        return shows

    def get_show_episodes(self, show_id: str, limit: int = 20) -> list[Episode]:
        """Return the most recent episodes for a show."""
        results = self._sp.show_episodes(show_id, limit=limit)
        episodes = []
        for ep in results["items"]:
            if ep is None:
                continue
            resume = ep.get("resume_point", {})
            episodes.append(Episode(
                id=ep["id"],
                name=ep["name"],
                duration_ms=ep["duration_ms"],
                release_date=ep["release_date"],
                resume_point_ms=resume.get("resume_position_ms", 0),
            ))
        return episodes

    def play_episode(self, episode_id: str, show_id: str) -> None:
        """Start playing an episode via its show context.

        Using context_uri + episode offset avoids a Spotify iOS crash that
        occurs when sending episode URIs directly via start_playback uris=[].
        """
        devices = self._sp.devices().get("devices", [])
        print(f"[spotify] devices: {[(d['name'], d['type'], d['is_active']) for d in devices]}")

        if not devices:
            raise NoActiveDeviceError()

        active = next((d for d in devices if d["is_active"]), None)
        kwargs = dict(
            context_uri=f"spotify:show:{show_id}",
            offset={"uri": f"spotify:episode:{episode_id}"},
        )

        if active:
            print(f"[spotify] playing on active device: {active['name']}")
            self._sp.start_playback(**kwargs)
        else:
            print(f"[spotify] waking inactive device: {devices[0]['name']}")
            self._sp.start_playback(device_id=devices[0]["id"], **kwargs)

    def toggle_playback(self) -> None:
        state = self._sp.current_playback()
        if state and state["is_playing"]:
            self._sp.pause_playback()
        elif state:
            self._sp.start_playback()

    def next_track(self) -> None:
        self._sp.next_track()

    def previous_track(self) -> None:
        self._sp.previous_track()

    def get_playback_state(self) -> Optional[PlaybackState]:
        state = self._sp.current_playback()
        if not state or not state.get("item"):
            return None
        item = state["item"]
        return PlaybackState(
            is_playing=state["is_playing"],
            episode_name=item.get("name", ""),
            show_name=item.get("show", {}).get("name", ""),
            progress_ms=state.get("progress_ms", 0),
            duration_ms=item.get("duration_ms", 0),
        )

    def format_duration(self, ms: int) -> str:
        minutes = ms // 60000
        seconds = (ms % 60000) // 1000
        if minutes >= 60:
            return f"{minutes // 60}h {minutes % 60}m"
        return f"{minutes}m {seconds:02d}s"
