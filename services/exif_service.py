"""
Extract EXIF, GPS, and metadata from images.
Handles both raw bytes (from Telegram documents) and file paths.
"""
from __future__ import annotations

import io
from typing import Any

import exifread
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS


def _gps_to_decimal(gps_data: dict) -> tuple[float, float] | None:
    """Convert EXIF GPS DMS to decimal degrees."""
    try:
        def to_deg(val):
            d, m, s = val
            return float(d) + float(m) / 60 + float(s) / 3600

        lat = to_deg(gps_data[2])
        lon = to_deg(gps_data[4])

        if gps_data.get(1) == "S":
            lat = -lat
        if gps_data.get(3) == "W":
            lon = -lon
        return lat, lon
    except Exception:
        return None


def extract_exif(data: bytes) -> dict[str, Any]:
    """
    Extract everything possible from image bytes.
    Returns a dict with: basic, camera, gps, timestamps, raw_tags.
    """
    result: dict[str, Any] = {
        "basic": {},
        "camera": {},
        "gps": {},
        "timestamps": {},
        "raw_tags": {},
        "has_exif": False,
    }

    try:
        img = Image.open(io.BytesIO(data))
        result["basic"] = {
            "format": img.format,
            "mode": img.mode,
            "size": f"{img.width}x{img.height}",
        }

        exif = img.getexif()
        if not exif:
            return result

        result["has_exif"] = True
        decoded = {TAGS.get(tag, tag): value for tag, value in exif.items()}

        for key in ("Make", "Model", "LensModel", "Software"):
            if key in decoded:
                result["camera"][key] = str(decoded[key])

        for key in ("DateTime", "DateTimeOriginal", "DateTimeDigitized"):
            if key in decoded:
                result["timestamps"][key] = str(decoded[key])

        gps_ifd = exif.get_ifd(0x8825)
        if gps_ifd:
            gps_decoded = {GPSTAGS.get(k, k): v for k, v in gps_ifd.items()}
            coords = _gps_to_decimal(gps_decoded)
            if coords:
                result["gps"] = {
                    "latitude": round(coords[0], 6),
                    "longitude": round(coords[1], 6),
                    "maps_url": f"https://www.google.com/maps?q={coords[0]},{coords[1]}",
                }

        tags = exifread.process_file(io.BytesIO(data), details=False)
        result["raw_tags"] = {k: str(v) for k, v in tags.items()}

        return result

    except Exception as e:
        result["error"] = str(e)
        return result


def format_exif_report(exif: dict[str, Any]) -> str:
    """Build a clean Telegram-friendly HTML report."""
    if exif.get("error"):
        return f"❌ Could not read image: {exif['error']}"

    if not exif["has_exif"]:
        return (
            "⚠️ <b>No EXIF data found.</b>\n\n"
            "This usually means one of two things:\n"
            "• The image was sent as a <b>photo</b> and Telegram stripped the metadata.\n"
            "• The image was exported from a social media app that removes EXIF.\n\n"
            "<b>Tip:</b> Send the original file as a <b>Document</b> "
            "(paperclip → File) to preserve metadata."
        )

    lines = ["<b>📸 Image Metadata</b>", "━━━━━━━━━━━━━━━━━━"]

    b = exif["basic"]
    if b:
        lines.append(f"<b>Format:</b> {b.get('format')} · {b.get('size')}")

    if exif["camera"]:
        lines.append("\n<b>📷 Camera</b>")
        for k, v in exif["camera"].items():
            lines.append(f"  {k}: <code>{v}</code>")

    if exif["timestamps"]:
        lines.append("\n<b>🕒 Timestamps</b>")
        for k, v in exif["timestamps"].items():
            lines.append(f"  {k}: <code>{v}</code>")

    if exif["gps"]:
        g = exif["gps"]
        lines.append("\n<b>📍 GPS</b>")
        lines.append(f"  Latitude: <code>{g['latitude']}</code>")
        lines.append(f"  Longitude: <code>{g['longitude']}</code>")
        lines.append(f'  <a href="{g["maps_url"]}">Open in Google Maps</a>')
    else:
        lines.append("\n<b>📍 GPS:</b> Not present")

    return "\n".join(lines)
