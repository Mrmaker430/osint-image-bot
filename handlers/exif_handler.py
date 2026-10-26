"""Standalone /exif command — prompts user to send an image."""
from telegram import Update
from telegram.ext import ContextTypes


async def cmd_exif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 <b>EXIF Extractor</b>\n\n"
        "Send me an image as a <b>Document</b> (paperclip → File) "
        "to preserve its metadata.\n\n"
        "If you send it as a normal photo, Telegram strips the EXIF data "
        "before the bot ever sees it.",
        parse_mode="HTML",
    )
