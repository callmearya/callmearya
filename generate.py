#!/usr/bin/env python3
"""Generate callmearya's animated light and dark profile cards."""

from __future__ import annotations

import argparse
import base64
import io
import json
import re
import urllib.request
from dataclasses import dataclass
from datetime import date
from html import escape
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps


WIDTH = 1180
HEIGHT = 620
CELL_WIDTH = 192
CELL_HEIGHT = 208


@dataclass(frozen=True)
class Theme:
    name: str
    background: str
    background_alt: str
    panel: str
    border: str
    primary: str
    secondary: str
    accent: str
    text: str
    muted: str
    faint: str
    scanline: str


THEMES = (
    Theme(
        name="dark",
        background="#050816",
        background_alt="#0B1120",
        panel="#0B1120",
        border="#EF4444",
        primary="#22D3EE",
        secondary="#F87171",
        accent="#FB7185",
        text="#FFFFFF",
        muted="#67E8F9",
        faint="#1E3A5F",
        scanline="#7DD3FC",
    ),
    Theme(
        name="light",
        background="#F5FAF7",
        background_alt="#FFFFFF",
        panel="#F8FCFA",
        border="#DC2626",
        primary="#0369A1",
        secondary="#EF4444",
        accent="#BE123C",
        text="#0F172A",
        muted="#0E7490",
        faint="#BAE6FD",
        scanline="#0369A1",
    ),
)


# Rows follow the Codex v2 pet contract. Each pair is (row, column).
SPIDEY_SEQUENCE = (
    (7, 0),  # dedicated upside-down hanging row
    (7, 1),
    (7, 2),
    (7, 3),
    (7, 4),
    (7, 5),
    (7, 4),
    (7, 3),
    (7, 2),
    (7, 1),
    (7, 0),
    (7, 0),
)


def image_data_uri(image: Image.Image) -> str:
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def ascii_portrait(path: Path, columns: int = 100, rows: int = 60) -> list[str]:
    with Image.open(path) as source:
        portrait = ImageOps.fit(
            source.convert("L"),
            (columns, rows),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.43),
        )
        portrait = ImageOps.autocontrast(portrait, cutoff=2)
        portrait = ImageEnhance.Contrast(portrait).enhance(1.18)

    ramp = "@%#*+=-:. "
    pixels = list(portrait.get_flattened_data())
    return [
        "".join(
            ramp[pixel * (len(ramp) - 1) // 255]
            for pixel in pixels[offset : offset + columns]
        )
        for offset in range(0, len(pixels), columns)
    ]


def spidey_frames(path: Path) -> list[str]:
    with Image.open(path) as atlas:
        atlas = atlas.convert("RGBA")
        expected = (CELL_WIDTH * 8, CELL_HEIGHT * 11)
        if atlas.size != expected:
            raise ValueError(f"Expected a {expected[0]}x{expected[1]} v2 atlas, got {atlas.size}")

        frames = []
        for row, column in SPIDEY_SEQUENCE:
            bounds = (
                column * CELL_WIDTH,
                row * CELL_HEIGHT,
                (column + 1) * CELL_WIDTH,
                (row + 1) * CELL_HEIGHT,
            )
            frames.append(image_data_uri(atlas.crop(bounds)))
        return frames


def svg_spidey(frames: list[str]) -> str:
    segment_count = len(frames)
    times = [index / segment_count for index in range(segment_count + 1)]
    key_times = ";".join(f"{value:.5f}" for value in times)
    images = []

    for active_index, frame in enumerate(frames):
        values = ["1" if index == active_index else "0" for index in range(segment_count)]
        values.append(values[0])
        images.append(
            f'''<image x="0" y="25" width="76" height="82" href="{frame}" opacity="0">
              <animate attributeName="opacity" values="{';'.join(values)}" keyTimes="{key_times}" dur="9.6s" calcMode="discrete" repeatCount="indefinite"/>
            </image>'''
        )

    return f'''
      <g id="spidey" transform="translate(418 18)">
        <animateTransform attributeName="transform" type="rotate" values="-3 38 0;3 38 0;-3 38 0" dur="3.4s" repeatCount="indefinite" additive="sum"/>
        <path d="M38 -18 V35" stroke="#CBD5E1" stroke-width="1.5" stroke-dasharray="2 2" opacity="0.8"/>
        <circle cx="38" cy="-18" r="2.4" fill="#E2E8F0" opacity="0.9"/>
        {''.join(images)}
      </g>
    '''


def svg_ascii(lines: list[str]) -> str:
    tspans = []
    for index, line in enumerate(lines):
        y = 40 + index * 7.55
        tspans.append(
            f'<tspan x="25" y="{y:.2f}" textLength="455" lengthAdjust="spacingAndGlyphs">{escape(line)}</tspan>'
        )
    return "".join(tspans)


def svg_system_lines() -> tuple[str, str]:
    line_markup = (
        '<tspan class="head">arya@callmearya</tspan><tspan class="cc"> -———————————————————————————————-</tspan>',
        '<tspan class="cc">. </tspan><tspan class="key">Subject</tspan><tspan class="cc">: ................. </tspan><tspan class="value">Arya</tspan>',
        '<tspan class="cc">. </tspan><tspan class="key">Role</tspan><tspan class="cc">: .................... </tspan><tspan class="value">Tech Enthusiast</tspan>',
        '<tspan class="cc">. </tspan>',
        '<tspan class="cc">. </tspan><tspan class="key">Mode</tspan><tspan class="cc">: .................... </tspan><tspan class="value">Curious · Building · Learning</tspan>',
        '<tspan class="cc">. </tspan><tspan class="key">Focus</tspan><tspan class="cc">: ................... </tspan><tspan class="value">Evidence-first agents · Knowledge work</tspan>',
        '<tspan class="cc">. </tspan><tspan class="key">Current</tspan><tspan class="cc">: ................. </tspan><tspan class="value">mahabharata-council · active</tspan>',
        '<tspan class="cc">. </tspan>',
        '<tspan class="cc">. </tspan><tspan class="key">Core</tspan><tspan class="cc">.</tspan><tspan class="key">Lang</tspan><tspan class="cc">: ............... </tspan><tspan class="value">Python, Kotlin, JavaScript</tspan>',
        '<tspan class="cc">. </tspan><tspan class="key">Core</tspan><tspan class="cc">.</tspan><tspan class="key">System</tspan><tspan class="cc">: ............. </tspan><tspan class="value">Cython, C, C++</tspan>',
        '<tspan class="cc">. </tspan><tspan class="key">Core</tspan><tspan class="cc">.</tspan><tspan class="key">Other</tspan><tspan class="cc">: .............. </tspan><tspan class="value">HTML, CSS, Shell</tspan>',
        '<tspan class="cc">. </tspan>',
        '<tspan class="accent">- Featured</tspan><tspan class="cc"> -———————————————————————————————-</tspan>',
        '<tspan class="cc">. </tspan><tspan class="key">01</tspan><tspan class="cc">: ...................... </tspan><tspan class="value">mahabharata-council</tspan>',
        '<tspan class="cc">. </tspan><tspan class="key">01</tspan><tspan class="cc">.</tspan><tspan class="key">Note</tspan><tspan class="cc">: ................. </tspan><tspan class="value">Evidence-first agents</tspan>',
        '<tspan class="cc">. </tspan><tspan class="key">02</tspan><tspan class="cc">: ...................... </tspan><tspan class="value">pournami-calendar-automation</tspan>',
        '<tspan class="cc">. </tspan><tspan class="key">02</tspan><tspan class="cc">.</tspan><tspan class="key">Note</tspan><tspan class="cc">: ................. </tspan><tspan class="value">Ephemeris → calendar</tspan>',
        '<tspan class="cc">. </tspan>',
        '<tspan class="accent">- Contact</tspan><tspan class="cc"> -————————————————————————————————-</tspan>',
        '<tspan class="cc">. </tspan><tspan class="key">GitHub</tspan><tspan class="cc">: .................. </tspan><tspan class="value">github.com/callmearya</tspan>',
        '<tspan class="cc">. </tspan><tspan class="key">Status</tspan><tspan class="cc">: .................. </tspan><tspan class="value">Open to interesting problems</tspan>',
        '<tspan class="cc">. </tspan><tspan class="value">Contribution signal continues below ↓</tspan>',
    )
    clips = []
    rows = []
    for index, markup in enumerate(line_markup):
        y = 42 + index * 22
        begin = 0.72 + index * 0.11
        clips.append(
            f'<clipPath id="line-{index}"><rect x="500" y="{y - 19}" width="0" height="24">'
            f'<animate attributeName="width" from="0" to="680" dur="0.38s" begin="{begin:.2f}s" fill="freeze"/>'
            '</rect></clipPath>'
        )
        rows.append(
            f'<g clip-path="url(#line-{index})"><text x="520" y="{y}">{markup}</text></g>'
        )
    return "".join(clips), "".join(rows)


def render_svg(theme: Theme, portrait: list[str], frames: list[str]) -> str:
    clips, system_rows = svg_system_lines()
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="586" viewBox="0 0 1180 586" role="img" aria-labelledby="title description">
  <title id="title">Arya — Tech Enthusiast</title>
  <desc id="description">Animated terminal profile with Arya's ASCII portrait and a tiny hanging Spidey mascot.</desc>
  <defs>
    <radialGradient id="background" cx="30%" cy="20%" r="80%"><stop offset="0" stop-color="{theme.background_alt}"/><stop offset="1" stop-color="{theme.background}"/></radialGradient>
    <linearGradient id="portraitInk" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{theme.secondary}">
        <animate attributeName="stop-color" values="{theme.secondary};#22D3EE;#60A5FA;{theme.secondary}" dur="8s" repeatCount="indefinite"/>
      </stop>
      <stop offset="1" stop-color="#22D3EE">
        <animate attributeName="stop-color" values="#22D3EE;#60A5FA;{theme.secondary};#22D3EE" dur="8s" repeatCount="indefinite"/>
      </stop>
    </linearGradient>
    <linearGradient id="border" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{theme.border}"/><stop offset="0.5" stop-color="{theme.accent}"/><stop offset="1" stop-color="#22D3EE"/></linearGradient>
    <pattern id="scanlines" width="4" height="4" patternUnits="userSpaceOnUse">
      <rect width="4" height="1" fill="{theme.scanline}" opacity="0.05"/>
    </pattern>
    <filter id="glow" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <mask id="portraitReveal" maskUnits="userSpaceOnUse" x="0" y="0" width="1180" height="620">
      <rect x="0" y="0" width="1180" height="0" fill="white">
        <animate attributeName="height" from="0" to="560" dur="2.6s" begin="0.2s" fill="freeze"/>
      </rect>
    </mask>
    {clips}
    <style>
      text, tspan {{ font-family: "Courier New", Consolas, monospace; white-space: pre; }}
      .ascii {{ font-size: 7.4px; fill: url(#portraitInk); letter-spacing: -0.2px; }}
      .key {{ font-size: 15px; fill: {theme.primary}; font-weight: bold; }}
      .value {{ font-size: 15px; fill: {theme.text}; font-weight: 500; }}
      .cc {{ font-size: 15px; fill: {theme.faint}; }}
      .head {{ font-size: 17px; fill: {theme.border}; font-weight: bold; }}
      .accent {{ font-size: 15px; fill: {theme.accent}; font-weight: bold; }}
      .term-label {{ font-size: 12px; fill: {theme.muted}; letter-spacing: 0.5px; opacity: 0.8; }}
      .scan-label {{ font-size: 10px; fill: #F87171; letter-spacing: 1px; }}
      .panel-title {{ font-size: 11px; fill: {theme.border}; letter-spacing: 2px; opacity: 0.85; }}
      .panel-title-blue {{ font-size: 11px; fill: {theme.secondary}; letter-spacing: 2px; opacity: 0.85; }}
      @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
    </style>
  </defs>

  <rect width="1180" height="586" rx="18" fill="url(#background)"/>
  <rect width="1180" height="586" rx="18" fill="url(#scanlines)"/>
  <g id="titlebar">
    <rect x="3" y="3" width="1174" height="34" rx="16" fill="{theme.background_alt}" opacity="0.85"/>
    <circle cx="24" cy="20" r="5" fill="#EF4444"/>
    <circle cx="42" cy="20" r="5" fill="#F59E0B"/>
    <circle cx="60" cy="20" r="5" fill="#10B981"/>
    <text x="590" y="25" text-anchor="middle" class="term-label">arya@callmearya ~ % ./profile.sh --live</text>
    <circle cx="1070" cy="20" r="4" fill="#F87171"><animate attributeName="opacity" values="1;0.15;1" dur="1.1s" repeatCount="indefinite"/></circle>
    <text x="1080" y="24" class="scan-label">SCANNING</text>
  </g>

  <g transform="translate(0 44)">
    <rect x="14" y="18" width="488" height="490" rx="14" fill="{theme.panel}" opacity="0.35" stroke="url(#border)" stroke-width="1"/>
    <rect x="508" y="8" width="655" height="518" rx="14" fill="{theme.panel}" opacity="0.35" stroke="url(#border)" stroke-width="1"/>
    <text x="30" y="14" class="panel-title-blue">VISUAL.MAP</text>
    <text x="524" y="6" class="panel-title">SYSTEM.INFO</text>
    <g mask="url(#portraitReveal)"><text class="ascii">{svg_ascii(portrait)}</text></g>
    <g>{system_rows}</g>
    <rect x="0" y="-70" width="1180" height="44" fill="{theme.border}" opacity="0.08">
      <animate attributeName="y" from="-70" to="540" dur="6.8s" repeatCount="indefinite"/>
    </rect>
  </g>

  {svg_spidey(frames)}
</svg>
'''


def parse_contributions_html(html: str) -> list[dict[str, int | str]]:
    matches = re.findall(
        r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*data-level="([0-4])"',
        html,
    )
    contributions = [{"date": day, "level": int(level)} for day, level in matches]
    if len(contributions) < 300:
        raise ValueError(f"Expected a contribution calendar, found only {len(contributions)} days")
    return contributions


def load_contributions(
    root: Path,
    *,
    refresh: bool,
    html_path: Path | None,
) -> list[dict[str, int | str]]:
    cache = root / "assets" / "contributions.json"
    if html_path is not None:
        contributions = parse_contributions_html(html_path.read_text(encoding="utf-8"))
        cache.write_text(json.dumps(contributions, indent=2) + "\n", encoding="utf-8")
        return contributions

    if refresh:
        request = urllib.request.Request(
            "https://github.com/users/callmearya/contributions",
            headers={"User-Agent": "callmearya-profile-readme"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            contributions = parse_contributions_html(response.read().decode("utf-8"))
        cache.write_text(json.dumps(contributions, indent=2) + "\n", encoding="utf-8")
        return contributions

    if not cache.exists():
        raise FileNotFoundError("Run generate.py with --refresh-contributions once")
    return json.loads(cache.read_text(encoding="utf-8"))


def render_contribution_svg(theme: Theme, contributions: list[dict[str, int | str]]) -> str:
    ordered = sorted(contributions, key=lambda item: str(item["date"]))
    first_day = date.fromisoformat(str(ordered[0]["date"]))
    first_sunday_offset = (first_day.weekday() + 1) % 7
    grid_start = first_day.toordinal() - first_sunday_offset
    today = date.today()
    active_days = sum(
        int(item["level"]) > 0 and date.fromisoformat(str(item["date"])) <= today
        for item in ordered
    )
    year = first_day.year

    nodes: list[str] = []
    horizontal: dict[int, list[tuple[float, float]]] = {day: [] for day in range(7)}
    vertical: dict[int, list[tuple[float, float]]] = {}
    month_labels: dict[str, tuple[float, float]] = {}
    level_colors = (theme.faint, theme.secondary, theme.primary, theme.accent, "#FB7185")

    for item in ordered:
        day = date.fromisoformat(str(item["date"]))
        offset = day.toordinal() - grid_start
        week = offset // 7
        weekday = offset % 7
        x = 98 + week * 19.2 + weekday * 2.8
        y = 105 + weekday * 23.5
        level = int(item["level"])
        is_future = day > today
        radius = 2.1 if level == 0 else 3.3 + level * 0.72
        opacity = 0.16 if is_future else (0.28 if level == 0 else 0.9)
        horizontal[weekday].append((x, y))
        vertical.setdefault(week, []).append((x, y))
        month_labels.setdefault(day.strftime("%b"), (x, y))
        delay = (week * 0.025 + weekday * 0.018) % 1.4
        pulse = (
            f'<animate attributeName="opacity" values="{opacity};1;{opacity}" '
            f'dur="3.6s" begin="{delay:.2f}s" repeatCount="indefinite"/>'
            if level > 0 and not is_future
            else ""
        )
        nodes.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{level_colors[level]}" '
            f'opacity="{opacity}" data-date="{day.isoformat()}" data-level="{level}">{pulse}</circle>'
        )

    strands = []
    for points in horizontal.values():
        if len(points) > 1:
            path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)
            strands.append(f'<path d="{path}" fill="none" stroke="{theme.faint}" stroke-width="0.75" opacity="0.34"/>')
    for points in vertical.values():
        if len(points) > 1:
            path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)
            strands.append(f'<path d="{path}" fill="none" stroke="{theme.faint}" stroke-width="0.65" opacity="0.22"/>')

    labels = []
    seen_x = -100.0
    for month, (x, _) in month_labels.items():
        if x - seen_x >= 55:
            labels.append(f'<text x="{x:.1f}" y="84" class="month">{month.upper()}</text>')
            seen_x = x

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="310" viewBox="0 0 1180 310" role="img" aria-labelledby="contribution-title contribution-description">
  <title id="contribution-title">Arya's contribution web</title>
  <desc id="contribution-description">A web-like calendar visualization of public GitHub contribution activity.</desc>
  <defs>
    <linearGradient id="webBackground" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{theme.background_alt}"/>
      <stop offset="1" stop-color="{theme.background}"/>
    </linearGradient>
    <linearGradient id="webBorder" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{theme.secondary}"/>
      <stop offset="0.5" stop-color="{theme.primary}"/>
      <stop offset="1" stop-color="{theme.accent}"/>
    </linearGradient>
    <filter id="nodeGlow" x="-100%" y="-100%" width="300%" height="300%">
      <feGaussianBlur stdDeviation="2.4" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <style>
      text {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }}
      .eyebrow {{ font-size: 11px; font-weight: 700; letter-spacing: 2px; fill: {theme.muted}; }}
      .title {{ font-size: 20px; font-weight: 800; fill: {theme.text}; }}
      .meta {{ font-size: 12px; fill: {theme.muted}; }}
      .month {{ font-size: 9px; font-weight: 700; letter-spacing: 1px; fill: {theme.muted}; }}
    </style>
  </defs>
  <rect width="1180" height="310" rx="18" fill="url(#webBackground)"/>
  <rect x="1.5" y="1.5" width="1177" height="307" rx="16.5" fill="none" stroke="url(#webBorder)" stroke-width="2" opacity="0.62"/>
  <text x="32" y="32" class="eyebrow">CONTRIBUTION.WEB</text>
  <text x="32" y="58" class="title">weaving code through {year}</text>
  <text x="1148" y="33" text-anchor="end" class="meta">{active_days} active days · public activity</text>
  {''.join(labels)}
  <g>{''.join(strands)}</g>
  <g filter="url(#nodeGlow)">{''.join(nodes)}</g>
  <g opacity="0.32">
    <line x1="76" y1="93" x2="76" y2="260" stroke="{theme.secondary}" stroke-width="1">
      <animate attributeName="x1" from="76" to="1130" dur="8s" repeatCount="indefinite"/>
      <animate attributeName="x2" from="76" to="1130" dur="8s" repeatCount="indefinite"/>
    </line>
  </g>
  <text x="32" y="284" class="meta">quiet days form the web · active days carry the signal</text>
  <g transform="translate(936 272)">
    <circle cx="0" cy="0" r="2.2" fill="{theme.faint}"/><text x="10" y="4" class="meta">quiet</text>
    <circle cx="75" cy="0" r="4" fill="{theme.secondary}"/><circle cx="101" cy="0" r="5" fill="{theme.primary}"/><circle cx="131" cy="0" r="6" fill="{theme.accent}"/>
    <text x="143" y="4" class="meta">active</text>
  </g>
</svg>
'''


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    portrait = ascii_portrait(root / "assets" / "avatar.png")
    frames = spidey_frames(root / "assets" / "spidey-spritesheet.webp")

    for theme in THEMES:
        card_output = root / f"{theme.name}.svg"
        card_output.write_text(render_svg(theme, portrait, frames), encoding="utf-8")
        print(f"wrote {card_output}")


if __name__ == "__main__":
    main()
