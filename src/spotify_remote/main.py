"""
Spotify Remote — main entry point.

State machine:
  LOADING → SHOWS → LOADING → EPISODES → PLAYER
                 ↑                    ↑
                BACK                 BACK
"""

import signal
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from .buttons import BACK, DOWN, SELECT, UP, ButtonHandler
from .display import Display
from .spotify_client import Episode, PlaybackState, Show, SpotifyClient
from .ui import Screen, render_episodes, render_loading, render_player, render_shows

PLAYER_REFRESH_INTERVAL = 10  # seconds


@dataclass
class AppState:
    screen: Screen = Screen.LOADING
    shows: list[Show] = field(default_factory=list)
    episodes: list[Episode] = field(default_factory=list)
    selected_show_index: int = 0
    cursor: int = 0
    scroll_offset: int = 0
    playback: Optional[PlaybackState] = None


class App:
    def __init__(self):
        self._state = AppState()
        self._display = Display()
        self._spotify = SpotifyClient()
        self._lock = threading.Lock()
        self._running = True
        self._player_timer: Optional[threading.Timer] = None

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _render(self):
        s = self._state
        if s.screen == Screen.LOADING:
            img = render_loading()
        elif s.screen == Screen.SHOWS:
            img = render_shows(s.shows, s.cursor, s.scroll_offset)
        elif s.screen == Screen.EPISODES:
            show_name = s.shows[s.selected_show_index].name if s.shows else ""
            img = render_episodes(show_name, s.episodes, s.cursor, s.scroll_offset)
        elif s.screen == Screen.PLAYER:
            img = render_player(s.playback)
        else:
            return
        self._display.render(img)

    # ── Button actions ────────────────────────────────────────────────────────

    def on_action(self, action: str):
        with self._lock:
            s = self._state

            if s.screen == Screen.LOADING:
                return  # ignore input while loading

            if s.screen == Screen.SHOWS:
                self._handle_list_action(action, len(s.shows), self._select_show)

            elif s.screen == Screen.EPISODES:
                if action == BACK:
                    self._go_to_shows()
                else:
                    self._handle_list_action(action, len(s.episodes), self._select_episode)

            elif s.screen == Screen.PLAYER:
                if action == BACK:
                    self._cancel_player_refresh()
                    s.screen = Screen.EPISODES
                    s.cursor = 0
                    s.scroll_offset = 0
                    self._render()
                elif action == SELECT:
                    self._spotify.toggle_playback()
                    self._refresh_player()

    def _handle_list_action(self, action: str, total: int, on_select):
        s = self._state
        visible = 5  # applies to both show and episode lists (approximate)

        if action == UP:
            if s.cursor > 0:
                s.cursor -= 1
                if s.cursor < s.scroll_offset:
                    s.scroll_offset -= 1
                self._render()

        elif action == DOWN:
            if s.cursor < total - 1:
                s.cursor += 1
                if s.cursor >= s.scroll_offset + visible:
                    s.scroll_offset += 1
                self._render()

        elif action == SELECT:
            on_select(s.cursor)

    # ── Screen transitions ────────────────────────────────────────────────────

    def _go_to_shows(self):
        s = self._state
        s.screen = Screen.SHOWS
        s.cursor = s.selected_show_index
        s.scroll_offset = max(0, s.cursor - 2)
        self._render()

    def _select_show(self, index: int):
        s = self._state
        s.selected_show_index = index
        s.screen = Screen.LOADING
        self._render()

        def fetch():
            episodes = self._spotify.get_show_episodes(s.shows[index].id)
            with self._lock:
                s.episodes = episodes
                s.cursor = 0
                s.scroll_offset = 0
                s.screen = Screen.EPISODES
                self._render()

        threading.Thread(target=fetch, daemon=True).start()

    def _select_episode(self, index: int):
        s = self._state
        episode = s.episodes[index]
        s.screen = Screen.LOADING
        self._render()

        def play():
            self._spotify.play_episode(episode.id)
            time.sleep(1)  # brief pause for Spotify to register the play
            self._refresh_player()

        threading.Thread(target=play, daemon=True).start()

    # ── Player refresh ────────────────────────────────────────────────────────

    def _refresh_player(self):
        playback = self._spotify.get_playback_state()
        with self._lock:
            self._state.playback = playback
            self._state.screen = Screen.PLAYER
            self._render()
        self._schedule_player_refresh()

    def _schedule_player_refresh(self):
        self._cancel_player_refresh()
        if self._running:
            self._player_timer = threading.Timer(
                PLAYER_REFRESH_INTERVAL, self._refresh_player
            )
            self._player_timer.daemon = True
            self._player_timer.start()

    def _cancel_player_refresh(self):
        if self._player_timer:
            self._player_timer.cancel()
            self._player_timer = None

    # ── Startup ───────────────────────────────────────────────────────────────

    def _load_shows(self):
        self._state.screen = Screen.LOADING
        self._render()
        shows = self._spotify.get_saved_shows()
        with self._lock:
            self._state.shows = shows
            self._state.screen = Screen.SHOWS
            self._render()

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self):
        buttons = ButtonHandler(on_action=self.on_action)

        def shutdown(sig, frame):
            self._running = False

        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)

        try:
            self._load_shows()
            # Main thread just keeps the process alive; all work is event-driven
            while self._running:
                time.sleep(0.5)
        finally:
            self._cancel_player_refresh()
            self._display.sleep()
            buttons.cleanup()


def main():
    App().run()
