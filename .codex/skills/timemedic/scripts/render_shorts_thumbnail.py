#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter


SERIES_FILL = "#000000"


def visible_character_count(text):
    return len(re.sub(r"[\s\W_]", "", text, flags=re.UNICODE))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("background", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--text", required=True)
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--layout", choices=("centered", "split-spatial", "reference-spatial", "deep-hook"), default="centered")
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
    parser.add_argument(
        "--top-width-scale",
        type=float,
        default=1.0,
        help="Horizontal scale for the top deep-hook tier; keeps its font height while fitting a longer setup line",
    )
    parser.add_argument("--stroke-color", default="#000000")
    parser.add_argument("--inner-stroke", type=int, default=14)
    parser.add_argument("--accent-fill", default="#FFD21F")
    parser.add_argument(
        "--foreground-polygon",
        default=None,
        help="Optional x:y comma-separated polygon restored above type, used to put the hero silhouette in front of background typography",
    )
    parser.add_argument(
        "--readability-veil",
        action="store_true",
        help="Apply a broad feathered warm-paper lift behind spatial type without boxes or outlines",
    )
    args = parser.parse_args()

    normalized_text = args.text.replace("\\n", "\n")
    lines = normalized_text.splitlines()
    line_counts = [visible_character_count(line) for line in lines]
    if args.layout == "deep-hook":
        if len(lines) != 2:
            raise SystemExit("deep-hook thumbnail copy must contain exactly two lines")
        if visible_character_count(normalized_text) > 10:
            raise SystemExit("deep-hook thumbnail copy exceeds 10 visible characters total")
        if args.stroke < 24 or args.stroke_color.upper() != "#FFFFFF":
            raise SystemExit("deep-hook requires a thick white outer stroke of at least 24px")
    elif args.layout in {"split-spatial", "reference-spatial"}:
        if len(lines) != 3:
            raise SystemExit("spatial thumbnail copy must contain exactly three blocks")
        if visible_character_count(normalized_text) > 10:
            raise SystemExit("spatial thumbnail copy exceeds 10 visible characters total")
        if args.layout == "reference-spatial" and (
            args.stroke != 0 or args.fill.upper() != SERIES_FILL
        ):
            raise SystemExit("reference-spatial typography requires solid black fill and no outline")
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
    foreground_source = image.convert("RGBA")
    font = ImageFont.truetype(str(args.font), args.font_size)
    line_fills = [args.fill.upper()] * len(lines)
    if args.line_fills:
        line_fills = [color.strip().upper() for color in args.line_fills.split(",")]
        if len(line_fills) != len(lines):
            raise SystemExit("--line-fills must contain exactly one color per text line")
    if args.layout == "centered" and any(color not in {"#FFFF00", "#00FF22", "#FF0033", "#FFFFFF"} for color in line_fills):
        raise SystemExit("legacy centered thumbnail fill uses the legacy SULL palette")
    if args.layout in {"split-spatial", "reference-spatial"}:
        line_fills = [SERIES_FILL] * 3

    if args.layout == "deep-hook":
        if not 0.5 <= args.top_width_scale <= 1.0:
            raise SystemExit("--top-width-scale must be between 0.5 and 1.0")
        fonts = [
            ImageFont.truetype(str(args.font), args.top_font_size),
            ImageFont.truetype(str(args.font), args.center_font_size),
        ]
        placements = [(args.center_x, args.top_y), (args.center_x, args.center_y)]
        fills = ["#FFFFFF", args.accent_fill.upper()]
        width_scales = [args.top_width_scale, 1.0]
        draw_probe = ImageDraw.Draw(image)
        block_boxes = []
        natural_boxes = []
        for line, block_font, (x, y), width_scale in zip(lines, fonts, placements, width_scales):
            box = draw_probe.textbbox((x, y), line, font=block_font, anchor="ma", stroke_width=args.stroke)
            scaled_width = round((box[2] - box[0]) * width_scale)
            scaled_box = (round(x - scaled_width / 2), box[1], round(x + scaled_width / 2), box[3])
            if scaled_box[0] < 28 or scaled_box[2] > 1052 or scaled_box[1] < 28 or scaled_box[3] > 1892:
                raise SystemExit(f"deep-hook block outside safe area: {line} {scaled_box}")
            natural_boxes.append(box)
            block_boxes.append(scaled_box)

        image = image.convert("RGBA")
        pad = args.stroke + 70
        for line, block_font, (x, _y), fill, width_scale, box in zip(
            lines, fonts, placements, fills, width_scales, natural_boxes
        ):
            block_width = box[2] - box[0]
            block_height = box[3] - box[1]
            layer = Image.new("RGBA", (block_width + pad * 2, block_height + pad * 2), (0, 0, 0, 0))
            origin = (pad - box[0] + x, pad - box[1] + _y)

            shadow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow)
            shadow_draw.text(
                (origin[0] + 18, origin[1] + 24), line, font=block_font, anchor="ma",
                fill=(0, 0, 0, 235), stroke_width=args.stroke + 4, stroke_fill=(0, 0, 0, 225)
            )
            shadow = shadow.filter(ImageFilter.GaussianBlur(10))
            layer = Image.alpha_composite(layer, shadow)

            layer_draw = ImageDraw.Draw(layer)
            layer_draw.text(
                origin, line, font=block_font, anchor="ma",
                fill="#FFFFFF", stroke_width=args.stroke, stroke_fill="#FFFFFF"
            )
            layer_draw.text(
                origin, line, font=block_font, anchor="ma",
                fill=fill, stroke_width=args.inner_stroke, stroke_fill="#111111"
            )
            if width_scale != 1.0:
                layer = layer.resize((round(layer.width * width_scale), layer.height), Image.Resampling.LANCZOS)
            paste_x = round(x - layer.width / 2)
            paste_y = box[1] - pad
            image.alpha_composite(layer, (paste_x, paste_y))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        image.convert("RGB").save(args.output, quality=95)
        print(json.dumps({
            "valid": True,
            "output": str(args.output),
            "size": [1080, 1920],
            "layout": "deep-hook",
            "copy_blocks": lines,
            "visible_characters": visible_character_count(normalized_text),
            "line_fills": fills,
            "outer_stroke_color": "#FFFFFF",
            "outer_stroke_width_px": args.stroke,
            "inner_stroke_color": "#111111",
            "inner_stroke_width_px": args.inner_stroke,
            "positions": placements,
            "font_sizes": [args.top_font_size, args.center_font_size],
            "top_width_scale": args.top_width_scale,
            "block_boxes": block_boxes,
        }, ensure_ascii=False))
        return

    if args.layout in {"split-spatial", "reference-spatial"}:
        fonts = [
            ImageFont.truetype(str(args.font), args.top_font_size),
            ImageFont.truetype(str(args.font), args.top_font_size),
            ImageFont.truetype(str(args.font), args.center_font_size),
        ]
        placements = [(args.left_x, args.top_y), (args.right_x, args.top_y), (args.center_x, args.center_y)]
        anchors = ["la", "ra", "ma"] if args.layout == "reference-spatial" else ["ma", "ma", "ma"]
        shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        block_boxes = []
        for line, block_font, (x, y), anchor in zip(lines, fonts, placements, anchors):
            box = shadow_draw.textbbox((x, y), line, font=block_font, anchor=anchor, stroke_width=args.stroke)
            if args.layout != "reference-spatial" and (box[0] < 40 or box[2] > 1040 or box[1] < 40 or box[3] > 1880):
                raise SystemExit(f"thumbnail block outside 40px safe area: {line} {box}")
            if args.layout == "reference-spatial" and (box[2] < 60 or box[0] > 1020 or box[3] < 60 or box[1] > 1860):
                raise SystemExit(f"reference block is effectively outside the canvas: {line} {box}")
            block_boxes.append(box)
            shadow_draw.text((x + 14, y + 18), line, font=block_font, anchor=anchor, fill=(0, 0, 0, 150))
        if args.readability_veil:
            veil_mask = Image.new("L", image.size, 0)
            veil_draw = ImageDraw.Draw(veil_mask)
            for left, top, right, bottom in block_boxes:
                veil_draw.rounded_rectangle((left - 34, top - 22, right + 34, bottom + 22), radius=50, fill=105)
            veil_mask = veil_mask.filter(ImageFilter.GaussianBlur(42))
            veil = Image.new("RGBA", image.size, (245, 222, 181, 0))
            veil.putalpha(veil_mask)
            image = Image.alpha_composite(image.convert("RGBA"), veil)
        shadow = shadow.filter(ImageFilter.GaussianBlur(8))
        image = Image.alpha_composite(image.convert("RGBA"), shadow)
        draw = ImageDraw.Draw(image)
        for line, block_font, (x, y), anchor in zip(lines, fonts, placements, anchors):
            draw.text((x, y), line, font=block_font, anchor=anchor, fill=SERIES_FILL, stroke_width=args.stroke, stroke_fill=args.stroke_color)
        foreground_polygon = None
        if args.foreground_polygon:
            try:
                foreground_polygon = [tuple(map(int, pair.split(":"))) for pair in args.foreground_polygon.split(",")]
            except ValueError as exc:
                raise SystemExit("--foreground-polygon must use x:y comma-separated integer points") from exc
            if len(foreground_polygon) < 3:
                raise SystemExit("--foreground-polygon requires at least three points")
            mask = Image.new("L", image.size, 0)
            ImageDraw.Draw(mask).polygon(foreground_polygon, fill=255)
            mask = mask.filter(ImageFilter.GaussianBlur(2))
            image.paste(foreground_source, (0, 0), mask)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        image.convert("RGB").save(args.output, quality=95)
        print(json.dumps({
            "valid": True,
            "output": str(args.output),
            "size": [1080, 1920],
            "layout": args.layout,
            "copy_blocks": lines,
            "visible_characters": visible_character_count(normalized_text),
            "fill": SERIES_FILL,
            "stroke_color": args.stroke_color,
            "stroke_width_px": args.stroke,
            "positions": placements,
            "font_sizes": [args.top_font_size, args.top_font_size, args.center_font_size],
            "block_boxes": block_boxes,
            "foreground_polygon": foreground_polygon,
            "readability_veil": args.readability_veil,
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
