import asyncio
import html
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
    KeyboardButton,
    LabeledPrice,
    LinkPreviewOptions,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
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
from app.redis_client import get_redis as _get_redis
from bot.messages import get_lang, t
from bot.limits import (
    check_and_increment,
    get_status,
    get_search_stats,
    grant_premium,
    FREE_DAILY_LIMIT,
    PAID_SEARCH_STARS,
    PAID_SEARCH_DAYS,
)
from bot.partner import (
    add_notify,
    get_partner,
    get_partners,
    get_partners_by_ids,
    normalize_partner_city,
    pop_notify_users,
    remove_partner,
    reverse_geocode,
    save_partner,
)

DONATE_TIERS = [50, 250, 500]
ADMIN_ID = 847615855


def _lang(context: ContextTypes.DEFAULT_TYPE, user) -> str:
    return context.user_data.get("lang") or get_lang(getattr(user, "language_code", None))


def _main_menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, "btn_find"), callback_data="find")],
        [InlineKeyboardButton(t(lang, "btn_partner"), callback_data="partner_start")],
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


def _paywall_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            t(lang, "paywall_button").format(stars=PAID_SEARCH_STARS),
            callback_data="buy_search_pass",
        )
    ]])


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
    s = await get_search_stats()

    ok, empty, nf = s["result_ok"], s["result_empty"], s["result_notfound"]
    total_outcomes = ok + empty + nf
    quality = f"{ok * 100 // total_outcomes}%" if total_outcomes else "n/a"

    cities_lines = "\n".join(
        f"  {city} — {score}" for city, score in s["top_cities"]
    ) or "  —"

    await update.message.reply_text(
        f"📊 <b>Stats</b>\n\n"
        f"👤 <b>Users</b>\n"
        f"  Total: {s['total_users']}  |  New today: {s['new_users_today']}  |  Active today: {s['active_today']}\n\n"
        f"🔍 <b>Searches</b>\n"
        f"  Today: {s['searches_today']}  |  All time: {s['searches_total']}\n\n"
        f"✅ <b>Quality</b>  {quality}\n"
        f"  ok: {ok}  |  no events: {empty}  |  not found: {nf}\n\n"
        f"🤝 <b>Partner requests</b>\n"
        f"  Today: {s['partner_requests_today']}  |  All time: {s['partner_requests_total']}\n\n"
        f"⭐ <b>Donations</b>\n"
        f"  Today: {s['donations_stars_today']}  |  All time: {s['donations_stars_total']}\n\n"
        f"🔝 <b>Top cities</b>\n{cities_lines}",
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
    lang = _lang(context, update.effective_user)
    try:
        await update.callback_query.message.edit_text(
            t(lang, "welcome"),
            parse_mode="HTML",
            reply_markup=_main_menu_kb(lang),
        )
    except Exception:
        pass


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
    try:
        await update.callback_query.message.delete()
    except Exception:
        pass


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


async def cb_buy_search_pass(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    lang = _lang(context, update.effective_user)
    await update.callback_query.message.reply_invoice(
        title=t(lang, "paywall_invoice_title"),
        description=t(lang, "paywall_invoice_desc"),
        payload="searchpass",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(t(lang, "paywall_invoice_title"), PAID_SEARCH_STARS)],
    )


async def cb_custom_stars(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    lang = _lang(context, update.effective_user)
    context.user_data["awaiting_stars"] = True
    await update.effective_chat.send_message(
        t(lang, "ask_stars_amount"),
        parse_mode="HTML",
    )


# ── Partner finder helpers ──────────────────────────────────────────────────

def _partner_role_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t(lang, "partner_role_leader"), callback_data="partner_role_leader"),
            InlineKeyboardButton(t(lang, "partner_role_follower"), callback_data="partner_role_follower"),
        ],
        [InlineKeyboardButton(t(lang, "partner_role_both"), callback_data="partner_role_both")],
    ])


def _partner_city_kb(lang: str, last_city: str | None) -> InlineKeyboardMarkup:
    rows = []
    if last_city:
        rows.append([InlineKeyboardButton(
            t(lang, "partner_city_use_last").format(city=last_city),
            callback_data="partner_city_last",
        )])
    rows.append([
        InlineKeyboardButton(t(lang, "partner_city_type"), callback_data="partner_city_type"),
        InlineKeyboardButton(t(lang, "partner_share_location"), callback_data="partner_city_geo"),
    ])
    return InlineKeyboardMarkup(rows)


def _partner_note_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, "partner_note_skip"), callback_data="partner_note_skip")]
    ])


def _partner_list_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(t(lang, "partner_remove_btn"), callback_data="partner_remove"),
        InlineKeyboardButton(t(lang, "partner_refresh_btn"), callback_data="partner_refresh"),
    ]])


def _format_partner_card(p: dict, lang: str) -> str:
    role_label = t(lang, f"partner_role_label_{p['role']}")
    name = f"@{p['username']}" if p.get("username") else "—"
    line = f"👤 {name} — {role_label}"
    if p.get("note"):
        line += f"\n   <i>{html.escape(p['note'])}</i>"
    return line


def _format_partner_list(partners: list[dict], city: str, lang: str) -> str:
    header = t(lang, "partner_list_header").format(city=city)
    cards = "\n\n".join(_format_partner_card(p, lang) for p in partners)
    return header + "\n" + cards


async def _show_partner_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    city: str,
    lang: str,
    *,
    edit: bool = False,
) -> None:
    user_id = update.effective_user.id
    partners = await get_partners(city, exclude_user_id=user_id)
    kb = _partner_list_kb(lang)
    if partners:
        text = _format_partner_list(partners, city, lang)
    else:
        text = t(lang, "partner_list_empty").format(city=city)
        await add_notify(user_id, city)

    if edit and update.callback_query:
        await update.callback_query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await update.effective_chat.send_message(text, parse_mode="HTML", reply_markup=kb)


async def _partner_nudge_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    data = context.job.data
    user_id, city, lang = data["user_id"], data["city"], data["lang"]
    if not await get_partner(user_id):
        return
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(t(lang, "partner_nudge_yes"), callback_data="partner_nudge_yes"),
        InlineKeyboardButton(t(lang, "partner_nudge_no"), callback_data="partner_nudge_no"),
    ]])
    await context.bot.send_message(
        chat_id=user_id,
        text=t(lang, "partner_nudge_msg").format(city=city),
        parse_mode="HTML",
        reply_markup=kb,
    )


async def _finish_partner_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    city: str,
    note: str,
) -> None:
    lang = _lang(context, update.effective_user)
    user = update.effective_user
    user_id = user.id
    role = context.user_data.pop("partner_role", "both")
    context.user_data.pop("partner_city", None)
    context.user_data.pop("partner_step", None)
    context.user_data.pop("partner_awaiting_location", None)

    username = user.username
    await save_partner(user_id, city, role, note, username, lang=lang)

    try:
        _r = _get_redis()
        if _r:
            _today = str(date.today())
            await _r.hincrby(f"stats:day:{_today}", "partner_requests", 1)
            await _r.hincrby("stats:totals", "partner_requests", 1)
    except Exception:
        pass

    # Notify users who were waiting — batch-fetch to avoid N sequential Redis GETs
    to_notify = await pop_notify_users(city, exclude_user_id=user_id)
    if to_notify:
        notify_data = await get_partners_by_ids(to_notify)
        for uid in to_notify:
            try:
                recipient_data = notify_data.get(uid)
                if not recipient_data:
                    continue  # request expired or manually removed — skip
                recipient_lang = recipient_data.get("lang", "en")
                await context.bot.send_message(
                    chat_id=uid,
                    text=t(recipient_lang, "partner_notify_msg").format(city=city),
                    parse_mode="HTML",
                )
            except Exception:
                pass

    # Warn if no username
    if not username:
        await update.effective_chat.send_message(
            t(lang, "partner_no_username"), parse_mode="HTML"
        )

    # Schedule nudge in 3 hours — cancel any pending nudge from a previous request
    nudge_name = f"partner_nudge_{user_id}"
    jq = context.application.job_queue
    if jq:
        for job in jq.get_jobs_by_name(nudge_name):
            job.schedule_removal()
        jq.run_once(
            _partner_nudge_job,
            when=3 * 3600,
            data={"user_id": user_id, "city": city, "lang": lang},
            name=nudge_name,
        )

    logging.info("partner_save user=%d city=%r role=%s", user_id, city, role)
    await _show_partner_list(update, context, city, lang)


# ── Partner callbacks ────────────────────────────────────────────────────────

async def cb_partner_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    lang = _lang(context, update.effective_user)
    user_id = update.effective_user.id

    existing = await get_partner(user_id)
    if existing:
        role_label = t(lang, f"partner_role_label_{existing['role']}")
        await update.effective_chat.send_message(
            t(lang, "partner_already").format(city=existing["city"], role=role_label),
            parse_mode="HTML",
            reply_markup=_partner_list_kb(lang),
        )
        return

    await update.effective_chat.send_message(
        t(lang, "partner_ask_role"),
        parse_mode="HTML",
        reply_markup=_partner_role_kb(lang),
    )


async def cb_partner_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    lang = _lang(context, update.effective_user)
    role = update.callback_query.data.split("_")[-1]  # leader / follower / both
    context.user_data["partner_role"] = role
    if context.user_data.get("partner_city"):
        # City already set (e.g. from location share after restart) — skip city step
        context.user_data["partner_step"] = "note"
        await update.callback_query.message.edit_text(
            t(lang, "partner_ask_note"),
            parse_mode="HTML",
            reply_markup=_partner_note_kb(lang),
        )
    else:
        last_city = context.user_data.get("last_city")
        await update.callback_query.message.edit_text(
            t(lang, "partner_ask_city"),
            parse_mode="HTML",
            reply_markup=_partner_city_kb(lang, last_city),
        )


async def cb_partner_city_last(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    lang = _lang(context, update.effective_user)
    city = context.user_data.get("last_city") or ""
    if not city:
        # last_city lost after bot restart — fall through to manual entry
        context.user_data["partner_step"] = "city"
        await update.callback_query.message.edit_text(
            t(lang, "partner_ask_city"),
            parse_mode="HTML",
        )
        return
    context.user_data["partner_city"] = city
    context.user_data["partner_step"] = "note"
    await update.callback_query.message.edit_text(
        t(lang, "partner_ask_note"),
        parse_mode="HTML",
        reply_markup=_partner_note_kb(lang),
    )


async def cb_partner_city_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    lang = _lang(context, update.effective_user)
    context.user_data["partner_step"] = "city"
    await update.callback_query.message.edit_text(
        t(lang, "partner_ask_city"),
        parse_mode="HTML",
    )


async def cb_partner_city_geo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    lang = _lang(context, update.effective_user)
    context.user_data["partner_awaiting_location"] = True
    # Text fallback: if user types instead of sharing location, handle_city catches it
    context.user_data["partner_step"] = "city"
    kb = ReplyKeyboardMarkup(
        [[KeyboardButton(t(lang, "partner_share_location"), request_location=True)]],
        one_time_keyboard=True,
        resize_keyboard=True,
    )
    await update.effective_chat.send_message(
        t(lang, "partner_ask_city"),
        parse_mode="HTML",
        reply_markup=kb,
    )


async def cb_partner_note_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    lang = _lang(context, update.effective_user)
    city = context.user_data.get("partner_city", "")
    if not city:
        await update.effective_chat.send_message(t(lang, "error"), parse_mode="HTML")
        return
    await _finish_partner_request(update, context, city, note="")


async def cb_partner_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    lang = _lang(context, update.effective_user)
    await remove_partner(update.effective_user.id)
    await update.callback_query.message.edit_text(
        t(lang, "partner_removed"),
        parse_mode="HTML",
        reply_markup=_main_menu_kb(lang),
    )


async def cb_partner_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    lang = _lang(context, update.effective_user)
    existing = await get_partner(update.effective_user.id)
    if not existing:
        await update.callback_query.message.edit_text(
            t(lang, "partner_removed"), parse_mode="HTML", reply_markup=_main_menu_kb(lang)
        )
        return
    await _show_partner_list(update, context, existing["city"], lang, edit=True)


async def cb_partner_nudge_yes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    lang = _lang(context, update.effective_user)
    await remove_partner(update.effective_user.id)
    await update.callback_query.message.edit_text(
        t(lang, "partner_removed"), parse_mode="HTML"
    )


async def cb_partner_nudge_no(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    lang = _lang(context, update.effective_user)
    await update.callback_query.message.edit_text(
        t(lang, "partner_nudge_still"), parse_mode="HTML"
    )


async def cmd_partner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(context, update.effective_user)
    user_id = update.effective_user.id

    existing = await get_partner(user_id)
    if existing:
        role_label = t(lang, f"partner_role_label_{existing['role']}")
        await update.message.reply_text(
            t(lang, "partner_already").format(city=existing["city"], role=role_label),
            parse_mode="HTML",
            reply_markup=_partner_list_kb(lang),
        )
        return

    await update.message.reply_text(
        t(lang, "partner_ask_role"),
        parse_mode="HTML",
        reply_markup=_partner_role_kb(lang),
    )


async def handle_partner_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(context, update.effective_user)
    was_awaiting = context.user_data.pop("partner_awaiting_location", False)
    context.user_data.pop("partner_step", None)

    loc = update.message.location
    city_raw = await reverse_geocode(loc.latitude, loc.longitude)
    if not city_raw:
        await update.message.reply_text(
            t(lang, "partner_location_failed"),
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )
        if was_awaiting:
            context.user_data["partner_step"] = "city"
        return
    normalized = await normalize_partner_city(city_raw)
    if normalized is None:
        await update.message.reply_text(
            t(lang, "partner_city_failed"),
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )
        if was_awaiting:
            context.user_data["partner_step"] = "city"
        return
    context.user_data["partner_city"] = normalized
    await update.message.reply_text(f"📍 {normalized}", reply_markup=ReplyKeyboardRemove())
    if context.user_data.get("partner_role"):
        context.user_data["partner_step"] = "note"
        await update.effective_chat.send_message(
            t(lang, "partner_ask_note"),
            parse_mode="HTML",
            reply_markup=_partner_note_kb(lang),
        )
    else:
        # No active flow (post-restart or out-of-order): city pre-filled, ask for role
        await update.effective_chat.send_message(
            t(lang, "partner_ask_role"),
            parse_mode="HTML",
            reply_markup=_partner_role_kb(lang),
        )


async def handle_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(context, update.effective_user)
    text = update.message.text.strip()

    # Partner flow: waiting for city input
    if context.user_data.get("partner_step") == "city":
        normalized = await normalize_partner_city(text)
        if normalized is None:
            await update.message.reply_text(t(lang, "partner_city_failed"), parse_mode="HTML")
            return  # keep partner_step = "city" so user can retry
        context.user_data["partner_city"] = normalized
        context.user_data["partner_step"] = "note"
        await update.message.reply_text(
            t(lang, "partner_ask_note"),
            parse_mode="HTML",
            reply_markup=_partner_note_kb(lang),
        )
        return

    # Partner flow: waiting for note input
    if context.user_data.get("partner_step") == "note":
        context.user_data.pop("partner_step")
        city = context.user_data.get("partner_city", "")
        await _finish_partner_request(update, context, city, note=text[:150])
        return

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
        context.user_data["pending_city"] = city
        await update.message.reply_text(
            t(lang, "rate_limit").format(limit=FREE_DAILY_LIMIT, stars=PAID_SEARCH_STARS),
            parse_mode="HTML",
            reply_markup=_paywall_kb(lang),
        )
        return

    await _run_search(update, context, lang, city, remaining)


async def _run_search(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, city: str, remaining: int
) -> None:
    user_id = update.effective_user.id
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
        outcome = "result_notfound"
    elif result.events:
        logging.info("search_done user=%d city=%r result=ok events=%d elapsed=%.0fs",
                     user_id, result.city, len(result.events), elapsed)
        context.user_data["last_city"] = result.city
        text = _format_events(result.events, result.city, result.sources_checked)
        outcome = "result_ok"
    else:
        logging.info("search_done user=%d city=%r result=no_events elapsed=%.0fs", user_id, result.city, elapsed)
        context.user_data["last_city"] = result.city
        text = t(lang, "no_events").format(city=result.city)
        text += _sources_line(result.sources_checked)
        outcome = "result_empty"

    try:
        _r = _get_redis()
        if _r:
            _today = str(date.today())
            await _r.hincrby(f"stats:day:{_today}", outcome, 1)
            if result.city_found:
                await _r.zincrby("stats:cities", 1, result.city)
    except Exception:
        pass

    # Hint about remaining searches when running low (free users only)
    if 0 < remaining <= 2:
        text += t(lang, "searches_left").format(remaining=remaining)

    text += "\n\n" + t(lang, "disclaimer")

    try:
        await status.delete()
    except Exception:
        pass
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
    payload = update.message.successful_payment.invoice_payload
    stars = update.message.successful_payment.total_amount
    user_id = update.effective_user.id

    if payload == "searchpass":
        logging.info("paid_access user=%d stars=%d", user_id, stars)
        await grant_premium(user_id, days=PAID_SEARCH_DAYS)
        try:
            _r = _get_redis()
            if _r:
                _today = str(date.today())
                await _r.hincrby(f"stats:day:{_today}", "paid_access_stars", stars)
                await _r.hincrby("stats:totals", "paid_access_stars", stars)
        except Exception:
            pass

        city = context.user_data.pop("pending_city", None)
        if city:
            await update.message.reply_text(
                t(lang, "paywall_thanks").format(city=city), parse_mode="HTML"
            )
            await _run_search(update, context, lang, city, -1)
        else:
            await update.message.reply_text(
                t(lang, "paywall_unlocked"), parse_mode="HTML", reply_markup=_main_menu_kb(lang)
            )
        return

    logging.info("donation user=%d stars=%d", user_id, stars)
    try:
        _r = _get_redis()
        if _r:
            _today = str(date.today())
            await _r.hincrby(f"stats:day:{_today}", "donations_stars", stars)
            await _r.hincrby("stats:totals", "donations_stars", stars)
    except Exception:
        pass
    await update.message.reply_text(
        t(lang, "donate_thanks"), parse_mode="HTML", reply_markup=_main_menu_kb(lang)
    )


def main() -> None:
    app = Application.builder().token(os.environ["TELEGRAM_BOT_TOKEN"]).concurrent_updates(True).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("partner", cmd_partner))
    app.add_handler(CallbackQueryHandler(cb_find, pattern="^find$"))
    app.add_handler(CallbackQueryHandler(cb_back, pattern="^back$"))
    app.add_handler(CallbackQueryHandler(cb_donate, pattern="^donate$"))
    app.add_handler(CallbackQueryHandler(cb_close_donate, pattern="^close_donate$"))
    app.add_handler(CallbackQueryHandler(cb_stars, pattern=r"^stars_\d+$"))
    app.add_handler(CallbackQueryHandler(cb_buy_search_pass, pattern="^buy_search_pass$"))
    app.add_handler(CallbackQueryHandler(cb_custom_stars, pattern="^custom_stars$"))
    app.add_handler(CallbackQueryHandler(cb_partner_start, pattern="^partner_start$"))
    app.add_handler(CallbackQueryHandler(cb_partner_role, pattern=r"^partner_role_(leader|follower|both)$"))
    app.add_handler(CallbackQueryHandler(cb_partner_city_last, pattern="^partner_city_last$"))
    app.add_handler(CallbackQueryHandler(cb_partner_city_type, pattern="^partner_city_type$"))
    app.add_handler(CallbackQueryHandler(cb_partner_city_geo, pattern="^partner_city_geo$"))
    app.add_handler(CallbackQueryHandler(cb_partner_note_skip, pattern="^partner_note_skip$"))
    app.add_handler(CallbackQueryHandler(cb_partner_remove, pattern="^partner_remove$"))
    app.add_handler(CallbackQueryHandler(cb_partner_refresh, pattern="^partner_refresh$"))
    app.add_handler(CallbackQueryHandler(cb_partner_nudge_yes, pattern="^partner_nudge_yes$"))
    app.add_handler(CallbackQueryHandler(cb_partner_nudge_no, pattern="^partner_nudge_no$"))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.LOCATION, handle_partner_location))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_city))

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
