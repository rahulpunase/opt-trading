import logging
import os
from typing import Optional

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

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


async def _actions(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "<b>📋 Available Actions</b>\n\n"
        "<b>Platform</b>\n"
        "/ping — Check if the bot is alive\n"
        "/status — Check if the platform is running\n"
        "/test — Send a test alert\n\n"
        "<b>Strategies</b>\n"
        "/running — Show currently running strategies with trade counts\n"
        "/strategies — List all strategies with Start / Pause / Stop controls\n"
        "/killswitch — Emergency stop all running strategies\n\n"
        "<b>Help</b>\n"
        "/actions — Show this menu"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def _running(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            running: list[dict] = (await client.get("http://trader:8000/strategies")).json()
    except Exception as e:
        await update.message.reply_text(f"❌ Could not fetch running strategies: {e}")
        return

    if not running:
        await update.message.reply_text("No strategies are currently running.")
        return

    lines = ["<b>🟢 Running Strategies</b>\n"]
    for s in running:
        tag_paper = "[paper]" if s.get("paper_trade") else "[live]"
        lines.append(f"● <b>{s['name']}</b>  {tag_paper}")
        lines.append(f"  Trades today: {s.get('trades_today', 0)}  |  Open positions: {s.get('open_positions', 0)}\n")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def _strategies(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            running_resp = await client.get("http://trader:8000/strategies")
            available_resp = await client.get("http://trader:8000/strategies/available")
        running: list[dict] = running_resp.json()
        available: list[dict] = available_resp.json()
    except Exception as e:
        await update.message.reply_text(f"❌ Could not fetch strategies: {e}")
        return

    running_names = {s["name"] for s in running}

    if not available:
        await update.message.reply_text("No strategies found.")
        return

    lines: list[str] = ["<b>📊 Strategies</b>\n"]
    keyboard: list[list[InlineKeyboardButton]] = []

    for s in available:
        name = s["name"]
        tag_paper = "[paper]" if s.get("paper_trade") else "[live]"
        tag_enabled = "" if s.get("enabled", True) else "[disabled]"
        status = "🟢 running" if name in running_names else "⚪ stopped"
        lines.append(f"● <b>{name}</b>  {tag_paper} {tag_enabled}  {s.get('timeframe', '')}")
        lines.append(f"  Status: {status}\n")
        keyboard.append([
            InlineKeyboardButton("▶ Start", callback_data=f"start:{name}"),
            InlineKeyboardButton("⏸ Pause", callback_data=f"pause:{name}"),
            InlineKeyboardButton("⏹ Stop",  callback_data=f"stop:{name}"),
        ])

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def _killswitch(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            running: list[dict] = (await client.get("http://trader:8000/strategies")).json()
    except Exception as e:
        await update.message.reply_text(f"❌ Could not fetch strategies: {e}")
        return

    if not running:
        await update.message.reply_text("No strategies are currently running.")
        return

    names = [s["name"] for s in running]
    names_text = "\n".join(f"• {n}" for n in names)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Confirm — stop all", callback_data="killswitch:confirm"),
        InlineKeyboardButton("❌ Cancel", callback_data="killswitch:cancel"),
    ]])
    await update.message.reply_text(
        f"⚠️ <b>Kill switch</b>\n\nThis will stop <b>{len(names)}</b> running strateg{'y' if len(names) == 1 else 'ies'}:\n\n{names_text}\n\nAre you sure?",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def _killswitch_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, action = query.data.split(":", 1)

    if action == "cancel":
        await query.edit_message_text("Kill switch cancelled.")
        return

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            running: list[dict] = (await client.get("http://trader:8000/strategies")).json()
    except Exception as e:
        await query.edit_message_text(f"❌ Could not fetch strategies: {e}")
        return

    if not running:
        await query.edit_message_text("No strategies are currently running.")
        return

    results: list[str] = []
    async with httpx.AsyncClient(timeout=5) as client:
        for s in running:
            name = s["name"]
            try:
                resp = await client.post("http://trader:8000/strategy/stop", json={"name": name})
                results.append(f"✅ {name}" if resp.status_code == 200 else f"❌ {name}: {resp.json().get('detail', resp.text)}")
            except Exception as e:
                results.append(f"❌ {name}: {e}")

    await query.edit_message_text(
        "<b>🛑 Kill switch executed</b>\n\n" + "\n".join(results),
        parse_mode="HTML",
    )


async def _strategy_action(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    action, name = query.data.split(":", 1)
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                f"http://trader:8000/strategy/{action}",
                json={"name": name},
            )
        if resp.status_code == 200:
            await query.edit_message_text(f"✅ <b>{name}</b> → {action}ed", parse_mode="HTML")
        else:
            detail = resp.json().get("detail", resp.text)
            await query.edit_message_text(
                f"❌ {action} <b>{name}</b> failed: {detail}", parse_mode="HTML"
            )
    except Exception as e:
        await query.edit_message_text(f"❌ {action} {name} error: {e}")


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
    _app.add_handler(CommandHandler("actions", _actions))
    _app.add_handler(CommandHandler("running", _running))
    _app.add_handler(CommandHandler("strategies", _strategies))
    _app.add_handler(CommandHandler("killswitch", _killswitch))
    _app.add_handler(CallbackQueryHandler(_strategy_action, pattern=r"^(start|stop|pause):.+"))
    _app.add_handler(CallbackQueryHandler(_killswitch_confirm, pattern=r"^killswitch:.+"))
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
