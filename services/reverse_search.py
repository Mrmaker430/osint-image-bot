"""
Method 3: reverse image search via Google Lens + external engine links.
"""
from __future__ import annotations

import asyncio
import os
import tempfile
from typing import Any

from googlelens import GoogleLens


_lens = GoogleLens()


async def google_lens_search(image_bytes: bytes) -> dict[str, Any]:
    """Run Google Lens and return the top results."""
    loop = asyncio.get_event_loop()

    try:
        result = await loop.run_in_executor(
            None, lambda: _lens.search_by_file_bytes(image_bytes)
        )
        return {"ok": True, "engine": "Google Lens", "data": result}
    except Exception:
        # Fallback: write to temp file
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        try:
            tmp.write(image_bytes)
            tmp.close()
            result = await loop.run_in_executor(
                None, lambda: _lens.search_by_file(tmp.name)
            )
            return {"ok": True, "engine": "Google Lens", "data": result}
        except Exception as e2:
            return {"ok": False, "engine": "Google Lens", "error": str(e2)}
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass


def build_search_links(image_url: str) -> list[dict[str, str]]:
    """Build direct reverse-search URLs for engines that accept a public image URL."""
    encoded = image_url.replace("&", "%26").replace("?", "%3F")
    return [
        {
            "name": "Google Images",
            "url": f"https://lens.google.com/uploadbyurl?url={encoded}",
        },
        {
            "name": "Yandex Images",
            "url": f"https://yandex.com/images/search?rpt=imageview&url={encoded}",
        },
        {
            "name": "Bing Visual Search",
            "url": f"https://www.bing.com/images/search?view=detailv2&iss=sbi&form=SBIVSP&sbisrc=UrlPaste&q=imgurl:{encoded}",
        },
        {
            "name": "TinEye",
            "url": f"https://tineye.com/search?url={encoded}",
        },
    ]


def format_lens_results(result: dict[str, Any]) -> str:
    """Format Google Lens results for Telegram."""
    if not result.get("ok"):
        return f"❌ <b>{result['engine']}</b>: {result.get('error', 'Search failed')}"

    data = result["data"]
    if isinstance(data, dict):
        matches = data.get("matches") or data.get("results") or []
    elif isinstance(data, list):
        matches = data
    else:
        matches = []

    if not matches:
        return f"🔍 <b>{result['engine']}</b>: No matches found."

    lines = [f"<b>🔍 {result['engine']} — {len(matches)} matches</b>", "━━━━━━━━━━━━━━━━━━"]

    for i, m in enumerate(matches[:5], 1):
        if isinstance(m, dict):
            title = m.get("title") or m.get("name") or "Untitled"
            url = m.get("url") or m.get("link") or ""
            lines.append(f"{i}. {title[:80]}")
            if url:
                lines.append(f'   <a href="{url}">Open</a>')
        else:
            lines.append(f"{i}. {str(m)[:80]}")

    return "\n".join(lines)
