#!/usr/bin/env python3
"""Render a captured console transcript (.txt) as a terminal-styled PNG image.

Usage: termshot.py <input.txt> <output.png> [title]

Strips ANSI escape sequences, wraps long lines, and draws the result onto a
dark terminal-style canvas with a title bar showing the transcript's source
filename (or an explicit title) and macOS-style window dots -- purely a
presentational rendering of the real, already-captured transcript text.
"""
import sys
import os
import re
import textwrap
from PIL import Image, ImageDraw, ImageFont

ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_SIZE = 15
LINE_HEIGHT = 20
PAD_X = 20
PAD_TOP = 44
PAD_BOTTOM = 20
WRAP_COLS = 110
BG = (17, 17, 21)
FG = (219, 219, 219)
TITLEBAR = (34, 34, 40)
DOT_COLORS = [(255, 95, 86), (255, 189, 46), (39, 201, 63)]


def strip_ansi(text):
    return ANSI_RE.sub('', text)


def main():
    if len(sys.argv) < 3:
        print("usage: termshot.py <input.txt> <output.png> [title]", file=sys.stderr)
        sys.exit(1)
    in_path, out_path = sys.argv[1], sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else os.path.basename(in_path)

    with open(in_path, "r", errors="replace") as f:
        raw = f.read()
    clean = strip_ansi(raw).replace("\r\n", "\n").replace("\r", "\n")

    lines = []
    for line in clean.split("\n"):
        if line.strip() == "":
            lines.append("")
            continue
        wrapped = textwrap.wrap(
            line, width=WRAP_COLS,
            break_long_words=True, break_on_hyphens=False,
            replace_whitespace=False, drop_whitespace=False,
        ) or [""]
        lines.extend(wrapped)

    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    char_w = font.getbbox("M")[2]
    width = PAD_X * 2 + char_w * WRAP_COLS
    height = PAD_TOP + PAD_BOTTOM + LINE_HEIGHT * len(lines)

    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, width, PAD_TOP], fill=TITLEBAR)
    for i, c in enumerate(DOT_COLORS):
        draw.ellipse([16 + i * 22, 15, 30 + i * 22, 29], fill=c)
    draw.text((width / 2, 22), title, font=font, fill=(160, 160, 168), anchor="mm")

    y = PAD_TOP + 10
    for line in lines:
        draw.text((PAD_X, y), line, font=font, fill=FG)
        y += LINE_HEIGHT

    img.save(out_path)
    print(f"wrote {out_path} ({width}x{height}, {len(lines)} lines)")


if __name__ == "__main__":
    main()
