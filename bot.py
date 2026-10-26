"""
OSINT Image Bot — Methods 2 + 3.
Method 2: face recognition search (FaceCheck.ID, Search4Faces, PimEyes).
Method 3: EXIF, reverse image search, contextual analysis.
"""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import BOT_TOKEN
from handlers.image_handler import handle_image
from handlers.search_handler import handle_callback
from handlers.exif_handler import cmd_exif

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("osint-bot")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕵️ <b>OSINT Image Bot</b>\n\n"
        "Send me an image and pick a method:\n\n"
        "<b>🔍 Method 2 — Face Search</b>\n"
        "• FaceCheck.ID — social platforms, free\n"
        "• Search4Faces — VK, TikTok, Clubhouse, free\n"
        "• PimEyes — web-wide tracking (paid key required)\n\n"
        "<b>📸 Method 3 — Metadata & OSINT</b>\n"
        "• EXIF (camera, GPS, timestamps)\n"
        "• Google Lens reverse search\n"
        "• Region cropping for background clues\n"
        "• Text enhancement for OCR\n"
        "• External engine links\n\n"
        "<b>Tip:</b> Send as <b>Document</b> to preserve EXIF.\n\n"
        "/help for details",
        parse_mode="HTML",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>How to use</b>\n\n"
        "1. Send a photo or image file\n"
        "2. Pick Method 2 or Method 3\n"
        "3. Choose a specific engine or tool\n"
        "4. Read the results\n\n"
        "<b>Method 2 (Face Search)</b>\n"
        "• FaceCheck.ID — free, social platforms\n"
        "• Search4Faces — free, VK/TikTok/OK\n"
        "• PimEyes — paid, requires API key\n\n"
        "<b>Method 3 (Metadata & OSINT)</b>\n"
        "• EXIF — camera, GPS, timestamps\n"
        "• Lens — reverse image search\n"
        "• Crop — split into 4 regions\n"
        "• Enhance — grayscale + sharpen\n"
        "• Engines — Yandex, Bing, TinEye links\n\n"
        "<i>Face results are ranked by confidence — verify manually. "
        "Never identify someone from a single match.</i>",
        parse_mode="HTML",
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("exif", cmd_exif))

    app.add_handler(
        MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image)
    )
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("OSINT Image Bot starting…")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
