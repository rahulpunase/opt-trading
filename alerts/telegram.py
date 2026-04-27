import logging
import os
from typing import Optional

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger("telegram")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

_app: Optional[Application] = None


# --- command handlers ---

async def _ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("pong 🏓")


async def _status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("✅ Platform is running")


async def _test(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await send_alert("🔔 Test alert from /test command")
    await update.message.reply_text("Test alert sent!")


# --- lifecycle ---

async def start_bot() -> None:
    global _app
    if not TOKEN:
        logger.warning("Telegram not configured — bot disabled")
        return
    _app = Application.builder().token(TOKEN).build()
    _app.add_handler(CommandHandler("ping", _ping))
    _app.add_handler(CommandHandler("status", _status))
    _app.add_handler(CommandHandler("test", _test))
    await _app.initialize()
    await _app.start()
    await _app.updater.start_polling(drop_pending_updates=True)
    logger.info("Telegram bot started (polling)")


async def stop_bot() -> None:
    global _app
    if _app is None:
        return
    await _app.updater.stop()
    await _app.stop()
    await _app.shutdown()
    _app = None
    logger.info("Telegram bot stopped")


# --- public API (signature unchanged — used by order_router and others) ---

async def send_alert(message: str) -> bool:
    if not TOKEN or not CHAT_ID:
        logger.warning("Telegram not configured, skipping alert: %s", message)
        return False
    try:
        if _app and _app.bot:
            await _app.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="HTML")
        else:
            # Fallback: raw HTTP when bot is not yet started (e.g. early startup alerts)
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    json={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"},
                )
                resp.raise_for_status()
        return True
    except Exception as e:
        logger.error("Telegram alert failed: %s", e)
        return False
