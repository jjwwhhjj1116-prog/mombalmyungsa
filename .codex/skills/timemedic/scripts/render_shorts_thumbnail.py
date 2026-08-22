#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter


SERIES_FILL = "#000000"
SERIES_STROKE = "#D4AF37"


def visible_character_count(text):
    return len(re.sub(r"[\s\W_]", "", text, flags=re.UNICODE))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("background", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--text", required=True)
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--layout", choices=("centered", "split-spatial"), default="centered")
    parser.add_argument("--font-size", type=int, default=175)
    parser.add_argument("--stroke", type=int, default=30)
    parser.add_argument("--fill", default="#FFFF00")
    parser.add_argument("--line-fills", default=None, help="Comma-separated SULL palette colors; one per line")
    parser.add_argument("--y", type=int, default=170)
    parser.add_argument("--x", type=int, default=540)
    parser.add_argument("--left-x", type=int, default=250)
    parser.add_argument("--right-x", type=int, default=810)
    parser.add_argument("--top-y", type=int, default=150)
    parser.add_argument("--center-x", type=int, default=540)
    parser.add_argument("--center-y", type=int, default=500)
    parser.add_argument("--top-font-size", type=int, default=245)
    parser.add_argument("--center-font-size", type=int, default=300)
    parser.add_argument("--stroke-color", default="#000000")
    args = parser.parse_args()

    normalized_text = args.text.replace("\\n", "\n")
    lines = normalized_text.splitlines()
    line_counts = [visible_character_count(line) for line in lines]
    if args.layout == "split-spatial":
        if len(lines) != 3:
            raise SystemExit("split-spatial thumbnail copy must contain exactly three blocks")
        if visible_character_count(normalized_text) > 10:
            raise SystemExit("split-spatial thumbnail copy exceeds 10 visible characters total")
        if args.stroke != 60 or args.stroke_color.upper() != SERIES_STROKE or args.fill.upper() != SERIES_FILL:
            raise SystemExit("split-spatial series typography requires black fill and 60px #D4AF37 stroke")
    else:
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
    line_fills = [args.fill.upper()] * len(lines)
    if args.line_fills:
        line_fills = [color.strip().upper() for color in args.line_fills.split(",")]
        if len(line_fills) != len(lines):
            raise SystemExit("--line-fills must contain exactly one color per text line")
    if args.layout == "centered" and any(color not in {"#FFFF00", "#00FF22", "#FF0033", "#FFFFFF"} for color in line_fills):
        raise SystemExit("legacy centered thumbnail fill uses the legacy SULL palette")
    if args.layout == "split-spatial":
        line_fills = [SERIES_FILL] * 3

    if args.layout == "split-spatial":
        fonts = [
            ImageFont.truetype(str(args.font), args.top_font_size),
            ImageFont.truetype(str(args.font), args.top_font_size),
            ImageFont.truetype(str(args.font), args.center_font_size),
        ]
        placements = [
            (args.left_x, args.top_y),
            (args.right_x, args.top_y),
            (args.center_x, args.center_y),
        ]
        shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        block_boxes = []
        for line, block_font, (x, y) in zip(lines, fonts, placements):
            box = shadow_draw.textbbox((x, y), line, font=block_font, anchor="ma", stroke_width=args.stroke)
            if box[0] < 40 or box[2] > 1040 or box[1] < 40 or box[3] > 1880:
                raise SystemExit(f"thumbnail block outside 40px safe area: {line} {box}")
            block_boxes.append(box)
            shadow_draw.text((x + 20, y + 28), line, font=block_font, anchor="ma", fill=(0, 0, 0, 245), stroke_width=args.stroke, stroke_fill=(0, 0, 0, 245))
        shadow = shadow.filter(ImageFilter.GaussianBlur(12))
        image = Image.alpha_composite(image.convert("RGBA"), shadow)
        draw = ImageDraw.Draw(image)
        for line, block_font, (x, y) in zip(lines, fonts, placements):
            draw.text((x, y), line, font=block_font, anchor="ma", fill=SERIES_FILL, stroke_width=args.stroke, stroke_fill=SERIES_STROKE)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        image.convert("RGB").save(args.output, quality=95)
        print(json.dumps({
            "valid": True,
            "output": str(args.output),
            "size": [1080, 1920],
            "layout": "split-spatial",
            "copy_blocks": lines,
            "visible_characters": visible_character_count(normalized_text),
            "fill": SERIES_FILL,
            "stroke_color": SERIES_STROKE,
            "stroke_width_px": args.stroke,
            "positions": placements,
            "font_sizes": [args.top_font_size, args.top_font_size, args.center_font_size],
            "block_boxes": block_boxes,
        }, ensure_ascii=False))
        return
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
        draw.text((args.x, y), line, font=font, anchor="ma", fill=line_fill, stroke_width=args.stroke, stroke_fill=args.stroke_color)
        y += line_height + spacing

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(args.output, quality=95)
    print(json.dumps({"valid": True, "output": str(args.output), "size": [1080, 1920], "layout": "centered", "copy": normalized_text, "visible_characters": visible_character_count(normalized_text), "visible_characters_per_line": line_counts, "line_fills": line_fills, "stroke_width_px": args.stroke, "text_block_height": total_height}, ensure_ascii=False))


if __name__ == "__main__":
    main()
