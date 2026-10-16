"""Regenerates the app icon (release/windows/app.ico and the window icon PNG). Dev tool: needs Pillow.

    python release/windows/make_icon.py

Design: a white plate on a blue rounded square, with a ring split into the three macros
(protein = green, carbohydrates = amber, fat = coral).
"""

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
ICO_PATH = ROOT / "release" / "windows" / "app.ico"
PNG_PATH = ROOT / "src" / "calorie_tracker" / "presentation" / "assets" / "app_icon.png"

SIZE = 2048  # drawn large, then scaled down for smooth edges
CENTER = SIZE // 2


def lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def background() -> Image.Image:
    top, bottom = (96, 124, 232), (42, 66, 166)
    gradient = Image.new("RGBA", (SIZE, SIZE))
    pixels = ImageDraw.Draw(gradient)
    for y in range(SIZE):
        pixels.line([(0, y), (SIZE, y)], fill=lerp(top, bottom, y / SIZE) + (255,))
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=470, fill=255)
    gradient.putalpha(mask)
    return gradient


def circle(draw, radius, fill, center=(CENTER, CENTER)):
    cx, cy = center
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=fill)


def build_master() -> Image.Image:
    image = background()

    # soft shadow under the plate
    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    circle(ImageDraw.Draw(shadow), 800, (15, 25, 80, 120), (CENTER, CENTER + 50))
    shadow = shadow.filter(ImageFilter.GaussianBlur(40))
    image = Image.alpha_composite(image, shadow)

    draw = ImageDraw.Draw(image)
    circle(draw, 800, (255, 255, 255, 255))          # plate
    circle(draw, 700, (226, 233, 248, 255))          # rim groove
    circle(draw, 676, (255, 255, 255, 255))          # plate centre

    # macro ring: protein / carbs / fat (clockwise from the top), with small gaps
    segments = ((0, 140, (46, 178, 107)), (140, 250, (245, 166, 35)), (250, 360, (239, 91, 91)))
    outer, inner, gap = 560, 330, 5
    box = [CENTER - outer, CENTER - outer, CENTER + outer, CENTER + outer]
    for start, end, color in segments:
        draw.pieslice(box, start - 90 + gap, end - 90 - gap, fill=color + (255,))
    circle(draw, inner, (255, 255, 255, 255))        # ring hole
    circle(draw, 150, (47, 70, 168, 255))            # centre dot (reads well at small sizes)
    return image


def main() -> None:
    master = build_master()
    PNG_PATH.parent.mkdir(parents=True, exist_ok=True)
    master.resize((256, 256), Image.LANCZOS).save(PNG_PATH)
    master.resize((256, 256), Image.LANCZOS).save(
        ICO_PATH, format="ICO", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)]
    )
    print(f"wrote {ICO_PATH} and {PNG_PATH}")


if __name__ == "__main__":
    main()
