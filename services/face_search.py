"""
Method 2: face recognition search engines.

  FaceCheck.ID  — free, unofficial API, works out of the box
  Search4Faces  — free, public API, works out of the box
  PimEyes       — paid, stub wired to PIMEYES_API_KEY
"""
from __future__ import annotations

import asyncio
import base64
from typing import Any

import aiohttp

from config import (
    FACECHECK_API_KEY,
    PIMEYES_API_KEY,
    FACE_SEARCH_TIMEOUT,
)

FACECHECK_UPLOAD = "https://facecheck.id/api/upload_pic"
FACECHECK_SEARCH = "https://facecheck.id/api/search"
SEARCH4FACES_API = "https://search4faces.com/api/search.php"


# --------------------------------------------------------------------------- #
#  FaceCheck.ID — free
# --------------------------------------------------------------------------- #

async def facecheck_search(image_bytes: bytes) -> dict[str, Any]:
    headers = {"Content-Type": "image/jpeg"}
    if FACECHECK_API_KEY:
        headers["Authorization"] = f"Bearer {FACECHECK_API_KEY}"

    timeout = aiohttp.ClientTimeout(total=FACE_SEARCH_TIMEOUT)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(FACECHECK_UPLOAD, data=image_bytes, headers=headers) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    return {
                        "ok": False,
                        "engine": "FaceCheck.ID",
                        "error": f"Upload failed ({resp.status}): {text[:200]}",
                    }
                upload = await resp.json()

            id_search = upload.get("id_search")
            if not id_search:
                return {
                    "ok": False,
                    "engine": "FaceCheck.ID",
                    "error": "No search ID returned (image may contain no face)",
                }

            for _ in range(FACE_SEARCH_TIMEOUT // 2):
                payload = {
                    "id_search": id_search,
                    "with_progress": True,
                    "status_only": False,
                    "demo": False,
                }
                async with session.post(FACECHECK_SEARCH, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        return {
                            "ok": False,
                            "engine": "FaceCheck.ID",
                            "error": f"Search failed ({resp.status})",
                        }
                    data = await resp.json()

                if data.get("output"):
                    raw = data["output"]
                    matches = []
                    for m in raw:
                        matches.append({
                            "score": float(m.get("score") or 0.0),
                            "url": m.get("url") or "",
                            "thumbnail_b64": m.get("base64") or "",
                            "guid": m.get("guid") or "",
                            "group": m.get("group") or "",
                        })
                    return {"ok": True, "engine": "FaceCheck.ID", "matches": matches}

                if data.get("message"):
                    return {
                        "ok": False,
                        "engine": "FaceCheck.ID",
                        "error": data["message"],
                    }

                await asyncio.sleep(2)

            return {
                "ok": False,
                "engine": "FaceCheck.ID",
                "error": "Search timed out",
            }
    except asyncio.TimeoutError:
        return {"ok": False, "engine": "FaceCheck.ID", "error": "Request timed out"}
    except Exception as e:
        return {"ok": False, "engine": "FaceCheck.ID", "error": str(e)}


# --------------------------------------------------------------------------- #
#  Search4Faces — free
# --------------------------------------------------------------------------- #

async def search4faces_search(image_bytes: bytes) -> dict[str, Any]:
    try:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        payload = {
            "image": encoded,
            "fields": ["vk", "ok", "tiktok", "clubhouse"],
        }

        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(SEARCH4FACES_API, json=payload) as resp:
                if resp.status != 200:
                    return {
                        "ok": False,
                        "engine": "Search4Faces",
                        "error": f"HTTP {resp.status}",
                    }
                data = await resp.json()

        if data.get("status") != "ok":
            return {
                "ok": False,
                "engine": "Search4Faces",
                "error": data.get("message") or "Search failed",
            }

        matches = []
        for m in data.get("found", []):
            matches.append({
                "service": m.get("service", "?"),
                "profile_url": m.get("profile") or m.get("url") or "",
                "photo_url": m.get("photo") or "",
                "similarity": float(m.get("similarity") or 0.0),
            })

        return {"ok": True, "engine": "Search4Faces", "matches": matches}

    except Exception as e:
        return {"ok": False, "engine": "Search4Faces", "error": str(e)}


# --------------------------------------------------------------------------- #
#  PimEyes — paid BYOK
# --------------------------------------------------------------------------- #

async def pimeyes_search(image_bytes: bytes) -> dict[str, Any]:
    if not PIMEYES_API_KEY:
        return {
            "ok": False,
            "engine": "PimEyes",
            "error": (
                "PimEyes requires a paid API subscription. "
                "Set PIMEYES_API_KEY in .env to enable."
            ),
        }

    try:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        headers = {"Authorization": f"Bearer {PIMEYES_API_KEY}"}
        payload = {"image": encoded, "limit": 10}

        timeout = aiohttp.ClientTimeout(total=90)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                "https://api.pimeyes.com/v1/search",
                json=payload,
                headers=headers,
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    return {
                        "ok": False,
                        "engine": "PimEyes",
                        "error": f"HTTP {resp.status}: {text[:150]}",
                    }
                data = await resp.json()

        matches = [
            {
                "url": m.get("url", ""),
                "score": float(m.get("confidence") or 0.0),
            }
            for m in data.get("results", [])
        ]
        return {"ok": True, "engine": "PimEyes", "matches": matches}

    except Exception as e:
        return {"ok": False, "engine": "PimEyes", "error": str(e)}


# --------------------------------------------------------------------------- #
#  Formatting
# --------------------------------------------------------------------------- #

def format_face_results(result: dict[str, Any]) -> str:
    engine = result.get("engine", "Search")

    if not result.get("ok"):
        return f"❌ <b>{engine}</b>\n\n{result.get('error', 'Unknown error')}"

    matches = result.get("matches", [])
    if not matches:
        return (
            f"🔍 <b>{engine}</b>\n\n"
            "No matches found.\n\n"
            "This can mean:\n"
            "• The face isn't indexed in this engine's database\n"
            "• No face was detected in the image\n"
            "• The image quality is too low\n\n"
            "Try a clearer, front-facing photo."
        )

    def _score(m):
        s = m.get("score") or m.get("similarity") or 0.0
        return s if s > 1.0 else s * 100

    matches = sorted(matches, key=_score, reverse=True)

    lines = [f"🔍 <b>{engine} — {len(matches)} matches</b>", "━━━━━━━━━━━━━━━━━━"]

    for i, m in enumerate(matches[:8], 1):
        raw_score = m.get("score") or m.get("similarity") or 0.0
        pct = int(raw_score * 100) if raw_score <= 1.0 else int(raw_score)

        if pct >= 85:
            label = "🟢"
        elif pct >= 70:
            label = "🟡"
        elif pct >= 50:
            label = "🟠"
        else:
            label = "⚪"

        service = m.get("service", "")
        url = m.get("url") or m.get("profile_url") or ""
        prefix = f"[{service}] " if service else ""

        if url:
            lines.append(f"{label} {i}. {prefix}<code>{pct}%</code> <a href='{url}'>Open profile</a>")
        else:
            lines.append(f"{label} {i}. {prefix}<code>{pct}%</code> (no direct link)")

    lines.append("")
    lines.append(
        "<i>🟢 85%+ strong · 🟡 70–84% likely · "
        "🟠 50–69% possible · ⚪ &lt;50% weak</i>"
    )
    lines.append("<i>Verify matches manually — never assume from score alone.</i>")

    return "\n".join(lines)
