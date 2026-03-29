"""
PIL-based renderer for all screens.

Every render_* function takes the current app state and returns a PIL Image
(176×264, mode "1" — 1-bit black/white) ready to be pushed to the display.
"""

import textwrap
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from . import config
from .spotify_client import Episode, PlaybackState, Show

# ── Layout constants ──────────────────────────────────────────────────────────

W = config.DISPLAY_WIDTH   # 176
H = config.DISPLAY_HEIGHT  # 264

TITLE_H = 28        # height of the top title area (text + separator)
ROW_H = 28          # height of a show row
EP_ROW_H = 38       # height of an episode row (name + subtitle)
ROWS_VISIBLE = (H - TITLE_H) // ROW_H
EP_ROWS_VISIBLE = (H - TITLE_H) // EP_ROW_H

PADDING = 6


# ── Font loader ───────────────────────────────────────────────────────────────

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
        f"/usr/share/fonts/truetype/liberation/LiberationSans{'-Bold' if bold else ''}.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT_TITLE = _font(18, bold=True)
FONT_BODY = _font(12)
FONT_SMALL = _font(10)

CURSOR_INDENT = int(FONT_BODY.getlength("▸ "))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _new_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("1", (W, H), 1)   # white
    return img, ImageDraw.Draw(img)


def _title_bar(draw: ImageDraw.ImageDraw, text: str):
    """Draw title text centered with a thin separator line underneath."""
    bbox = draw.textbbox((0, 0), text, font=FONT_TITLE)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw.text(((W - text_w) // 2, (TITLE_H - text_h) // 2 - 2), text, font=FONT_TITLE, fill=0)
    draw.line([(PADDING, TITLE_H - 1), (W - PADDING, TITLE_H - 1)], fill=0)


def _truncate(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    """Truncate text with ellipsis to fit max_width pixels."""
    if font.getlength(text) <= max_width:
        return text
    while text and font.getlength(text + "…") > max_width:
        text = text[:-1]
    return text + "…"


def _format_duration(ms: int) -> str:
    minutes = ms // 60000
    if minutes >= 60:
        return f"{minutes // 60}h {minutes % 60:02d}m"
    return f"{minutes}m"


def _format_date(date_str: str) -> str:
    """'2024-03-15' → 'Mar 15'"""
    try:
        from datetime import datetime
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%b %-d")
    except Exception:
        return date_str


# ── Screen renderers ──────────────────────────────────────────────────────────

_SPLASH_PATH = Path(__file__).parent / "assets" / "splash_converted.png"


def render_splash() -> Image.Image:
    """Load the pre-converted 1-bit splash image, or fall back to a blank screen."""
    if _SPLASH_PATH.exists():
        return Image.open(_SPLASH_PATH).convert("1")
    img = Image.new("1", (W, H), 1)
    return img


def render_loading(message: str = "Loading…") -> Image.Image:
    img, draw = _new_canvas()
    bbox = draw.textbbox((0, 0), message, font=FONT_BODY)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(((W - tw) // 2, (H - th) // 2), message, font=FONT_BODY, fill=0)
    return img


def render_shows(
    shows: list[Show],
    cursor: int,
    scroll_offset: int,
) -> Image.Image:
    img, draw = _new_canvas()
    _title_bar(draw, "Podcasts")

    text_x = PADDING + CURSOR_INDENT
    max_text_w = W - text_x - PADDING - 6

    visible = shows[scroll_offset: scroll_offset + ROWS_VISIBLE]
    for i, show in enumerate(visible):
        y = TITLE_H + i * ROW_H
        is_selected = (scroll_offset + i) == cursor
        text_y = y + (ROW_H - 14) // 2

        if is_selected:
            draw.text((PADDING, text_y), "▸", font=FONT_BODY, fill=0)

        label = _truncate(show.name, FONT_BODY, max_text_w)
        draw.text((text_x, text_y), label, font=FONT_BODY, fill=0)

    if len(shows) > ROWS_VISIBLE:
        _draw_scrollbar(draw, len(shows), scroll_offset, ROWS_VISIBLE)

    return img


def render_episodes(
    show_name: str,
    episodes: list[Episode],
    cursor: int,
    scroll_offset: int,
) -> Image.Image:
    img, draw = _new_canvas()
    _title_bar(draw, _truncate(show_name, FONT_TITLE, W - PADDING * 2))

    text_x = PADDING + CURSOR_INDENT
    max_text_w = W - text_x - PADDING - 6

    visible = episodes[scroll_offset: scroll_offset + EP_ROWS_VISIBLE]
    for i, ep in enumerate(visible):
        y = TITLE_H + i * EP_ROW_H
        is_selected = (scroll_offset + i) == cursor

        if is_selected:
            draw.text((PADDING, y + 3), "▸", font=FONT_BODY, fill=0)

        name = _truncate(ep.name, FONT_BODY, max_text_w)
        draw.text((text_x, y + 3), name, font=FONT_BODY, fill=0)

        subtitle = f"{_format_date(ep.release_date)}  ·  {_format_duration(ep.duration_ms)}"
        draw.text((text_x, y + 18), subtitle, font=FONT_SMALL, fill=0)

    if len(episodes) > EP_ROWS_VISIBLE:
        _draw_scrollbar(draw, len(episodes), scroll_offset, EP_ROWS_VISIBLE)

    return img


def render_player(playback: Optional[PlaybackState]) -> Image.Image:
    img, draw = _new_canvas()

    if playback is None:
        draw.text((PADDING, H // 2 - 16), "No active playback.", font=FONT_BODY, fill=0)
        draw.text((PADDING, H // 2), "Start playing on a Spotify", font=FONT_SMALL, fill=0)
        draw.text((PADDING, H // 2 + 14), "device, then press SELECT.", font=FONT_SMALL, fill=0)
        return img

    # Show name as header with separator
    show = _truncate(playback.show_name, FONT_TITLE, W - PADDING * 2)
    draw.text((PADDING, 8), show, font=FONT_TITLE, fill=0)
    draw.line([(PADDING, 30), (W - PADDING, 30)], fill=0)

    # Episode name (may wrap to 2 lines)
    ep_max_w = W - PADDING * 2
    ep_text = playback.episode_name
    if FONT_BODY.getlength(ep_text) > ep_max_w:
        chars_per_line = int(ep_max_w / (FONT_BODY.getlength(ep_text) / len(ep_text)))
        lines = textwrap.wrap(ep_text, chars_per_line)[:2]
        lines[-1] = _truncate(lines[-1], FONT_BODY, ep_max_w)
    else:
        lines = [ep_text]

    y = 40
    for line in lines:
        draw.text((PADDING, y), line, font=FONT_SMALL, fill=0)
        y += 14

    # Progress — time text and thin bar at bottom
    bar_left = PADDING
    bar_right = W - PADDING
    bar_y = H - 24

    elapsed = _format_duration(playback.progress_ms)
    total = _format_duration(playback.duration_ms)
    draw.text((PADDING, bar_y - 16), f"{elapsed} / {total}", font=FONT_SMALL, fill=0)

    # Thin 4px progress bar (outline for track, solid fill for progress)
    draw.rectangle([bar_left, bar_y, bar_right, bar_y + 4], outline=0)
    if playback.duration_ms > 0:
        fill_w = int((bar_right - bar_left) * playback.progress_ms / playback.duration_ms)
        if fill_w > 0:
            draw.rectangle([bar_left, bar_y, bar_left + fill_w, bar_y + 4], fill=0)

    return img


# ── Scrollbar ─────────────────────────────────────────────────────────────────

def _draw_scrollbar(
    draw: ImageDraw.ImageDraw,
    total: int,
    offset: int,
    visible: int,
):
    sb_x = W - 4
    sb_top = TITLE_H + 2
    sb_bot = H - 2
    sb_h = sb_bot - sb_top

    thumb_h = max(8, sb_h * visible // total)
    thumb_top = sb_top + (sb_h - thumb_h) * offset // max(1, total - visible)
    draw.rectangle([sb_x, thumb_top, sb_x + 2, thumb_top + thumb_h], fill=0)


# ── Screen enum (used by main) ────────────────────────────────────────────────

class Screen(Enum):
    SPLASH = auto()
    LOADING = auto()
    SHOWS = auto()
    EPISODES = auto()
    PLAYER = auto()
