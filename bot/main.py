import asyncio
import logging
import os
import time
from collections import defaultdict
from datetime import date
from urllib.parse import urlparse

from dotenv import load_dotenv
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    LinkPreviewOptions,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

load_dotenv()
logging.basicConfig(level=logging.INFO)

from app.agent import run_milonga_agent
from bot.messages import get_lang, t
from bot.limits import check_and_increment, get_status, get_search_stats, FREE_DAILY_LIMIT

DONATE_TIERS = [50, 250, 500]
ADMIN_ID = 847615855


def _lang(context: ContextTypes.DEFAULT_TYPE, user) -> str:
    return context.user_data.get("lang") or get_lang(getattr(user, "language_code", None))


def _main_menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, "btn_find"), callback_data="find")],
        [InlineKeyboardButton(t(lang, "btn_donate"), callback_data="donate")],
    ])


def _back_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, "back"), callback_data="back")]
    ])


def _donate_kb(lang: str) -> InlineKeyboardMarkup:
    rows = []
    for stars in DONATE_TIERS:
        label = t(lang, f"donate_{stars}")
        rows.append([InlineKeyboardButton(label, callback_data=f"stars_{stars}")])
    rows.append([InlineKeyboardButton(t(lang, "donate_custom"), callback_data="custom_stars")])
    rows.append([InlineKeyboardButton(t(lang, "close"), callback_data="close_donate")])
    return InlineKeyboardMarkup(rows)


def _sources_line(sources_checked: list[str]) -> str:
    domains: list[str] = []
    for url in sources_checked:
        try:
            d = urlparse(url).netloc.removeprefix("www.")
            if d and d not in domains:
                domains.append(d)
        except Exception:
            pass
    if not domains:
        return ""
    return "\n\n<i>🔍 " + " • ".join(domains[:8]) + "</i>"


def _format_events(events, city: str, sources_checked: list[str]) -> str:
    by_date: dict[str, list] = defaultdict(list)
    for ev in events:
        by_date[ev.date or ""].append(ev)

    today_str = str(date.today())
    text = f"💃 <b>{city}</b>\n"

    for d in sorted(by_date.keys()):
        evs = by_date[d]
        try:
            parsed = date.fromisoformat(d)
            is_today = d == today_str
            day_label = "Today" if is_today else parsed.strftime("%A")
            day_str = parsed.strftime(f"{day_label}, %B {parsed.day}")
        except ValueError:
            day_str = d
        text += f"\n📅 <b>{day_str}</b>\n"
        for i, ev in enumerate(evs, 1):
            lines = [f"\n<b>{i}. {ev.name}</b>"]
            if ev.time:
                lines.append(f"🕐 {ev.time}")
            if ev.venue:
                lines.append(f"📍 {ev.venue}")
            if ev.address:
                lines.append(f"📌 {ev.address}")
            if ev.price:
                lines.append(f"💰 {ev.price}")
            if ev.dj:
                lines.append(f"🎵 DJ: {ev.dj}")
            if ev.source_url:
                lines.append(f'🔗 <a href="{ev.source_url}">Source</a>')
            text += "\n".join(lines) + "\n"

    text += _sources_line(sources_checked)
    return text.strip()


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(getattr(update.effective_user, "language_code", None))
    context.user_data["lang"] = lang
    logging.info("start user=%d lang=%s", update.effective_user.id, lang)
    await update.message.reply_text(
        t(lang, "welcome"),
        parse_mode="HTML",
        reply_markup=_main_menu_kb(lang),
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(context, update.effective_user)
    status = await get_status(update.effective_user.id)
    text = t(lang, "status_free").format(
        remaining=status["remaining"], limit=FREE_DAILY_LIMIT
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=_main_menu_kb(lang))


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    stats = await get_search_stats()
    await update.message.reply_text(
        f"📊 <b>Stats</b>\n\n"
        f"Total users: <b>{stats['total_users']}</b>\n"
        f"Active today: <b>{stats['active_today']}</b>\n"
        f"Searches today: <b>{stats['searches_today']}</b>",
        parse_mode="HTML",
    )


async def cb_find(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    lang = _lang(context, update.effective_user)
    await update.effective_chat.send_message(
        t(lang, "ask_city"),
        parse_mode="HTML",
        reply_markup=_back_kb(lang),
    )


async def cb_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await update.callback_query.message.delete()


async def cb_donate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    lang = _lang(context, update.effective_user)
    # Send as NEW message so previous results are not lost
    await update.effective_chat.send_message(
        t(lang, "donate_text"),
        parse_mode="HTML",
        reply_markup=_donate_kb(lang),
    )


async def cb_close_donate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await update.callback_query.message.delete()


async def cb_stars(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    lang = _lang(context, update.effective_user)
    stars = int(update.callback_query.data.split("_")[1])
    await update.callback_query.message.reply_invoice(
        title=t(lang, "donate_title"),
        description=t(lang, "donate_desc_tip"),
        payload=f"donate_{stars}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(t(lang, "donate_title"), stars)],
    )


async def cb_custom_stars(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    lang = _lang(context, update.effective_user)
    context.user_data["awaiting_stars"] = True
    await update.effective_chat.send_message(
        t(lang, "ask_stars_amount"),
        parse_mode="HTML",
    )


async def handle_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(context, update.effective_user)
    text = update.message.text.strip()

    # Handle custom Stars amount input
    if context.user_data.get("awaiting_stars"):
        context.user_data.pop("awaiting_stars")
        try:
            stars = int(text)
            if stars < 50:
                raise ValueError
        except ValueError:
            await update.message.reply_text(t(lang, "invalid_stars"), parse_mode="HTML")
            return
        await update.message.reply_invoice(
            title=t(lang, "donate_title"),
            description=t(lang, "donate_desc_tip"),
            payload=f"donate_{stars}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(t(lang, "donate_title"), stars)],
        )
        return

    city = text

    if context.user_data.get("searching"):
        return

    user_id = update.effective_user.id
    allowed, remaining = await check_and_increment(user_id)
    if not allowed:
        logging.info("rate_limit user=%d city=%r", user_id, city)
        await update.message.reply_text(
            t(lang, "rate_limit").format(limit=FREE_DAILY_LIMIT),
            parse_mode="HTML",
            reply_markup=_donate_kb(lang),
        )
        return

    logging.info("search_start user=%d city=%r lang=%s", user_id, city, lang)
    t0 = time.monotonic()

    context.user_data["searching"] = True
    status = await update.message.reply_text(
        t(lang, "searching").format(city=city),
        parse_mode="HTML",
    )

    try:
        result = await asyncio.wait_for(
            run_milonga_agent(city=city.title(), date=str(date.today())),
            timeout=270,
        )
    except asyncio.TimeoutError:
        logging.warning("search_timeout user=%d city=%r elapsed=%.0fs", user_id, city, time.monotonic() - t0)
        await status.edit_text(t(lang, "error"), parse_mode="HTML")
        context.user_data["searching"] = False
        return
    except Exception:
        logging.exception("search_error user=%d city=%r elapsed=%.0fs", user_id, city, time.monotonic() - t0)
        await status.edit_text(t(lang, "error"), parse_mode="HTML")
        context.user_data["searching"] = False
        return

    elapsed = time.monotonic() - t0
    context.user_data["searching"] = False

    if not result.city_found:
        logging.info("search_done user=%d city=%r result=not_found elapsed=%.0fs", user_id, city, elapsed)
        text = t(lang, "city_not_found").format(city=city)
    elif result.events:
        logging.info("search_done user=%d city=%r result=ok events=%d elapsed=%.0fs",
                     user_id, result.city, len(result.events), elapsed)
        text = _format_events(result.events, result.city, result.sources_checked)
    else:
        logging.info("search_done user=%d city=%r result=no_events elapsed=%.0fs", user_id, result.city, elapsed)
        text = t(lang, "no_events").format(city=result.city)
        text += _sources_line(result.sources_checked)

    # Hint about remaining searches when running low (free users only)
    if 0 < remaining <= 2:
        text += t(lang, "searches_left").format(remaining=remaining)

    text += "\n\n" + t(lang, "disclaimer")

    await status.delete()
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=_main_menu_kb(lang),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


async def pre_checkout(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(context, update.effective_user)
    stars = update.message.successful_payment.total_amount
    logging.info("donation user=%d stars=%d", update.effective_user.id, stars)
    await update.message.reply_text(
        t(lang, "donate_thanks"), parse_mode="HTML", reply_markup=_main_menu_kb(lang)
    )


def main() -> None:
    app = Application.builder().token(os.environ["TELEGRAM_BOT_TOKEN"]).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CallbackQueryHandler(cb_find, pattern="^find$"))
    app.add_handler(CallbackQueryHandler(cb_back, pattern="^back$"))
    app.add_handler(CallbackQueryHandler(cb_donate, pattern="^donate$"))
    app.add_handler(CallbackQueryHandler(cb_close_donate, pattern="^close_donate$"))
    app.add_handler(CallbackQueryHandler(cb_stars, pattern=r"^stars_\d+$"))
    app.add_handler(CallbackQueryHandler(cb_custom_stars, pattern="^custom_stars$"))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_city))

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
