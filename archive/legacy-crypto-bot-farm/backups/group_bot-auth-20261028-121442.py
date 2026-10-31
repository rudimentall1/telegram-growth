import logging
import re
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, ContextTypes,
    MessageHandler, CommandHandler, ChatMemberHandler, filters
)
from config import TELEGRAM_TOKEN, GROUP_CHAT_ID, CHAT_ID
import growth_db

logging.basicConfig(level=logging.INFO)

WELCOME_TEXT = (
    "👋 Добро пожаловать, {name}!\n\n"
    "Здесь обсуждаем новости из канала @cryptoping_ru — airdrop, NFT, тестнеты, ноды.\n"
    "Напиши /help, если хочешь посмотреть частые вопросы."
)

GREETINGS = ["привет", "здарова", "хай", "hello", "hi", "приветствую", "здравствуй"]

AUTO_REPLIES = {
    # airdrop
    "airdrop": "🪂 Свежие airdrop смотри в основном канале: @cryptoping_ru",
    "аирдроп": "🪂 Свежие airdrop смотри в основном канале: @cryptoping_ru",
    "эирдроп": "🪂 Свежие airdrop смотри в основном канале: @cryptoping_ru",
    "дроп": "🪂 Свежие airdrop смотри в основном канале: @cryptoping_ru",
    "ретродроп": "🪂 Свежие airdrop смотри в основном канале: @cryptoping_ru",

    # nft
    "nft": "🖼 Новости по NFT постим в @cryptoping_ru, там же и минты.",
    "нфт": "🖼 Новости по NFT постим в @cryptoping_ru, там же и минты.",
    "минт": "🖼 Новости по NFT постим в @cryptoping_ru, там же и минты.",
    "минтить": "🖼 Новости по NFT постим в @cryptoping_ru, там же и минты.",

    # nodes/testnet
    "node": "🖥 Про ноды/тестнеты пишем в @cryptoping_ru, следи за постами с 🖥.",
    "нода": "🖥 Про ноды/тестнеты пишем в @cryptoping_ru, следи за постами с 🖥.",
    "ноду": "🖥 Про ноды/тестнеты пишем в @cryptoping_ru, следи за постами с 🖥.",
    "ноды": "🖥 Про ноды/тестнеты пишем в @cryptoping_ru, следи за постами с 🖥.",
    "тестнет": "🖥 Про ноды/тестнеты пишем в @cryptoping_ru, следи за постами с 🖥.",
    "валидатор": "🖥 Про ноды/тестнеты пишем в @cryptoping_ru, следи за постами с 🖥.",

    # scam warnings
    "scam": "⚠️ Если сомневаешься в проекте — не спеши подключать кошелёк, сначала проверь официальные соцсети проекта.",
    "скам": "⚠️ Если сомневаешься в проекте — не спеши подключать кошелёк, сначала проверь официальные соцсети проекта.",
    "кинули": "⚠️ Если сомневаешься в проекте — не спеши подключать кошелёк, сначала проверь официальные соцсети проекта.",
    "развод": "⚠️ Если сомневаешься в проекте — не спеши подключать кошелёк, сначала проверь официальные соцсети проекта.",

    # общее про канал
    "канал": "📢 Основной канал с новостями: @cryptoping_ru",
    "источник": "📢 Основной канал с новостями: @cryptoping_ru",
    "правила": "📌 Правил пока немного: без спама и рекламы сторонних проектов без согласования. Приятного общения!",

    # крипто-сленг
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

    # частые вопросы - составные фразы, чтобы не ловить обычные разговоры
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
    return any(g in text for g in GREETINGS)

async def on_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text(text)

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.lower()

    if is_mostly_greeting(text):
        await update.message.reply_text("👋 Привет! Напиши /help, если хочешь узнать, о чём этот чат.")
        return

    # сортируем по длине ключа - сначала проверяем более длинные и точные фразы,
    # чтобы "когда дроп" сработало раньше общего "дроп"
    for keyword in sorted(AUTO_REPLIES, key=len, reverse=True):
        if keyword in text:
            await update.message.reply_text(AUTO_REPLIES[keyword])
            break


async def _growth_admin(update, context):
    user = update.effective_user
    if not user:
        return False
    try:
        member = await context.bot.get_chat_member(GROUP_CHAT_ID, user.id)
        return member.status in ("administrator", "creator")
    except Exception:
        logging.exception("Unable to verify growth command administrator")
        return False

async def growth_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _growth_admin(update, context):
        await update.effective_message.reply_text(
            "Команда доступна только администраторам группы."
        )
        return
    if len(context.args) != 1:
        await update.effective_message.reply_text(
            "Использование: /growthlink source_name"
        )
        return

    source = context.args[0].strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", source):
        await update.effective_message.reply_text(
            "Источник: 1–32 символа, только латиница, цифры, _ и -."
        )
        return

    try:
        invite = await context.bot.create_chat_invite_link(
            chat_id=CHAT_ID, name=source, creates_join_request=False
        )
        growth_db.save_link(invite.invite_link, source, update.effective_user.id)
        await update.effective_message.reply_text(
            f"Источник: {source}\nСсылка: {invite.invite_link}"
        )
    except Exception:
        logging.exception("Failed to create growth invite link")
        await update.effective_message.reply_text(
            "Не удалось создать ссылку. Проверь права бота администратора канала."
        )

async def growth_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _growth_admin(update, context):
        await update.effective_message.reply_text(
            "Команда доступна только администраторам группы."
        )
        return
    rows = growth_db.report()
    lines = ["Отчёт CryptoPing RU", ""]
    if rows:
        for source, joins, leaves, net in rows:
            lines.append(
                f"{source}: вступления {joins}, отписки {leaves}, "
                f"баланс событий {net}"
            )
    else:
        lines.append("Событий пока нет.")
    lines.extend(["", f"Сейчас числятся участниками: {growth_db.active_count()}"])
    lines.append(
        "Примечание: Telegram не предоставляет число кликов по invite-ссылкам. "
        "Баланс событий — не доказательство удержания конкретной кампании."
    )
    await update.effective_message.reply_text("\n".join(lines))

async def track_channel_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    event = update.chat_member
    if not event:
        return
    try:
        channel = await context.bot.get_chat(CHAT_ID)
        if event.chat.id != channel.id:
            return

        old = event.old_chat_member.status
        new = event.new_chat_member.status
        was_member = old in ("member", "administrator", "creator")
        is_member = new in ("member", "administrator", "creator")
        if was_member == is_member:
            return

        user = event.new_chat_member.user
        if user.is_bot:
            return

        invite = getattr(event, "invite_link", None)
        growth_db.record_member(
            update.update_id, user.id,
            invite.invite_link if invite else None,
            is_member,
        )
    except Exception:
        logging.exception("Failed to record channel membership event")


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("growthlink", growth_link))
    app.add_handler(CommandHandler("growthreport", growth_report))
    app.add_handler(ChatMemberHandler(track_channel_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
