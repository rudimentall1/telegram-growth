import asyncio
import logging
import re

from telegram import Update
from telegram.error import BadRequest, Forbidden, TelegramError
from telegram.ext import (
    ApplicationBuilder,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
from config import CHAT_ID, GROUP_CHAT_ID, TELEGRAM_TOKEN
import growth_db

logging.basicConfig(level=logging.INFO)
# httpx logs full Telegram Bot API request URLs at INFO level; those URLs contain
# the bot token. Never write them to the system journal.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

WELCOME_TEXT = (
    "👋 Добро пожаловать, {name}!\n\n"
    "Здесь обсуждаем новости из канала @cryptoping_ru — airdrop, NFT, тестнеты, ноды.\n"
    "Напиши /help, если хочешь посмотреть частые вопросы."
)

GREETINGS = ["привет", "здарова", "хай", "hello", "hi", "приветствую", "здравствуй"]

AUTO_REPLIES = {
    "airdrop": "🪂 Свежие airdrop смотри в основном канале: @cryptoping_ru",
    "аирдроп": "🪂 Свежие airdrop смотри в основном канале: @cryptoping_ru",
    "эирдроп": "🪂 Свежие airdrop смотри в основном канале: @cryptoping_ru",
    "дроп": "🪂 Свежие airdrop смотри в основном канале: @cryptoping_ru",
    "ретродроп": "🪂 Свежие airdrop смотри в основном канале: @cryptoping_ru",
    "nft": "🖼 Новости по NFT постим в @cryptoping_ru, там же и минты.",
    "нфт": "🖼 Новости по NFT постим в @cryptoping_ru, там же и минты.",
    "минт": "🖼 Новости по NFT постим в @cryptoping_ru, там же и минты.",
    "минтить": "🖼 Новости по NFT постим в @cryptoping_ru, там же и минты.",
    "node": "🖥 Про ноды/тестнеты пишем в @cryptoping_ru, следи за постами с 🖥.",
    "нода": "🖥 Про ноды/тестнеты пишем в @cryptoping_ru, следи за постами с 🖥.",
    "ноду": "🖥 Про ноды/тестнеты пишем в @cryptoping_ru, следи за постами с 🖥.",
    "ноды": "🖥 Про ноды/тестнеты пишем в @cryptoping_ru, следи за постами с 🖥.",
    "тестнет": "🖥 Про ноды/тестнеты пишем в @cryptoping_ru, следи за постами с 🖥.",
    "валидатор": "🖥 Про ноды/тестнеты пишем в @cryptoping_ru, следи за постами с 🖥.",
    "scam": "⚠️ Если сомневаешься в проекте — не спеши подключать кошелёк, сначала проверь официальные соцсети проекта.",
    "скам": "⚠️ Если сомневаешься в проекте — не спеши подключать кошелёк, сначала проверь официальные соцсети проекта.",
    "кинули": "⚠️ Если сомневаешься в проекте — не спеши подключать кошелёк, сначала проверь официальные соцсети проекта.",
    "развод": "⚠️ Если сомневаешься в проекте — не спеши подключать кошелёк, сначала проверь официальные соцсети проекта.",
    "канал": "📢 Основной канал с новостями: @cryptoping_ru",
    "источник": "📢 Основной канал с новостями: @cryptoping_ru",
    "правила": "📌 Правил пока немного: без спама и рекламы сторонних проектов без согласования. Приятного общения!",
    "кошелек": "👛 Совет: никогда не вводи seed-фразу от кошелька на сторонних сайтах, даже если просят «для верификации».",
    "кошелёк": "👛 Совет: никогда не вводи seed-фразу от кошелька на сторонних сайтах, даже если просят «для верификации».",
    "wallet": "👛 Совет: никогда не вводи seed-фразу от кошелька на сторонних сайтах, даже если просят «для верификации».",
    "seed": "👛 Совет: никогда не вводи seed-фразу от кошелька на сторонних сайтах, даже если просят «для верификации».",
    "газ": "⛽ Комиссия сети (газ) зависит от загруженности блокчейна — перед минтом/транзакцией стоит проверить текущий газ.",
    "gas fee": "⛽ Комиссия сети (газ) зависит от загруженности блокчейна — перед минтом/транзакцией стоит проверить текущий газ.",
    "своп": "🔄 Своп (обмен токенов) — используй только проверенные DEX (Uniswap, Jupiter и т.п.), проверяй адрес контракта перед подтверждением.",
    "свап": "🔄 Своп (обмен токенов) — используй только проверенные DEX (Uniswap, Jupiter и т.п.), проверяй адрес контракта перед подтверждением.",
    "swap": "🔄 Своп (обмен токенов) — используй только проверенные DEX (Uniswap, Jupiter и т.п.), проверяй адрес контракта перед подтверждением.",
    "стейкинг": "🔒 Стейкинг — блокировка токенов ради вознаграждения. Перед стейком проверяй платформу — от неё зависит, сможешь ли забрать токены обратно.",
    "стейк": "🔒 Стейкинг — блокировка токенов ради вознаграждения. Перед стейком проверяй платформу — от неё зависит, сможешь ли забрать токены обратно.",
    "staking": "🔒 Стейкинг — блокировка токенов ради вознаграждения. Перед стейком проверяй платформу — от неё зависит, сможешь ли забрать токены обратно.",
    "когда дроп": "🪂 Даты конкретных дропов смотри в постах канала @cryptoping_ru — бот следит за новостями по ним.",
    "когда следующий": "📢 Следи за постами в @cryptoping_ru — как только выходит новость, бот присылает её сюда.",
    "сколько стоит вход": "💰 Расходы зависят от конкретного проекта (обычно это газ сети) — детали смотри в новости по конкретному дропу/минту.",
    "как участвовать": "📌 Обычно нужно: кошелёк, немного газа на комиссию, и выполнение условий проекта (подписки, транзакции и т.п.) — детали в конкретной новости.",
    "как участвовать в дропе": "📌 Обычно нужно: кошелёк, немного газа на комиссию, и выполнение условий проекта (подписки, транзакции и т.п.) — детали в конкретной новости.",
    "стоит ли участвовать": "🤔 Это решаешь сам — оцени репутацию проекта, риски (не вкладывай больше, чем готов потерять) и соотнеси с потраченным временем.",
}


def is_mostly_greeting(text):
    words = re.findall(r"\w+", text.lower())
    if len(words) > 4:
        return False
    return any(greeting in text for greeting in GREETINGS)


async def on_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    for member in update.message.new_chat_members:
        name = member.first_name or member.username or "друг"
        await update.message.reply_text(WELCOME_TEXT.format(name=name))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "ℹ️ Частые вопросы:\n\n"
        "• Основной канал с новостями: @cryptoping_ru\n"
        "• Пишем про: airdrop, NFT, тестнеты, ноды\n"
        "• Это не финансовый совет, всегда проверяй сам (DYOR)"
    )
    await update.effective_message.reply_text(text)


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.lower()
    if is_mostly_greeting(text):
        await update.message.reply_text("👋 Привет! Напиши /help, если хочешь узнать, о чём этот чат.")
        return
    for keyword in sorted(AUTO_REPLIES, key=len, reverse=True):
        if keyword in text:
            await update.message.reply_text(AUTO_REPLIES[keyword])
            break


async def _growth_admin(update, context):
    message = getattr(update, "effective_message", None)
    chat = getattr(update, "effective_chat", None)
    sender_chat = getattr(message, "sender_chat", None) if message else None
    chat_id = getattr(chat, "id", None)
    sender_chat_id = getattr(sender_chat, "id", None)
    candidates = [
        getattr(update, "effective_user", None),
        getattr(message, "from_user", None) if message else None,
    ]

    user = getattr(update, "effective_user", None)
    if chat_id == GROUP_CHAT_ID and getattr(user, "id", None) == 777000:
        logging.info("growth auth allowed: group identity user_id=777000 chat_id=%s", chat_id)
        return True

    if chat_id == GROUP_CHAT_ID and sender_chat_id == GROUP_CHAT_ID:
        logging.info("growth auth allowed: anonymous group admin chat_id=%s", chat_id)
        return True

    for candidate in candidates:
        if candidate is not None and getattr(candidate, "id", None) in getattr(config, "GROWTH_ADMIN_IDS", set()):
            logging.info("growth auth allowed: configured admin user_id=%s chat_id=%s", candidate.id, chat_id)
            return True

    user = next((candidate for candidate in candidates if candidate is not None), None)
    if user is None:
        logging.warning("growth auth denied: no user chat_id=%s sender_chat_id=%s update_id=%s",
                        chat_id, sender_chat_id, getattr(update, "update_id", None))
        return False
    try:
        member = await context.bot.get_chat_member(GROUP_CHAT_ID, user.id)
        allowed = member.status in ("administrator", "creator")
        logging.info("growth auth user_id=%s chat_id=%s status=%s allowed=%s",
                     user.id, chat_id, member.status, allowed)
        return allowed
    except Exception:
        logging.exception("Unable to verify growth command administrator user_id=%s chat_id=%s",
                          user.id, chat_id)
        return False


async def growth_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _growth_admin(update, context):
        await update.effective_message.reply_text("Команда доступна только администраторам группы.")
        return
    if len(context.args) != 1:
        await update.effective_message.reply_text("Использование: /growthlink source_name")
        return
    source = context.args[0].strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", source):
        await update.effective_message.reply_text("Источник: 1–32 символа, только латиница, цифры, _ и -.")
        return
    try:
        invite = await context.bot.create_chat_invite_link(
            chat_id=CHAT_ID, name=source, creates_join_request=False
        )
        growth_db.save_link(invite.invite_link, source, update.effective_user.id)
        await update.effective_message.reply_text(
            f"Источник: {source}\n"
            f"Отслеживаемая ссылка: {invite.invite_link}\n\n"
            "Готовый текст для размещения:\n"
            "🛰 CryptoPing RU — крипто-активности и новости Web3.\n"
            "Airdrop, тестнеты, ноды и NFT в одном канале.\n"
            f"Подписаться: {invite.invite_link}"
        )
    except Exception:
        logging.exception("Failed to create growth invite link")
        await update.effective_message.reply_text(
            "Не удалось создать ссылку. Проверь права бота администратора канала."
        )


async def growth_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _growth_admin(update, context):
        await update.effective_message.reply_text("Команда доступна только администраторам группы.")
        return
    days = None
    if context.args:
        if len(context.args) != 1:
            await update.effective_message.reply_text(
                "Использование: /growthreport [7d|30d|all]"
            )
            return
        period = context.args[0].strip().lower()
        if period in {"all", "все", "всё"}:
            days = None
        else:
            match = re.fullmatch(r"(\d{1,4})(?:d|д)?", period)
            if not match or not 1 <= int(match.group(1)) <= 3650:
                await update.effective_message.reply_text(
                    "Укажи период: /growthreport 7d, /growthreport 30d или /growthreport all."
                )
                return
            days = int(match.group(1))

    rows = growth_db.source_report(days)
    total_joins = sum(row[1] for row in rows)
    total_leaves = sum(row[2] for row in rows)
    total_net = sum(row[3] for row in rows)
    total_active = sum(row[4] for row in rows)
    period_label = f"последние {days} дн." if days is not None else "вся история"
    lines = [
        "Отчёт CryptoPing RU",
        f"Период: {period_label}",
        f"Вступления: {total_joins}",
        f"Отписки: {total_leaves}",
        f"Баланс событий: {total_net}",
        f"Активны сейчас в базе: {total_active}",
        "",
    ]
    if rows:
        for source, joins, leaves, net, active in rows:
            lines.append(
                f"{source}: +{joins} вступл., −{leaves} отписок, "
                f"баланс {net}, активны сейчас {active}"
            )
    else:
        lines.append("За выбранный период событий и известных активных участников нет.")
    lines.extend([
        "",
        "Активные — только участники, чьи изменения членства видел бот; это не полное "
        "число подписчиков канала. Вступления без известной invite-ссылки идут в "
        "источник unattributed. Telegram Bot API не показывает число кликов по ссылкам.",
    ])
    await update.effective_message.reply_text("\n".join(lines))


def is_telegram_member(chat_member):
    """Treat restricted users as members only when Telegram sets is_member=True."""
    status = getattr(chat_member, "status", None)
    if status in ("member", "administrator", "creator"):
        return True
    if status == "restricted":
        return bool(getattr(chat_member, "is_member", False))
    return False


async def track_channel_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    event = update.chat_member
    if not event:
        return
    old = event.old_chat_member
    new = event.new_chat_member
    invite = getattr(event, "invite_link", None)
    logging.info(
        "chat_member received update_id=%s chat_id=%s chat_type=%s old_status=%s new_status=%s "
        "invite_present=%s invite_name=%s",
        update.update_id, event.chat.id, event.chat.type, old.status, new.status,
        bool(invite and invite.invite_link), getattr(invite, "name", None) if invite else None,
    )
    try:
        channel = await context.bot.get_chat(CHAT_ID)
        if event.chat.id != channel.id:
            logging.info("chat_member ignored: unexpected chat_id=%s expected_channel_id=%s",
                         event.chat.id, channel.id)
            return
        was_member = is_telegram_member(old)
        is_member = is_telegram_member(new)
        if was_member == is_member:
            logging.info("chat_member ignored: membership unchanged update_id=%s", update.update_id)
            return
        user = new.user
        if user.is_bot:
            logging.info("chat_member ignored: bot user_id=%s", user.id)
            return
        invite_url = invite.invite_link if invite else None
        growth_db.record_member(update.update_id, user.id, invite_url, is_member)
        logging.info("chat_member recorded update_id=%s user_id=%s joined=%s invite_present=%s",
                     update.update_id, user.id, is_member, bool(invite_url))
    except Exception:
        logging.exception("Failed to record channel membership event update_id=%s", update.update_id)



async def _current_chat_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Only the current group owner/admin can opt that group into scheduled promo."""
    chat = update.effective_chat
    message = update.effective_message
    if chat is None or chat.type not in ("group", "supergroup"):
        return False

    sender_chat = getattr(message, "sender_chat", None) if message else None
    if sender_chat is not None and getattr(sender_chat, "id", None) == chat.id:
        # Telegram represents an anonymous group admin as the group itself.
        return True

    user = update.effective_user
    if user is None:
        return False
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        return member.status in ("administrator", "creator")
    except Exception:
        logging.exception(
            "Unable to verify current-chat administrator user_id=%s chat_id=%s",
            user.id, chat.id,
        )
        return False


async def allow_promotion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.effective_message
    if chat is None or message is None or chat.type not in ("group", "supergroup"):
        if message:
            await message.reply_text("Команду /allowpromo можно включить только внутри группы.")
        return
    if not await _current_chat_admin(update, context):
        await message.reply_text("Включить автопубликации может только администратор этой группы.")
        return

    source = f"promo_{abs(chat.id)}"
    authorized_by = getattr(update.effective_user, "id", None)
    try:
        invite = await context.bot.create_chat_invite_link(
            chat_id=CHAT_ID, name=source, creates_join_request=False
        )
        growth_db.save_link(invite.invite_link, source, authorized_by)
        growth_db.enable_promotion_target(
            chat_id=chat.id,
            title=chat.title or chat.username or str(chat.id),
            username=chat.username,
            invite_link=invite.invite_link,
            authorized_by=authorized_by,
        )
        interval_hours = int(getattr(config, "PROMOTION_INTERVAL_HOURS", 72))
        await message.reply_text(
            "Автопромо включено по запросу администратора этой группы.\n"
            f"@cryptoping_ru будет публиковаться не чаще одного раза в {interval_hours} ч.\n"
            "Ссылка для этой группы отслеживается отдельно.\n"
            "Отключить: /disablepromo"
        )
        logging.info(
            "promotion target enabled chat_id=%s title=%s authorized_by=%s",
            chat.id, chat.title, authorized_by,
        )
    except Exception:
        logging.exception("Failed to enable promotion target chat_id=%s", chat.id)
        await message.reply_text(
            "Не удалось включить автопромо. Проверь, что бот — администратор "
            "канала @cryptoping_ru и может создавать invite-ссылки."
        )


async def disable_promotion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.effective_message
    if chat is None or message is None or chat.type not in ("group", "supergroup"):
        if message:
            await message.reply_text("Команду /disablepromo нужно вызвать внутри группы.")
        return
    if not await _current_chat_admin(update, context):
        await message.reply_text("Отключить автопубликации может только администратор этой группы.")
        return

    disabled = growth_db.disable_promotion_target(chat.id)
    if disabled:
        await message.reply_text("Автопромо отключено. Новые публикации в эту группу отправляться не будут.")
    else:
        await message.reply_text("Для этой группы автопромо уже отключено или не было включено.")


async def promotion_targets_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _growth_admin(update, context):
        await update.effective_message.reply_text("Команда доступна только администраторам группы.")
        return
    targets = growth_db.list_promotion_targets(enabled_only=True)
    if not targets:
        await update.effective_message.reply_text(
            "Нет групп, включивших автопромо. Администратор целевой группы должен вызвать /allowpromo."
        )
        return

    lines = ["Группы с включённым автопромо:", ""]
    for chat_id, title, username, last_post_at, last_error in targets[:40]:
        label = f"@{username}" if username else title
        status = f"последняя публикация: {last_post_at}" if last_post_at else "ожидает первой публикации"
        if last_error:
            status += f"; ошибка: {last_error[:120]}"
        lines.append(f"• {label} ({chat_id}) — {status}")
    if len(targets) > 40:
        lines.append(f"...и ещё {len(targets) - 40} групп.")
    await update.effective_message.reply_text("\n".join(lines))


def _promotion_text(invite_link):
    return (
        "🛰 CryptoPing RU — новости и возможности Web3.\n"
        "Airdrop, тестнеты, ноды и NFT. Условия и риски проверяйте по официальным источникам.\n"
        f"Подписаться: {invite_link}"
    )


async def publish_due_promotions(context: ContextTypes.DEFAULT_TYPE):
    """Publish only to groups whose own administrators explicitly opted in."""
    interval_hours = int(getattr(config, "PROMOTION_INTERVAL_HOURS", 72))
    try:
        targets = growth_db.due_promotion_targets(interval_hours)
    except Exception:
        logging.exception("Unable to load scheduled promotion targets")
        return

    for chat_id, title, username, invite_link in targets:
        try:
            sent = await context.bot.send_message(
                chat_id=chat_id,
                text=_promotion_text(invite_link),
                disable_web_page_preview=True,
            )
            growth_db.mark_promotion_sent(chat_id, sent.message_id)
            logging.info(
                "promotion sent chat_id=%s title=%s message_id=%s",
                chat_id, title, sent.message_id,
            )
        except (Forbidden, BadRequest) as exc:
            growth_db.mark_promotion_failed(chat_id, exc, disable=True)
            logging.warning(
                "promotion target disabled after Telegram rejected post chat_id=%s error=%s",
                chat_id, exc,
            )
        except TelegramError as exc:
            growth_db.mark_promotion_failed(chat_id, exc, disable=False)
            logging.warning("temporary promotion send failure chat_id=%s error=%s", chat_id, exc)
        except Exception as exc:
            growth_db.mark_promotion_failed(chat_id, exc, disable=False)
            logging.exception("Unexpected promotion send failure chat_id=%s", chat_id)
        await asyncio.sleep(1.2)


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("growthlink", growth_link))
    app.add_handler(CommandHandler("growthreport", growth_report))
    app.add_handler(CommandHandler("allowpromo", allow_promotion))
    app.add_handler(CommandHandler("disablepromo", disable_promotion))
    app.add_handler(CommandHandler("promotetargets", promotion_targets_report))
    app.add_handler(ChatMemberHandler(track_channel_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    interval_hours = int(getattr(config, "PROMOTION_INTERVAL_HOURS", 72))
    if not 1 <= interval_hours <= 720:
        raise ValueError("PROMOTION_INTERVAL_HOURS must be between 1 and 720 hours")
    check_interval_minutes = int(getattr(config, "PROMOTION_CHECK_INTERVAL_MINUTES", 5))
    if not 1 <= check_interval_minutes <= 60:
        raise ValueError("PROMOTION_CHECK_INTERVAL_MINUTES must be between 1 and 60 minutes")
    if app.job_queue is None:
        raise RuntimeError(
            "JobQueue is unavailable. Install dependencies from requirements.txt "
            "including the job-queue extra."
        )
    app.job_queue.run_repeating(
        publish_due_promotions,
        interval=check_interval_minutes * 60,
        first=10,
        name="opt-in-promotion-scheduler",
        job_kwargs={"max_instances": 1, "coalesce": True},
    )
    logging.info(
        "Opt-in promotion scheduler enabled interval_hours=%s check_interval_minutes=%s",
        interval_hours, check_interval_minutes,
    )
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
