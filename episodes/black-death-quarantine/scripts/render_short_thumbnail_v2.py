from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
QA = ROOT / "qa"
FONT_PATH = ASSETS / "GmarketSansTTFBold.ttf"
BACKGROUND_PATH = ASSETS / "frame-zero-bg-v2-short.png"
FINAL_PATH = ASSETS / "thumbnail-v2-short.png"
MOBILE_PATH = QA / "thumbnail-v2-short-mobile-25pct.jpg"

CANVAS = (1080, 1920)
SETUP = "5천만 명을 죽인"
KEYWORD = "흑사병"


def fit_font(text: str, max_width: int, start_size: int, min_size: int) -> ImageFont.FreeTypeFont:
    for size in range(start_size, min_size - 1, -2):
        font = ImageFont.truetype(str(FONT_PATH), size)
        box = font.getbbox(text, stroke_width=0)
        if box[2] - box[0] <= max_width:
            return font
    return ImageFont.truetype(str(FONT_PATH), min_size)


def centered_x(text: str, font: ImageFont.FreeTypeFont) -> int:
    box = font.getbbox(text, stroke_width=0)
    return (CANVAS[0] - (box[2] - box[0])) // 2 - box[0]


def add_text(base: Image.Image) -> None:
    layer = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    setup_font = fit_font(SETUP, 940, 124, 92)
    setup_x = centered_x(SETUP, setup_font)
    setup_y = 72
    draw.text(
        (setup_x + 11, setup_y + 16),
        SETUP,
        font=setup_font,
        fill=(0, 0, 0, 245),
        stroke_width=18,
        stroke_fill=(0, 0, 0, 255),
    )
    draw.text(
        (setup_x, setup_y),
        SETUP,
        font=setup_font,
        fill=(250, 250, 250, 255),
        stroke_width=12,
        stroke_fill=(17, 17, 17, 255),
    )

    keyword_font = fit_font(KEYWORD, 900, 300, 246)
    keyword_x = centered_x(KEYWORD, keyword_font)
    keyword_y = 238

    for offset in range(42, 5, -4):
        shade = max(5, 42 - offset)
        draw.text(
            (keyword_x + offset, keyword_y + offset),
            KEYWORD,
            font=keyword_font,
            fill=(shade, shade, 0, 255),
            stroke_width=24,
            stroke_fill=(0, 0, 0, 255),
        )

    draw.text(
        (keyword_x, keyword_y),
        KEYWORD,
        font=keyword_font,
        fill=(255, 210, 31, 255),
        stroke_width=30,
        stroke_fill=(255, 255, 255, 255),
    )
    draw.text(
        (keyword_x, keyword_y),
        KEYWORD,
        font=keyword_font,
        fill=(255, 210, 31, 255),
        stroke_width=14,
        stroke_fill=(17, 17, 17, 255),
    )
    base.alpha_composite(layer)


def main() -> None:
    QA.mkdir(parents=True, exist_ok=True)
    background = Image.open(BACKGROUND_PATH).convert("RGB").resize(CANVAS, Image.Resampling.LANCZOS)
    base = background.convert("RGBA")

    reading_surface = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    surface_draw = ImageDraw.Draw(reading_surface)
    for py in range(0, 670):
        alpha = round(132 * (1 - py / 670))
        surface_draw.line((0, py, CANVAS[0], py), fill=(0, 0, 0, max(0, alpha)))
    reading_surface = reading_surface.filter(ImageFilter.GaussianBlur(16))
    base.alpha_composite(reading_surface)

    add_text(base)
    base.convert("RGB").save(FINAL_PATH, quality=97)
    base.convert("RGB").resize((270, 480), Image.Resampling.LANCZOS).save(MOBILE_PATH, quality=95)


if __name__ == "__main__":
    main()
