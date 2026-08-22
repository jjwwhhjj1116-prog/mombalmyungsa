#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter


ALLOWED_FILL_COLORS = {"#FFFF00", "#00FF22", "#FF0033", "#FFFFFF"}


def visible_character_count(text):
    return len(re.sub(r"[\s\W_]", "", text, flags=re.UNICODE))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("background", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--text", required=True)
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--font-size", type=int, default=175)
    parser.add_argument("--stroke", type=int, default=30)
    parser.add_argument("--fill", default="#FFFF00")
    parser.add_argument("--line-fills", default=None, help="Comma-separated SULL palette colors; one per line")
    parser.add_argument("--y", type=int, default=170)
    parser.add_argument("--x", type=int, default=540)
    args = parser.parse_args()

    normalized_text = args.text.replace("\\n", "\n")
    line_counts = [visible_character_count(line) for line in normalized_text.splitlines()]
    if len(line_counts) < 2:
        raise SystemExit("thumbnail copy must use 2 or 3 semantic lines")
    if len(line_counts) > 3:
        raise SystemExit("thumbnail copy exceeds 3 lines")
    if any(count > 7 for count in line_counts):
        raise SystemExit("thumbnail copy exceeds 7 visible characters on a line")
    if not args.background.is_file() or not args.font.is_file():
        raise SystemExit("background or font missing")

    image = Image.open(args.background).convert("RGB")
    image = image.resize((1080, 1920), Image.Resampling.LANCZOS)
    font = ImageFont.truetype(str(args.font), args.font_size)
    lines = normalized_text.splitlines()
    line_fills = [args.fill.upper()] * len(lines)
    if args.line_fills:
        line_fills = [color.strip().upper() for color in args.line_fills.split(",")]
        if len(line_fills) != len(lines):
            raise SystemExit("--line-fills must contain exactly one color per text line")
    if any(color not in ALLOWED_FILL_COLORS for color in line_fills):
        raise SystemExit("thumbnail fill must use only #FFFF00, #00FF22, #FF0033, or #FFFFFF")
    draw = ImageDraw.Draw(image)
    boxes = [draw.textbbox((0, 0), line, font=font, stroke_width=args.stroke) for line in lines]
    line_height = max(box[3] - box[1] for box in boxes)
    spacing = 18
    total_height = line_height * len(lines) + spacing * (len(lines) - 1)
    y = args.y

    shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    for line, box in zip(lines, boxes):
        width = box[2] - box[0]
        if width > 1000:
            raise SystemExit("thumbnail line exceeds safe width; add a manual line break")
        if args.x - width / 2 < 20 or args.x + width / 2 > 1060:
            raise SystemExit("thumbnail line exceeds horizontal safe area; change --x or add a manual line break")
        shadow_draw.text((args.x + 16, y + 20), line, font=font, anchor="ma", fill=(0, 0, 0, 220), stroke_width=args.stroke, stroke_fill=(0, 0, 0, 235))
        y += line_height + spacing
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    image = Image.alpha_composite(image.convert("RGBA"), shadow)

    draw = ImageDraw.Draw(image)
    y = args.y
    for line, box, line_fill in zip(lines, boxes, line_fills):
        draw.text((args.x, y), line, font=font, anchor="ma", fill=line_fill, stroke_width=args.stroke, stroke_fill="#000000")
        y += line_height + spacing

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(args.output, quality=95)
    print(json.dumps({"valid": True, "output": str(args.output), "size": [1080, 1920], "copy": normalized_text, "visible_characters": visible_character_count(normalized_text), "visible_characters_per_line": line_counts, "line_fills": line_fills, "stroke_width_px": args.stroke, "text_block_height": total_height}, ensure_ascii=False))


if __name__ == "__main__":
    main()
