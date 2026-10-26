"""
Entry point: receives an image, runs quick EXIF, presents method menu.
"""
from __future__ import annotations

import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from services.exif_service import extract_exif
from config import MAX_FILE_MB

logger = logging.getLogger(__name__)


def _method_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Method 2 — Face Search", callback_data="method_select:2")],
        [InlineKeyboardButton("📸 Method 3 — Metadata & OSINT", callback_data="method_select:3")],
    ])


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    if msg.photo:
        file_obj = msg.photo[-1]
        filename = "photo.jpg"
        sent_as_document = False
    elif msg.document:
        doc = msg.document
        if not doc.mime_type or not doc.mime_type.startswith("image/"):
            await msg.reply_text("❌ Please send an image file (JPEG, PNG, WebP).")
            return
        file_obj = doc
        filename = doc.file_name or "document.jpg"
        sent_as_document = True
    else:
        return

    if file_obj.file_size and file_obj.file_size > MAX_FILE_MB * 1024 * 1024:
        await msg.reply_text(f"❌ File is larger than {MAX_FILE_MB} MB.")
        return

    status = await msg.reply_text("📥 Downloading image…")

    try:
        tg_file = await context.bot.get_file(file_obj.file_id)
        data = bytes(await tg_file.download_as_bytearray())
    except Exception as e:
        await status.edit_text(f"❌ Download failed: {e}")
        return

    exif = extract_exif(data)

    context.user_data["image_bytes"] = data
    context.user_data["image_filename"] = filename
    context.user_data["exif"] = exif
    context.user_data["sent_as_document"] = sent_as_document

    header_lines = ["<b>🖼️ Image received</b>", "━━━━━━━━━━━━━━━━━━"]

    b = exif.get("basic", {})
    if b:
        header_lines.append(f"Format: <code>{b.get('format')} · {b.get('size')}</code>")

    if exif.get("has_exif"):
        header_lines.append("EXIF: ✅ present")
        if exif["gps"]:
            header_lines.append(
                f"GPS: ✅ <a href='{exif['gps']['maps_url']}'>view on map</a>"
            )
    else:
        if sent_as_document:
            header_lines.append("EXIF: ❌ not present (image was stripped before upload)")
        else:
            header_lines.append(
                "EXIF: ❌ stripped by Telegram — resend as <b>Document</b> to preserve"
            )

    header_lines.append("")
    header_lines.append("<b>Pick an analysis method:</b>")
    header_lines.append("")
    header_lines.append("<b>Method 2</b> — find faces across social platforms")
    header_lines.append("<b>Method 3</b> — extract metadata, reverse search, inspect clues")

    await status.edit_text(
        "\n".join(header_lines),
        parse_mode=ParseMode.HTML,
        reply_markup=_method_keyboard(),
        disable_web_page_preview=True,
      )
