import asyncio
import logging
import config
import re

from telegram import Update
from telegram.error import BadRequest, Forbidden, TelegramError
from telegram.ext import (
    ApplicationBuilder,
    TypeHandler,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import CHAT_ID, GROUP_CHAT_ID, TELEGRAM_TOKEN
import growth_db
from publisher.telegram import (
    register_handlers as register_publisher_handlers,
    publish_captured_source_posts,
    publish_pending_external_drafts,
)
from publisher.storage import PublisherStore
from publisher.trial_targets import TRIAL_EXTERNAL_GROUPS

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


async def on_source_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Capture new text/caption posts from our own news channel as drafts only."""
    post = update.channel_post
    if not post:
        return
    configured_source = str(CHAT_ID).strip()
    if configured_source.startswith("@"):
        if (getattr(post.chat, "username", None) or "").lower() != configured_source[1:].lower():
            return
    elif str(post.chat_id) != configured_source:
        return
    body = (post.text or post.caption or "").strip()
    if not body:
        logging.info("publisher source post skipped: no text/caption message_id=%s", post.message_id)
        return
    title = " ".join(body.split())[:100]
    username = getattr(post.chat, "username", None)
    source_url = f"https://t.me/{username}/{post.message_id}" if username else None
    try:
        draft_id, created = PublisherStore().capture_source_post(
            post.chat_id, post.message_id, title, body, source_url
        )
        logging.info("publisher source captured draft_id=%s message_id=%s created=%s", draft_id, post.message_id, created)
    except Exception:
        logging.exception("Unable to capture source channel post message_id=%s", post.message_id)


async def on_bot_chat_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Register public groups when the bot is added as an ordinary member."""
    event = update.my_chat_member
    if not event:
        return
    chat = event.chat
    if chat.type not in ("group", "supergroup") or not getattr(chat, "username", None):
        return

    store = PublisherStore()
    handle = f"@{chat.username}"
    target_id = store.add_target("group", handle)
    new_status = getattr(event.new_chat_member, "status", None)
    if new_status in ("left", "kicked"):
        target = store.get_target(target_id)
        if target and target["status"] == "approved":
            store.pause_target(target_id)
        logging.info("publisher external group membership removed handle=%s target_id=%s", handle, target_id)
        return

    restricted_can_send = (
        new_status == "restricted"
        and bool(getattr(event.new_chat_member, "is_member", False))
        and getattr(getattr(event.new_chat_member, "permissions", None), "can_send_messages", None) is True
    )
    if new_status in ("member", "administrator", "creator") or restricted_can_send:
        store.review_target(
            target_id,
            "approve",
            "allowed",
            "Telegram my_chat_member confirms bot membership. Live send permissions are checked before each publication.",
        )
        logging.info(
            "publisher external group enabled handle=%s target_id=%s bot_status=%s; live send permission will be checked per post",
            handle, target_id, new_status,
        )
        return

    logging.info(
        "publisher external group discovered handle=%s target_id=%s bot_status=%s; not currently a member",
        handle, target_id, new_status,
    )


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



async def growth_retention(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _growth_admin(update, context):
        await update.effective_message.reply_text("Команда доступна только администраторам группы.")
        return
    days = 30
    if context.args:
        if len(context.args) != 1:
            await update.effective_message.reply_text(
                "Использование: /growthretention [30d]"
            )
            return
        match = re.fullmatch(r"(\d{1,4})(?:d|д)?", context.args[0].strip().lower())
        if not match or not 1 <= int(match.group(1)) <= 3650:
            await update.effective_message.reply_text(
                "Укажи окно когорты: /growthretention 30d."
            )
            return
        days = int(match.group(1))

    rows = growth_db.cohort_retention(days=days, retention_days=7)
    lines = [
        "Удержание CryptoPing RU",
        f"Окно первых наблюдаемых вступлений: {days} дн.",
        "Метрика: доля участников, оставшихся в канале через 7 дней после вступления.",
        "Учитываются только когорты, для которых прошло полных 7 дней.",
        "",
    ]
    if rows:
        for source, cohort_size, retained, rate in rows:
            lines.append(
                f"{source}: {retained}/{cohort_size} удержано ({rate:.1f}%)"
            )
    else:
        lines.append("Пока нет зрелых когорт с достаточной историей для D7.")
    lines.extend([
        "",
        "Это удержание среди первых вступлений, наблюдавшихся ботом, а не среди всех подписчиков. "
        "Пропущенные Telegram chat_member updates могут исказить результат.",
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



async def refresh_trial_group_memberships(context: ContextTypes.DEFAULT_TYPE):
    """Enable only the two trial destinations after live Telegram permission checks."""
    store = PublisherStore()
    bot_user = await context.bot.get_me()
    targets = {row["handle"].lower(): row for row in store.list_targets()}

    for handle in sorted(TRIAL_EXTERNAL_GROUPS):
        target = targets.get(handle)
        if not target:
            logging.error("publisher trial target missing from registry handle=%s", handle)
            continue
        try:
            chat = await context.bot.get_chat(handle)
            if getattr(chat, "type", None) not in ("group", "supergroup"):
                logging.warning("publisher trial target is not a group handle=%s type=%s",
                                handle, getattr(chat, "type", None))
                continue

            member = await context.bot.get_chat_member(chat.id, bot_user.id)
            status = getattr(member, "status", None)
            if status in ("administrator", "creator"):
                can_send = status == "creator" or (
                    getattr(member, "can_send_messages", True) is not False
                )
            elif status == "member":
                permissions = getattr(chat, "permissions", None)
                can_send = getattr(permissions, "can_send_messages", None) is True
            elif status == "restricted":
                permissions = getattr(member, "permissions", None)
                can_send = bool(getattr(member, "is_member", False)) and (
                    getattr(permissions, "can_send_messages", None) is True
                )
            else:
                can_send = False

            if can_send:
                if target["status"] != "approved" or target["promotion_policy"] != "allowed":
                    evidence = (
                        "Owner confirms this is one of the first two subscribed groups and "
                        "authorizes CryptoPing RU news publication for the trial. Telegram "
                        f"Bot API verified bot membership status={status}; the publisher "
                        "rechecks live send permission before every post."
                    )
                    store.review_target(target["id"], "approve", "allowed", evidence)
                    logging.info(
                        "publisher trial target enabled handle=%s bot_status=%s pinned_rules=%s",
                        handle, status, bool(getattr(chat, "pinned_message", None)),
                    )
                else:
                    logging.info("publisher trial target ready handle=%s bot_status=%s",
                                 handle, status)
            else:
                if target["status"] == "approved":
                    store.pause_target(target["id"])
                logging.info(
                    "publisher trial target not ready handle=%s bot_status=%s; "
                    "bot must be a member with ordinary send permission",
                    handle, status,
                )
        except Exception as exc:
            logging.warning("publisher trial access check failed handle=%s error=%s",
                            handle, str(exc)[:240])


async def publish_captured_channel_posts(context: ContextTypes.DEFAULT_TYPE):
    """Auto-publish new posts from our news channel into our own community."""
    try:
        store = PublisherStore()
        target = next((
            row for row in store.list_targets()
            if row["handle"] == "@cryptoping_ru_chat"
            and row["status"] == "approved"
            and row["promotion_policy"] == "allowed"
        ), None)
        if not target:
            logging.error("publisher autonomous route disabled: owned community target is not approved")
            return
        outcomes = await publish_captured_source_posts(context.bot, store, target["id"], limit=3)
        external_pending = await publish_pending_external_drafts(
            context.bot, store, target["id"], limit=5
        )
        for item in external_pending:
            logging.info(
                "publisher trial fanout draft_id=%s target=%s status=%s reason=%s",
                item.get("draft_id"), item.get("handle", "-"),
                item.get("status"), item.get("reason", ""),
            )
        # Register Publisher's destination-specific channel invites in the
        # growth ledger so subsequent joins can be attributed to the destination.
        for publisher_target in store.list_targets():
            invite_link = store.get_target_referral_link(publisher_target["id"])
            if invite_link:
                growth_db.save_link(
                    invite_link, f"publisher_target_{publisher_target['id']}", None
                )
        for item in outcomes:
            logging.info(
                "publisher autonomous result draft_id=%s status=%s reason=%s",
                item.get("draft_id"), item.get("status"), item.get("reason", ""),
            )
    except Exception:
        logging.exception("publisher autonomous source pipeline failed")


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member))
    app.add_handler(TypeHandler(Update, on_source_channel_post), group=1)
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("growthlink", growth_link))
    app.add_handler(CommandHandler("growthreport", growth_report))
    app.add_handler(CommandHandler("growthretention", growth_retention))
    app.add_handler(ChatMemberHandler(track_channel_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(ChatMemberHandler(on_bot_chat_membership, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    register_publisher_handlers(app, _growth_admin, GROUP_CHAT_ID)

    if app.job_queue is None:
        raise RuntimeError(
            "JobQueue is unavailable. Install dependencies from requirements.txt "
            "including the job-queue extra."
        )
    app.job_queue.run_repeating(
        refresh_trial_group_memberships,
        interval=300,
        first=5,
        name="publisher-trial-group-membership-check",
        job_kwargs={"max_instances": 1, "coalesce": True},
    )
    app.job_queue.run_repeating(
        publish_captured_channel_posts,
        interval=60,
        first=20,
        name="publisher-own-channel-autopublish",
        job_kwargs={"max_instances": 1, "coalesce": True},
    )
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

