#!/usr/bin/env python3
"""Makes every Android icon image from one file: branding/icon.png

Run from the repo root:   python3 tools/make_icons.py
(The GitHub build runs it for you before building the app.)
"""
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "branding" / "icon.png"
RES = ROOT / "app" / "src" / "main" / "res"

# Pixel sizes for each screen density
DENSITIES = ["mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi"]
LAUNCHER_SIZES = dict(zip(DENSITIES, [48, 72, 96, 144, 192]))     # old-style icon
ADAPTIVE_SIZES = dict(zip(DENSITIES, [108, 162, 216, 324, 432]))  # adaptive icon layer
NOTIFY_SIZES = dict(zip(DENSITIES, [24, 36, 48, 72, 96]))         # status bar icon

# Status bar icon: pixels darker than CUT_BELOW become see-through (the eyes),
# pixels brighter than SOLID_ABOVE stay solid white, in between fades smoothly.
CUT_BELOW = 50
SOLID_ABOVE = 78

if not SOURCE.exists():
    sys.exit("ERROR: branding/icon.png was not found. Add your icon image there.")

source = Image.open(SOURCE).convert("RGBA")
box = source.getchannel("A").getbbox()
if box is None:
    sys.exit("ERROR: icon.png is completely transparent.")

# Crop away the empty space around the icon, then make it square.
cropped = source.crop(box)
side = max(cropped.size)
square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
square.paste(cropped, ((side - cropped.width) // 2, (side - cropped.height) // 2))

count = 0


def save(image, path):
    global count
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, optimize=True)
    count += 1


def fit(canvas_size, fraction):
    """The icon, centred on a transparent canvas, using `fraction` of its width."""
    inner = max(1, int(canvas_size * fraction))
    small = square.resize((inner, inner), Image.LANCZOS)
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    canvas.paste(small, ((canvas_size - inner) // 2, (canvas_size - inner) // 2), small)
    return canvas


def silhouette(size):
    """White shape for the status bar. Dark parts (like eyes) become see-through."""
    big = size * 4
    img = square.resize((big, big), Image.LANCZOS)
    brightness = img.convert("L").point(
        lambda v: 0 if v <= CUT_BELOW else (255 if v >= SOLID_ABOVE
                                            else (v - CUT_BELOW) * 255 // (SOLID_ABOVE - CUT_BELOW)))
    alpha = Image.new("L", (big, big))
    alpha.paste(Image.composite(img.getchannel("A"), Image.new("L", (big, big), 0), brightness))
    white = Image.new("RGBA", (big, big), (255, 255, 255, 0))
    white.putalpha(alpha)
    return white.resize((size, size), Image.LANCZOS)


for d in DENSITIES:
    # Old-style launcher icons (Android 7)
    legacy = fit(LAUNCHER_SIZES[d], 0.88)
    save(legacy, RES / f"mipmap-{d}" / "ic_launcher.png")
    save(legacy, RES / f"mipmap-{d}" / "ic_launcher_round.png")
    # Adaptive icon front layer (Android 8 and newer). Kept inside the safe zone.
    save(fit(ADAPTIVE_SIZES[d], 0.60), RES / f"mipmap-{d}" / "ic_launcher_foreground.png")
    # Status bar notification icon
    save(silhouette(NOTIFY_SIZES[d]), RES / f"drawable-{d}" / "ic_stat_notify.png")

# Splash screen icon (one size is enough)
save(fit(864, 0.64), RES / "drawable-nodpi" / "splash_icon.png")

print(f"Made {count} images from {SOURCE.name}")
