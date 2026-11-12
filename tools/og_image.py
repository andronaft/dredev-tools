#!/usr/bin/env python3
"""The share image of the calculator site (1200x630): assets/og.jpg, used as og:image on every page.

Needs Pillow and the macOS system fonts:  /usr/bin/python3 tools/og_image.py
Run it again only if the site's name or tagline changes.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent.parent
W, H, PAD = 1200, 630, 80
BG, INK, MUTED, LINE = "#f6f7f9", "#14181f", "#5b6575", "#e3e7ee"
AVENIR = "/System/Library/Fonts/Avenir Next.ttc"


def font(size, index=0):  # 0 bold, 2 demi bold, 5 medium
    return ImageFont.truetype(AVENIR, size, index=index)


img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)
# The site's mark: a rounded square with the amber-to-red gradient of the favicon.
mark = Image.new("RGB", (96, 96))
px = mark.load()
for y in range(96):
    for x in range(96):
        t = (x + y) / 190
        px[x, y] = tuple(round(a + (b - a) * t) for a, b in zip((0xF5, 0x9E, 0x0B), (0xEF, 0x44, 0x44)))
mask = Image.new("L", (96, 96), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, 95, 95], radius=26, fill=255)
img.paste(mark, (PAD, PAD), mask)
d.text((PAD + 120, PAD + 18), "Dre Dev Tools", font=font(52), fill=INK)
d.text((PAD, 250), "Free calculators", font=font(92), fill=INK)
d.text((PAD, 350), "for the trades", font=font(92), fill=INK)
d.text((PAD, 478), "HVAC · electrical · coatings · pool · baking · soap", font=font(34, 5), fill=MUTED)
d.line([(PAD, H - 78), (W - PAD, H - 78)], fill=LINE, width=2)
d.text((PAD, H - 62), "zhukovskyi.space/calculators", font=font(28, 2), fill=MUTED)
d.text((W - PAD, H - 62), "Tables with sources · no account", font=font(28, 5), fill=MUTED, anchor="ra")
img.save(HERE / "assets" / "og.jpg", quality=88, optimize=True)
print(HERE / "assets" / "og.jpg")
