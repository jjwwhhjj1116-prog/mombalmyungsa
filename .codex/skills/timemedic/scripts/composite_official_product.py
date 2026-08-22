#!/usr/bin/env python3
"""Extract an official white-background packshot and place it on a frame-zero background."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter


def white_to_alpha(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    rgb = rgba.convert("RGB")
    white = Image.new("RGB", rgb.size, "white")
    distance = ImageChops.difference(rgb, white).convert("L")
    alpha = distance.point(lambda value: 0 if value < 8 else min(255, (value - 8) * 5))
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.8))
    rgba.putalpha(alpha)
    return rgba


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("background", type=Path)
    parser.add_argument("official_image", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--crop", default="1100,120,1700,1320")
    parser.add_argument("--height", type=int, default=650)
    parser.add_argument("--x", type=int, default=720)
    parser.add_argument("--y", type=int, default=1040)
    args = parser.parse_args()

    if not args.background.is_file() or not args.official_image.is_file():
        raise SystemExit("background or official image missing")

    crop = tuple(int(value) for value in args.crop.split(","))
    if len(crop) != 4:
        raise SystemExit("--crop requires left,top,right,bottom")

    canvas = Image.open(args.background).convert("RGBA").resize((1080, 1920), Image.Resampling.LANCZOS)
    source = Image.open(args.official_image).convert("RGB").crop(crop)
    packshot = white_to_alpha(source)
    bbox = packshot.getchannel("A").getbbox()
    if not bbox:
        raise SystemExit("packshot extraction produced an empty alpha mask")
    packshot = packshot.crop(bbox)
    width = round(packshot.width * args.height / packshot.height)
    packshot = packshot.resize((width, args.height), Image.Resampling.LANCZOS)

    shadow_mask = packshot.getchannel("A").filter(ImageFilter.GaussianBlur(18))
    shadow = Image.new("RGBA", packshot.size, (20, 8, 0, 175))
    shadow.putalpha(shadow_mask.point(lambda value: round(value * 0.65)))
    canvas.alpha_composite(shadow, (args.x + 18, args.y + 24))
    canvas.alpha_composite(packshot, (args.x, args.y))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(args.output, quality=96)
    print(f"saved {args.output} packshot_size={packshot.size} position=({args.x},{args.y})")


if __name__ == "__main__":
    main()
