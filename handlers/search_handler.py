"""
Single callback handler for all inline keyboards:
  - method selection (2 vs 3)
  - Method 2 submenu (face engines)
  - Method 3 submenu (metadata tools)
  - back navigation
"""
from __future__ import annotations

import base64
import io
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import FACE_SEARCH_COOLDOWN
from services.exif_service import format_exif_report
from services.reverse_search import google_lens_search, format_lens_results
from services.context_service import crop_regions, enhance_for_text
from services.face_search import (
    facecheck_search,
    search4faces_search,
    pimeyes_search,
    format_face_results,
)


# --------------------------------------------------------------------------- #
#  Keyboards
# --------------------------------------------------------------------------- #

def _method_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Method 2 — Face Search", callback_data="method_select:2")],
        [InlineKeyboardButton("📸 Method 3 — Metadata & OSINT", callback_data="method_select:3")],
    ])


def _m2_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 FaceCheck.ID (free)", callback_data="m2:facecheck")],
        [InlineKeyboardButton("🌐 Search4Faces (free)", callback_data="m2:search4faces")],
        [InlineKeyboardButton("💎 PimEyes (paid key)", callback_data="m2:pimeyes")],
        [InlineKeyboardButton("◀ Back", callback_data="back:methods")],
    ])


def _m3_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📸 Show EXIF", callback_data="m3:exif")],
        [InlineKeyboardButton("🔍 Google Lens", callback_data="m3:lens")],
        [InlineKeyboardButton("🧩 Crop into regions", callback_data="m3:crop")],
        [InlineKeyboardButton("🔎 Enhance text", callback_data="m3:enhance")],
        [InlineKeyboardButton("🌐 External engines", callback_data="m3:engines")],
        [InlineKeyboardButton("◀ Back", callback_data="back:methods")],
    ])


def _back_to_m3() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀ Back to Method 3", callback_data="method_select:3")],
    ])


def _back_to_m2() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀ Back to Method 2", callback_data="method_select:2")],
        [InlineKeyboardButton("🏠 Method menu", callback_data="back:methods")],
    ])


# --------------------------------------------------------------------------- #
#  Main callback dispatcher
# --------------------------------------------------------------------------- #

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if "image_bytes" not in context.user_data:
        await query.edit_message_text("⚠️ Session expired. Send the image again.")
        return

    data = query.data

    if data.startswith("method_select:"):
        which = data.split(":")[1]
        if which == "2":
            await query.edit_message_text(
                "🔍 <b>Method 2 — Face Search</b>\n\n"
                "Searches for faces across social platforms, news sites, "
                "and public databases.\n\n"
                "<b>FaceCheck.ID</b> — broad coverage, free\n"
                "<b>Search4Faces</b> — VK, OK, TikTok, Clubhouse, free\n"
                "<b>PimEyes</b> — web-wide tracking, paid API key required\n\n"
                "<i>Face searches take 30–90 seconds. Results are ranked "
                "by confidence — verify manually.</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=_m2_keyboard(),
                disable_web_page_preview=True,
            )
        elif which == "3":
            await query.edit_message_text(
                "📸 <b>Method 3 — Metadata & OSINT</b>\n\n"
                "Extracts EXIF, runs reverse image search, and helps you "
                "inspect details.\n\n"
                "Pick a tool below.",
                parse_mode=ParseMode.HTML,
                reply_markup=_m3_keyboard(),
                disable_web_page_preview=True,
            )
        return

    if data == "back:methods":
        await query.edit_message_text(
            "<b>Pick an analysis method:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=_method_keyboard(),
        )
        return

    if data.startswith("m2:"):
        await _handle_method2(query, context, data.split(":")[1])
        return

    if data.startswith("m3:"):
        await _handle_method3(query, context, data.split(":")[1])
        return


# --------------------------------------------------------------------------- #
#  Method 2
# --------------------------------------------------------------------------- #

async def _handle_method2(query, context: ContextTypes.DEFAULT_TYPE, engine: str):
    data = context.user_data["image_bytes"]

    last = context.user_data.get("last_face_search", 0)
    now = time.time()
    if now - last < FACE_SEARCH_COOLDOWN:
        wait = int(FACE_SEARCH_COOLDOWN - (now - last))
        await query.answer(f"Wait {wait}s before another face search.", show_alert=True)
        return
    context.user_data["last_face_search"] = now

    if engine == "facecheck":
        await query.edit_message_text(
            "🌐 <b>FaceCheck.ID</b>\n\nSearching… this takes 30–90 seconds.",
            parse_mode=ParseMode.HTML,
        )
        result = await facecheck_search(data)
        await _send_face_result(query, result)

    elif engine == "search4faces":
        await query.edit_message_text(
            "🌐 <b>Search4Faces</b>\n\nSearching VK, OK, TikTok, Clubhouse…",
            parse_mode=ParseMode.HTML,
        )
        result = await search4faces_search(data)
        await _send_face_result(query, result)

    elif engine == "pimeyes":
        await query.edit_message_text(
            "💎 <b>PimEyes</b>\n\nSearching…",
            parse_mode=ParseMode.HTML,
        )
        result = await pimeyes_search(data)
        await _send_face_result(query, result)


async def _send_face_result(query, result: dict):
    report = format_face_results(result)
    await query.edit_message_text(
        report,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=_back_to_m2(),
    )

    # Send thumbnails from FaceCheck.ID as photos
    for m in result.get("matches", [])[:5]:
        b64 = m.get("thumbnail_b64")
        if not b64:
            continue
        try:
            raw = base64.b64decode(b64)
            score = m.get("score", 0)
            pct = int(score * 100) if score <= 1.0 else int(score)
            await query.message.reply_photo(
                photo=io.BytesIO(raw),
                caption=f"Match · {pct}% confidence",
            )
        except Exception:
            continue


# --------------------------------------------------------------------------- #
#  Method 3
# --------------------------------------------------------------------------- #

async def _handle_method3(query, context: ContextTypes.DEFAULT_TYPE, tool: str):
    data = context.user_data["image_bytes"]

    if tool == "exif":
        exif = context.user_data.get("exif") or {}
        await query.edit_message_text(
            format_exif_report(exif),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=_back_to_m3(),
        )

    elif tool == "lens":
        await query.edit_message_text("🔍 Running Google Lens…")
        result = await google_lens_search(data)
        report = format_lens_results(result)
        await query.edit_message_text(
            report,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=_back_to_m3(),
        )

    elif tool == "crop":
        regions = crop_regions(data, grid=2)
        await query.edit_message_text(
            "🧩 Sending 4 cropped regions. Use these to zoom into background "
            "details, text, tattoos, or landmarks.",
            reply_markup=_back_to_m3(),
        )
        for label, region_bytes in regions:
            await query.message.reply_photo(
                photo=io.BytesIO(region_bytes),
                caption=f"Region: {label}",
            )

    elif tool == "enhance":
        enhanced = enhance_for_text(data)
        await query.message.reply_photo(
            photo=io.BytesIO(enhanced),
            caption="🔎 Enhanced for text — grayscale, sharpened, high contrast.",
        )
        await query.edit_message_text(
            "Enhanced version sent above.",
            reply_markup=_back_to_m3(),
        )

    elif tool == "engines":
        await query.edit_message_text(
            "🌐 <b>External reverse search engines</b>\n\n"
            "These need a public URL for the image.\n\n"
            "<b>Steps:</b>\n"
            "1. Upload the image to <code>0x0.st</code> or <code>imgur.com</code>\n"
            "2. Copy the direct image link\n"
            "3. Send the link to this bot\n\n"
            "The bot will generate one-tap links for Google, Yandex, Bing, "
            "and TinEye.",
            parse_mode=ParseMode.HTML,
            reply_markup=_back_to_m3(),
)
