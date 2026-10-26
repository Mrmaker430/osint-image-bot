"""
Method 3: contextual clue helpers — cropping and text enhancement.
"""
from __future__ import annotations

import io

from PIL import Image, ImageFilter, ImageEnhance


def crop_regions(image_bytes: bytes, grid: int = 2) -> list[tuple[str, bytes]]:
    """Crop the image into a grid of regions and return them as bytes."""
    img = Image.open(io.BytesIO(image_bytes))
    w, h = img.size
    regions = []
    cw, ch = w // grid, h // grid

    for row in range(grid):
        for col in range(grid):
            box = (col * cw, row * ch, (col + 1) * cw, (row + 1) * ch)
            cropped = img.crop(box)
            buf = io.BytesIO()
            cropped.save(buf, format="JPEG", quality=90)
            label = f"region_{row+1}_{col+1}"
            regions.append((label, buf.getvalue()))

    return regions


def enhance_for_text(image_bytes: bytes) -> bytes:
    """Sharpen and increase contrast to make small text in the image readable."""
    img = Image.open(io.BytesIO(image_bytes))
    img = img.convert("L")
    img = img.filter(ImageFilter.SHARPEN)
    img = ImageEnhance.Contrast(img).enhance(2.0)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()
