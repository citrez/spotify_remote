"""
PIL-based renderer for all screens.

Every render_* function takes the current app state and returns a PIL Image
(264×176, mode "1" — 1-bit black/white) ready to be pushed to the display.
"""

import textwrap
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from . import config
from .spotify_client import Episode, PlaybackState, Show

# ── Layout constants ──────────────────────────────────────────────────────────

W = config.DISPLAY_WIDTH   # 264
H = config.DISPLAY_HEIGHT  # 176

TITLE_H = 22        # height of the top title bar
ROW_H = 28          # height of a show row
EP_ROW_H = 38       # height of an episode row (name + subtitle)
ROWS_VISIBLE = (H - TITLE_H) // ROW_H          # 5 show rows
EP_ROWS_VISIBLE = (H - TITLE_H) // EP_ROW_H    # 4 episode rows

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


FONT_TITLE = _font(13, bold=True)
FONT_BODY = _font(12)
FONT_SMALL = _font(10)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _new_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("1", (W, H), 1)   # white
    return img, ImageDraw.Draw(img)


def _title_bar(draw: ImageDraw.ImageDraw, text: str):
    draw.rectangle([0, 0, W - 1, TITLE_H - 1], fill=0)
    draw.text((PADDING, 4), text, font=FONT_TITLE, fill=1)


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

def render_loading(message: str = "Loading…") -> Image.Image:
    img, draw = _new_canvas()
    draw.rectangle([0, 0, W - 1, H - 1], outline=0)
    # Centre the message
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

    visible = shows[scroll_offset: scroll_offset + ROWS_VISIBLE]
    for i, show in enumerate(visible):
        y = TITLE_H + i * ROW_H
        is_selected = (scroll_offset + i) == cursor

        if is_selected:
            draw.rectangle([0, y, W - 1, y + ROW_H - 2], fill=0)
            text_fill = 1
        else:
            text_fill = 0

        label = _truncate(show.name, FONT_BODY, W - PADDING * 2)
        draw.text((PADDING, y + (ROW_H - 14) // 2), label, font=FONT_BODY, fill=text_fill)

    # Scroll indicator
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

    visible = episodes[scroll_offset: scroll_offset + EP_ROWS_VISIBLE]
    for i, ep in enumerate(visible):
        y = TITLE_H + i * EP_ROW_H
        is_selected = (scroll_offset + i) == cursor

        if is_selected:
            draw.rectangle([0, y, W - 1, y + EP_ROW_H - 2], fill=0)
            text_fill = 1
        else:
            text_fill = 0

        name = _truncate(ep.name, FONT_BODY, W - PADDING * 2)
        draw.text((PADDING, y + 3), name, font=FONT_BODY, fill=text_fill)

        subtitle = f"{_format_date(ep.release_date)}  ·  {_format_duration(ep.duration_ms)}"
        draw.text((PADDING, y + 18), subtitle, font=FONT_SMALL, fill=text_fill)

    if len(episodes) > EP_ROWS_VISIBLE:
        _draw_scrollbar(draw, len(episodes), scroll_offset, EP_ROWS_VISIBLE)

    return img


CTRL_H = 42   # height of the controls bar at the bottom of the player screen


def _draw_player_controls(draw: ImageDraw.ImageDraw, is_playing: bool):
    """Draw a 3-button control row across the bottom CTRL_H pixels of the screen."""
    ctrl_y = H - CTRL_H
    draw.line([(0, ctrl_y - 1), (W - 1, ctrl_y - 1)], fill=0)

    section_w = W // 3  # 88 px each

    play_icon = "⏸" if is_playing else "▶"
    play_label = "Pause" if is_playing else "Play"
    sections = [
        ("◀", "Prev"),
        (play_icon, play_label),
        ("▶", "Next"),
    ]

    for i, (icon, label) in enumerate(sections):
        x_start = i * section_w
        x_center = x_start + section_w // 2

        if i > 0:
            draw.line([(x_start, ctrl_y), (x_start, H - 1)], fill=0)

        icon_bbox = draw.textbbox((0, 0), icon, font=FONT_BODY)
        icon_w = icon_bbox[2] - icon_bbox[0]
        draw.text((x_center - icon_w // 2, ctrl_y + 4), icon, font=FONT_BODY, fill=0)

        label_bbox = draw.textbbox((0, 0), label, font=FONT_SMALL)
        label_w = label_bbox[2] - label_bbox[0]
        draw.text((x_center - label_w // 2, ctrl_y + 22), label, font=FONT_SMALL, fill=0)


def render_player(playback: Optional[PlaybackState]) -> Image.Image:
    img, draw = _new_canvas()

    if playback is None:
        _title_bar(draw, "Now Playing")
        draw.text((PADDING, 50), "No active playback.", font=FONT_BODY, fill=0)
        draw.text((PADDING, 68), "Start playing on a Spotify", font=FONT_SMALL, fill=0)
        draw.text((PADDING, 82), "device, then press SELECT.", font=FONT_SMALL, fill=0)
        return img

    _title_bar(draw, "Now Playing")

    # Status line
    status = "▶  Playing" if playback.is_playing else "⏸  Paused"
    draw.text((PADDING, TITLE_H + 4), status, font=FONT_SMALL, fill=0)

    # Show name
    show = _truncate(playback.show_name, FONT_BODY, W - PADDING * 2)
    draw.text((PADDING, TITLE_H + 18), show, font=FONT_BODY, fill=0)

    # Episode name (may wrap to 2 lines)
    ep_max_w = W - PADDING * 2
    ep_text = playback.episode_name
    if FONT_BODY.getlength(ep_text) > ep_max_w:
        chars_per_line = int(ep_max_w / (FONT_BODY.getlength(ep_text) / len(ep_text)))
        lines = textwrap.wrap(ep_text, chars_per_line)[:2]
        lines[-1] = _truncate(lines[-1], FONT_BODY, ep_max_w)
    else:
        lines = [ep_text]

    y = TITLE_H + 36
    for line in lines:
        draw.text((PADDING, y), line, font=FONT_SMALL, fill=0)
        y += 13

    # Progress bar (sits just above the controls area)
    bar_y = H - CTRL_H - 30
    elapsed = _format_duration(playback.progress_ms)
    total = _format_duration(playback.duration_ms)
    draw.text((PADDING, bar_y), f"{elapsed} / {total}", font=FONT_SMALL, fill=0)

    bar_top = bar_y + 14
    bar_bot = bar_top + 10
    bar_left = PADDING
    bar_right = W - PADDING

    draw.rectangle([bar_left, bar_top, bar_right, bar_bot], outline=0)
    if playback.duration_ms > 0:
        fill_w = int((bar_right - bar_left - 2) * playback.progress_ms / playback.duration_ms)
        if fill_w > 0:
            draw.rectangle([bar_left + 1, bar_top + 1, bar_left + 1 + fill_w, bar_bot - 1], fill=0)

    # Control buttons
    _draw_player_controls(draw, playback.is_playing)

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

    draw.rectangle([sb_x, sb_top, sb_x + 2, sb_bot], outline=0)

    thumb_h = max(6, sb_h * visible // total)
    thumb_top = sb_top + (sb_h - thumb_h) * offset // max(1, total - visible)
    draw.rectangle([sb_x, thumb_top, sb_x + 2, thumb_top + thumb_h], fill=0)


# ── Screen enum (used by main) ────────────────────────────────────────────────

class Screen(Enum):
    LOADING = auto()
    SHOWS = auto()
    EPISODES = auto()
    PLAYER = auto()
