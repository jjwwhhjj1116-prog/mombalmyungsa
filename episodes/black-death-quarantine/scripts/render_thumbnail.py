from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
QA = ROOT / "qa"
FONT_PATH = ASSETS / "GmarketSansTTFBold.ttf"
BACKGROUND_PATH = ASSETS / "frame-zero-bg-v1-landscape.png"
FINAL_PATH = ASSETS / "thumbnail-v1-landscape.png"
MOBILE_PATH = QA / "thumbnail-v1-mobile-25pct.jpg"

CANVAS = (1920, 1080)
SETUP = "5천만 명을 죽인"
KEYWORD = "흑사병"


def fit_font(text: str, max_width: int, start_size: int, min_size: int) -> ImageFont.FreeTypeFont:
    size = start_size
    while size >= min_size:
        font = ImageFont.truetype(str(FONT_PATH), size)
        box = font.getbbox(text, stroke_width=0)
        if box[2] - box[0] <= max_width:
            return font
        size -= 2
    return ImageFont.truetype(str(FONT_PATH), min_size)


def mask_for(text: str, font: ImageFont.FreeTypeFont, size: tuple[int, int], position: tuple[int, int]) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.text(position, text, font=font, fill=255, anchor="la")
    return mask


def add_setup(layer: Image.Image) -> None:
    font = fit_font(SETUP, 960, 150, 104)
    draw = ImageDraw.Draw(layer)
    x, y = 82, 105
    draw.text((x + 16, y + 20), SETUP, font=font, fill=(0, 0, 0, 235), stroke_width=15, stroke_fill=(0, 0, 0, 245), anchor="la")
    draw.text((x, y), SETUP, font=font, fill=(248, 248, 248, 255), stroke_width=11, stroke_fill=(17, 17, 17, 255), anchor="la")


def add_keyword(layer: Image.Image) -> None:
    font = fit_font(KEYWORD, 920, 330, 250)
    x, y = 78, 300

    # Deep stepped extrusion, kept behind the face and inside the left text zone.
    extrusion = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    extrusion_draw = ImageDraw.Draw(extrusion)
    for offset in range(40, 3, -4):
        shade = max(8, 44 - offset)
        extrusion_draw.text(
            (x + offset, y + offset),
            KEYWORD,
            font=font,
            fill=(shade, shade, 0, 255),
            stroke_width=18,
            stroke_fill=(0, 0, 0, 255),
            anchor="la",
        )
    layer.alpha_composite(extrusion)

    mask = mask_for(KEYWORD, font, CANVAS, (x, y))
    gradient = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    pixels = gradient.load()
    top = y
    bottom = min(CANVAS[1] - 1, y + font.size + 70)
    for py in range(top, bottom + 1):
        t = (py - top) / max(1, bottom - top)
        r = round(255 - 18 * t)
        g = round(236 - 74 * t)
        b = round(118 - 112 * t)
        for px in range(CANVAS[0]):
            pixels[px, py] = (r, g, b, 255)

    outline = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    outline_draw = ImageDraw.Draw(outline)
    outline_draw.text((x, y), KEYWORD, font=font, fill=(255, 255, 255, 0), stroke_width=23, stroke_fill=(5, 5, 5, 255), anchor="la")
    outline_draw.text((x, y), KEYWORD, font=font, fill=(255, 255, 255, 0), stroke_width=8, stroke_fill=(255, 207, 32, 255), anchor="la")
    layer.alpha_composite(outline)
    layer.alpha_composite(Image.composite(gradient, Image.new("RGBA", CANVAS), mask))

    shine = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    shine_draw = ImageDraw.Draw(shine)
    shine_draw.text((x, y - 3), KEYWORD, font=font, fill=(255, 255, 255, 0), stroke_width=2, stroke_fill=(255, 250, 205, 230), anchor="la")
    shine.putalpha(ImageChops.multiply(shine.getchannel("A"), mask))
    layer.alpha_composite(shine)


def main() -> None:
    QA.mkdir(parents=True, exist_ok=True)
    background = Image.open(BACKGROUND_PATH).convert("RGB")
    background = background.resize(CANVAS, Image.Resampling.LANCZOS)
    base = background.convert("RGBA")

    # A gentle left-side reading surface preserves the generated miniature scene.
    shade = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    shade_draw = ImageDraw.Draw(shade)
    for px in range(0, 1120):
        alpha = round(80 * (1 - px / 1120))
        shade_draw.line((px, 0, px, 760), fill=(0, 0, 0, alpha))
    shade = shade.filter(ImageFilter.GaussianBlur(18))
    base.alpha_composite(shade)

    text_layer = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    add_setup(text_layer)
    add_keyword(text_layer)
    base.alpha_composite(text_layer)

    base.convert("RGB").save(FINAL_PATH, quality=96)
    base.convert("RGB").resize((480, 270), Image.Resampling.LANCZOS).save(MOBILE_PATH, quality=94)


if __name__ == "__main__":
    main()
