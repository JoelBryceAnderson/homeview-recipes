#!/usr/bin/env python3
"""Attach a photo to a recipe: python3 add_image.py <slug> <photo>

Fixes rotation, resizes to 1600px max, strips EXIF (including phone GPS),
saves images/<slug>.jpg and sets "image" in recipes/<slug>.json.
Requires Pillow (pip install pillow).
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageOps

try:  # iPhone HEIC photos, if pillow-heif is installed
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    pass

ROOT = Path(__file__).parent
MAX = 1600


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    slug, src = sys.argv[1], Path(sys.argv[2])
    recipe = ROOT / "recipes" / f"{slug}.json"
    if not recipe.is_file():
        sys.exit(f"No recipe at {recipe}")

    img = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    img.thumbnail((MAX, MAX), Image.LANCZOS)
    out = ROOT / "images" / f"{slug}.jpg"
    out.parent.mkdir(exist_ok=True)
    img.save(out, "JPEG", quality=85, optimize=True, progressive=True)  # no EXIF

    data = json.loads(recipe.read_text())
    data["image"] = f"images/{slug}.jpg"
    recipe.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"Saved {out.relative_to(ROOT)} ({img.width}x{img.height}) and updated {recipe.name}")


if __name__ == "__main__":
    main()
