"""Opt-in Telegram channel cross-promotion, adapted for the existing PTB bot.

Inspired by the workflow of the MIT-licensed project
https://github.com/qilaidev/channel-promo-bot. This module uses the existing
python-telegram-bot Application and growth.db; it does not start another poller.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from telegram import Update
from telegram.error import BadRequest, Forbidden, RetryAfter, TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes

import config
import growth_db
from config import CHAT_ID, GROUP_CHAT_ID

log = logging.getLogger(__name__)

DEFAULT_INTERVAL_HOURS = 72
DEFAULT_MIN_MEMBERS = 10
USERNAME_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?t\.me/([A-Za-z0-9_]{5,32})/?$|^@?([A-Za-z0-9_]{5,32})$",
    re.IGNORECASE,
)


def _dict_from_row(cursor, row) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(zip((col[0] for col in cursor.description), row))


def init_db() -> None:
    """Create the cross-promotion tables in the existing SQLite database."""
    with growth_db.connect() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS crosspromo_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL UNIQUE,
                title TEXT NOT NULL,
                username TEXT NOT NULL,
                member_count INTEGER NOT NULL DEFAULT 0,
                owner_user_id INTEGER,
                status TEXT NOT NULL CHECK (
                    status IN ('pending', 'active', 'paused', 'rejected', 'inactive')
                ),
                home_invite_link TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                approved_at TEXT,
                last_promo_at TEXT,
                last_error TEXT
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS crosspromo_deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_chat_id INTEGER NOT NULL,
                promoted_chat_id INTEGER NOT NULL,
                message_id INTEGER,
                sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_crosspromo_status_due
            ON crosspromo_channels(status, last_promo_at)
            """
        )
        db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_crosspromo_delivery_history
            ON crosspromo_deliveries(target_chat_id, promoted_chat_id, sent_at)
            """
        )


def get_channel(chat_id: int) -> dict[str, Any] | None:
    with growth_db.connect() as db:
        cursor = db.execute(
            "SELECT * FROM crosspromo_channels WHERE chat_id = ?", (chat_id,)
        )
        return _dict_from_row(cursor, cursor.fetchone())


def get_channel_by_id(channel_id: int) -> dict[str, Any] | None:
    with growth_db.connect() as db:
        cursor = db.execute(
            "SELECT * FROM crosspromo_channels WHERE id = ?", (channel_id,)
        )
        return _dict_from_row(cursor, cursor.fetchone())


def _update_channel_metadata(
    chat_id: int,
    title: str,
    username: str,
    member_count: int,
    owner_user_id: int | None = None,
) -> None:
    with growth_db.connect() as db:
        db.execute(
            """
            UPDATE crosspromo_channels
            SET title = ?, username = ?, member_count = ?,
                owner_user_id = COALESCE(?, owner_user_id),
                last_error = NULL
            WHERE chat_id = ?
            """,
            (title, username, member_count, owner_user_id, chat_id),
        )


def add_pending_channel(
    chat_id: int,
    title: str,
    username: str,
    member_count: int,
    owner_user_id: int,
    home_invite_link: str | None,
) -> tuple[int, str]:
    """Add a channel for owner review; preserve an existing active/paused state."""
    with growth_db.connect() as db:
        cursor = db.execute(
            "SELECT id, status, home_invite_link FROM crosspromo_channels WHERE chat_id = ?",
            (chat_id,),
        )
        existing = cursor.fetchone()
        if existing:
            channel_id, status, old_link = existing
            db.execute(
                """
                UPDATE crosspromo_channels
                SET title = ?, username = ?, member_count = ?, owner_user_id = ?,
                    home_invite_link = COALESCE(home_invite_link, ?),
                    status = CASE
                        WHEN status IN ('active', 'paused') THEN status
                        ELSE 'pending'
                    END,
                    last_error = NULL
                WHERE chat_id = ?
                """,
                (title, username, member_count, owner_user_id, home_invite_link, chat_id),
            )
            return int(channel_id), str(status)
        cursor = db.execute(
            """
            INSERT INTO crosspromo_channels(
                chat_id, title, username, member_count, owner_user_id,
                status, home_invite_link
            ) VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """,
            (chat_id, title, username, member_count, owner_user_id, home_invite_link),
        )
        return int(cursor.lastrowid), "pending"


def ensure_home_channel(
    chat_id: int, title: str, username: str, member_count: int
) -> dict[str, Any]:
    """Register the owner's configured channel once, without undoing a pause."""
    current = get_channel(chat_id)
    if current is None:
        with growth_db.connect() as db:
            db.execute(
                """
                INSERT OR IGNORE INTO crosspromo_channels(
                    chat_id, title, username, member_count, status
                ) VALUES (?, ?, ?, ?, 'active')
                """,
                (chat_id, title, username, member_count),
            )
    elif current["status"] not in ("paused", "inactive", "rejected"):
        _update_channel_metadata(chat_id, title, username, member_count)
        with growth_db.connect() as db:
            db.execute(
                "UPDATE crosspromo_channels SET status='active' WHERE chat_id=?",
                (chat_id,),
            )
    return get_channel(chat_id)  # type: ignore[return-value]


def set_home_invite_link(chat_id: int, link: str) -> None:
    with growth_db.connect() as db:
        db.execute(
            """
            UPDATE crosspromo_channels SET home_invite_link = ?
            WHERE chat_id = ?
            """,
            (link, chat_id),
        )


def pending_channels() -> list[dict[str, Any]]:
    with growth_db.connect() as db:
        cursor = db.execute(
            """
            SELECT * FROM crosspromo_channels
            WHERE status = 'pending'
            ORDER BY created_at, id
            LIMIT 50
            """
        )
        return [_dict_from_row(cursor, row) for row in cursor.fetchall()]  # type: ignore[misc]


def active_channels() -> list[dict[str, Any]]:
    with growth_db.connect() as db:
        cursor = db.execute(
            """
            SELECT * FROM crosspromo_channels
            WHERE status = 'active'
            ORDER BY member_count, created_at, id
            """
        )
        return [_dict_from_row(cursor, row) for row in cursor.fetchall()]  # type: ignore[misc]


def approve_channel(channel_id: int, approved_by: int) -> bool:
    with growth_db.connect() as db:
        cursor = db.execute(
            """
            UPDATE crosspromo_channels
            SET status='active', approved_at=CURRENT_TIMESTAMP, last_error=NULL
            WHERE id=? AND status='pending'
            """,
            (channel_id,),
        )
        return cursor.rowcount > 0


def reject_channel(channel_id: int) -> bool:
    with growth_db.connect() as db:
        cursor = db.execute(
            """
            UPDATE crosspromo_channels SET status='rejected'
            WHERE id=? AND status='pending'
            """,
            (channel_id,),
        )
        return cursor.rowcount > 0


def set_channel_status(chat_id: int, status: str) -> bool:
    if status not in {"active", "paused", "inactive", "rejected"}:
        raise ValueError("invalid cross-promotion status")
    with growth_db.connect() as db:
        cursor = db.execute(
            "UPDATE crosspromo_channels SET status=?, last_error=NULL WHERE chat_id=?",
            (status, chat_id),
        )
        return cursor.rowcount > 0


def due_targets(interval_hours: int = DEFAULT_INTERVAL_HOURS) -> list[dict[str, Any]]:
    interval_hours = int(interval_hours)
    if not 1 <= interval_hours <= 720:
        raise ValueError("interval_hours must be between 1 and 720")
    with growth_db.connect() as db:
        active_count = db.execute(
            "SELECT COUNT(*) FROM crosspromo_channels WHERE status='active'"
        ).fetchone()[0]
        if active_count < 2:
            return []
        cursor = db.execute(
            """
            SELECT * FROM crosspromo_channels
            WHERE status='active'
              AND (last_promo_at IS NULL
                   OR last_promo_at <= datetime('now', ?))
            ORDER BY COALESCE(last_promo_at, '1970-01-01 00:00:00'),
                     created_at, id
            """,
            (f"-{interval_hours} hours",),
        )
        return [_dict_from_row(cursor, row) for row in cursor.fetchall()]  # type: ignore[misc]


def select_candidate(target_chat_id: int) -> dict[str, Any] | None:
    """Pick a partner with a similar audience and fair per-target rotation."""
    with growth_db.connect() as db:
        target_cursor = db.execute(
            "SELECT member_count FROM crosspromo_channels WHERE chat_id=? AND status='active'",
            (target_chat_id,),
        )
        target = target_cursor.fetchone()
        if not target:
            return None
        target_size = max(1, int(target[0] or 1))

        cursor = db.execute(
            """
            SELECT c.*,
                (SELECT MAX(d.sent_at) FROM crosspromo_deliveries d
                 WHERE d.target_chat_id=? AND d.promoted_chat_id=c.chat_id) AS last_sent
            FROM crosspromo_channels c
            WHERE c.status='active' AND c.chat_id != ?
            ORDER BY COALESCE(last_sent, '1970-01-01 00:00:00'),
                     c.created_at, c.id
            """,
            (target_chat_id, target_chat_id),
        )
        candidates = [_dict_from_row(cursor, row) for row in cursor.fetchall()]
        if not candidates:
            return None

        low = max(1, target_size // 3)
        high = max(target_size * 3, DEFAULT_MIN_MEMBERS)
        similar = [
            item for item in candidates
            if low <= max(1, int(item["member_count"] or 1)) <= high
        ]
        if similar:
            candidates = similar

        recent_rows = db.execute(
            """
            SELECT DISTINCT promoted_chat_id FROM crosspromo_deliveries
            WHERE target_chat_id=? AND sent_at >= datetime('now', '-7 days')
            """,
            (target_chat_id,),
        ).fetchall()
        recent = {int(row[0]) for row in recent_rows}
        alternatives = [item for item in candidates if int(item["chat_id"]) not in recent]
        if alternatives:
            candidates = alternatives

        # Lowest exposure count breaks ties after the oldest/never-used delivery.
        counts: dict[int, int] = {}
        for item in candidates:
            counts[int(item["chat_id"])] = int(
                db.execute(
                    """
                    SELECT COUNT(*) FROM crosspromo_deliveries
                    WHERE target_chat_id=? AND promoted_chat_id=?
                    """,
                    (target_chat_id, item["chat_id"]),
                ).fetchone()[0]
            )
        candidates.sort(
            key=lambda item: (
                item.get("last_sent") or "1970-01-01 00:00:00",
                counts[int(item["chat_id"])],
                item["created_at"],
                int(item["id"]),
            )
        )
        return candidates[0]


def mark_delivery(target_chat_id: int, promoted_chat_id: int, message_id: int) -> None:
    with growth_db.connect() as db:
        db.execute(
            """
            INSERT INTO crosspromo_deliveries(
                target_chat_id, promoted_chat_id, message_id
            ) VALUES (?, ?, ?)
            """,
            (target_chat_id, promoted_chat_id, message_id),
        )
        db.execute(
            """
            UPDATE crosspromo_channels
            SET last_promo_at=CURRENT_TIMESTAMP, last_error=NULL
            WHERE chat_id=?
            """,
            (target_chat_id,),
        )


def mark_delivery_failed(chat_id: int, error: Exception, *, disable: bool) -> None:
    message = str(error).replace("\n", " ")[:500]
    with growth_db.connect() as db:
        db.execute(
            """
            UPDATE crosspromo_channels
            SET last_error=?,
                status=CASE WHEN ? THEN 'inactive' ELSE status END
            WHERE chat_id=?
            """,
            (message, int(disable), chat_id),
        )


async def _is_main_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    message = update.effective_message
    chat = update.effective_chat
    if user is None:
        sender_chat = getattr(message, "sender_chat", None) if message else None
        return bool(chat and sender_chat and sender_chat.id == GROUP_CHAT_ID)
    if user.id in getattr(config, "GROWTH_ADMIN_IDS", set()):
        return True
    try:
        member = await context.bot.get_chat_member(GROUP_CHAT_ID, user.id)
        return member.status in ("administrator", "creator")
    except Exception:
        log.exception("Cross-promo admin check failed for user_id=%s", user.id)
        return False


def _parse_public_username(value: str) -> str | None:
    match = USERNAME_RE.fullmatch(value.strip())
    if not match:
        return None
    return match.group(1) or match.group(2)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return
    await update.effective_message.reply_text(
        "🤝 Взаимное продвижение каналов CryptoPing RU\n\n"
        "Для владельца канала:\n"
        "/crosspromo_add @channel — подать канал в сеть взаимного продвижения.\n"
        "Наш бот должен быть администратором этого канала с правом публикации; "
        "отправитель должен быть администратором самого канала.\n\n"
        "Для администраторов CryptoPing RU:\n"
        "/crosspromopending — очередь на проверку.\n"
        "/crosspromoapprove ID — одобрить канал.\n"
        "/crosspromoreject ID — отклонить заявку.\n"
        "/crosspromolist — активная сеть.\n"
        "/crosspromopause — приостановить участие @cryptoping_ru.\n"
        "/crosspromoresume — возобновить участие.\n\n"
        f"Публикации выходят не чаще раза в {int(getattr(config, 'CROSSPROMO_INTERVAL_HOURS', DEFAULT_INTERVAL_HOURS))} ч. "
        "на канал. Продвижение взаимное; число подписчиков не гарантируется."
    )


async def add_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return
    if len(context.args) != 1:
        await message.reply_text("Использование: /crosspromo_add @channel")
        return
    username = _parse_public_username(context.args[0])
    if not username:
        await message.reply_text("Нужен публичный канал вида @channel или https://t.me/channel.")
        return

    try:
        home = await context.bot.get_chat(CHAT_ID)
        target = await context.bot.get_chat(f"@{username}")
        if target.type != "channel" or not target.username:
            await message.reply_text("Поддерживаются только публичные Telegram-каналы.")
            return
        if target.id == home.id:
            await message.reply_text("Это уже ваш основной канал CryptoPing RU.")
            return

        owner_member = await context.bot.get_chat_member(target.id, user.id)
        if owner_member.status not in ("administrator", "creator"):
            await message.reply_text("Подать канал может только его владелец или администратор.")
            return

        bot_user = await context.bot.get_me()
        bot_member = await context.bot.get_chat_member(target.id, bot_user.id)
        if bot_member.status not in ("administrator", "creator"):
            await message.reply_text(
                f"Сначала добавь @{bot_user.username} администратором в {target.title} "
                "с правом публикации. Чужие боты не нужны: используется наш "
                "@crypto_source_farm_bot."
            )
            return
        if bot_member.status != "creator" and not getattr(bot_member, "can_post_messages", False):
            await message.reply_text(
                f"У @{bot_user.username} нет права публиковать посты в {target.title}. "
                "Включи только право публикации и повтори команду."
            )
            return

        member_count = await context.bot.get_chat_member_count(target.id)
        min_members = max(1, int(getattr(config, "CROSSPROMO_MIN_MEMBERS", DEFAULT_MIN_MEMBERS)))
        if member_count < min_members:
            await message.reply_text(
                f"В канале {member_count} подписчиков; минимум для сети — {min_members}."
            )
            return

        current = get_channel(target.id)
        home_invite_link = current.get("home_invite_link") if current else None
        if not home_invite_link:
            source = f"xpromo_{abs(target.id)}"[:32]
            try:
                invite = await context.bot.create_chat_invite_link(
                    chat_id=home.id, name=source, creates_join_request=False
                )
                home_invite_link = invite.invite_link
                growth_db.save_link(home_invite_link, source, user.id)
            except TelegramError:
                # Public link remains a functional fallback; attribution will be weaker.
                log.exception("Could not create tracked CryptoPing invite for %s", target.id)

        channel_id, previous_status = add_pending_channel(
            chat_id=target.id,
            title=target.title or username,
            username=target.username,
            member_count=member_count,
            owner_user_id=user.id,
            home_invite_link=home_invite_link,
        )
        if previous_status == "active":
            await message.reply_text(f"@{username} уже состоит в сети взаимного продвижения.")
        elif previous_status == "paused":
            await message.reply_text(
                f"@{username} уже зарегистрирован, но сейчас приостановлен владельцем сети."
            )
        else:
            await message.reply_text(
                f"Заявка принята: {target.title} (@{username}), подписчиков: {member_count}.\n"
                f"ID заявки: {channel_id}. После проверки администратор сети одобрит её."
            )
        log.info("Cross-promo channel submitted chat_id=%s by user_id=%s", target.id, user.id)
    except (BadRequest, Forbidden) as exc:
        log.warning("Cross-promo registration rejected: %s", exc)
        await message.reply_text(
            "Telegram не дал проверить канал. Убедись, что ссылка публичная, "
            "ты администратор, а наш бот имеет доступ к каналу."
        )
    except TelegramError:
        log.exception("Cross-promo registration Telegram error")
        await message.reply_text("Telegram вернул ошибку при проверке. Попробуй позже.")


async def pending_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return
    if not await _is_main_admin(update, context):
        await message.reply_text("Только администратор CryptoPing RU может просматривать заявки.")
        return
    rows = pending_channels()
    if not rows:
        await message.reply_text("Очередь заявок пуста.")
        return
    lines = ["Заявки на взаимное продвижение:"]
    for row in rows:
        lines.append(
            f"ID {row['id']}: {row['title']} (@{row['username']}) — "
            f"{row['member_count']} подписчиков. Одобрить: /crosspromoapprove {row['id']}"
        )
    await message.reply_text("\n".join(lines)[:4000])


async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return
    if not await _is_main_admin(update, context):
        await message.reply_text("Только администратор CryptoPing RU может одобрять каналы.")
        return
    if len(context.args) != 1 or not context.args[0].isdigit():
        await message.reply_text("Использование: /crosspromoapprove ID")
        return
    channel_id = int(context.args[0])
    row = get_channel_by_id(channel_id)
    if not row or not approve_channel(channel_id, update.effective_user.id if update.effective_user else 0):
        await message.reply_text("Заявка не найдена или уже обработана.")
        return
    await message.reply_text(
        f"Одобрено: {row['title']} (@{row['username']}). "
        "Канал участвует во взаимном продвижении по очереди."
    )
    try:
        await context.bot.send_message(
            chat_id=int(row["owner_user_id"]),
            text=f"Твой канал @{row['username']} одобрен для взаимного продвижения CryptoPing RU.",
        )
    except TelegramError:
        pass


async def reject_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return
    if not await _is_main_admin(update, context):
        await message.reply_text("Только администратор CryptoPing RU может отклонять каналы.")
        return
    if len(context.args) != 1 or not context.args[0].isdigit():
        await message.reply_text("Использование: /crosspromoreject ID")
        return
    row = get_channel_by_id(int(context.args[0]))
    if not row or not reject_channel(int(context.args[0])):
        await message.reply_text("Ожидающая заявка не найдена.")
        return
    await message.reply_text(f"Заявка @{row['username']} отклонена.")


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return
    if not await _is_main_admin(update, context):
        await message.reply_text("Только администратор CryptoPing RU может просматривать сеть.")
        return
    rows = active_channels()
    if not rows:
        await message.reply_text("Активных каналов пока нет.")
        return
    lines = [f"Активных каналов в сети: {len(rows)}", ""]
    for row in rows[:45]:
        label = f"@{row['username']}" if row["username"] else row["title"]
        last = row["last_promo_at"] or "пока не публиковался"
        lines.append(f"ID {row['id']}: {label} · {row['member_count']} подписчиков · {last}")
    await message.reply_text("\n".join(lines)[:4000])


async def pause_home_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return
    if not await _is_main_admin(update, context):
        await message.reply_text("Только администратор CryptoPing RU может приостанавливать участие.")
        return
    try:
        home = await context.bot.get_chat(CHAT_ID)
        existing = get_channel(home.id)
        if existing is None:
            await message.reply_text("Канал ещё не внесён в сеть. Нечего приостанавливать.")
            return
        set_channel_status(home.id, "paused")
        await message.reply_text(
            "Участие @cryptoping_ru приостановлено: новые промо в канал не публикуются, "
            "и сам канал не предлагается партнёрам."
        )
    except TelegramError:
        log.exception("Could not pause home cross-promo channel")


async def resume_home_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return
    if not await _is_main_admin(update, context):
        await message.reply_text("Только администратор CryptoPing RU может возобновлять участие.")
        return
    try:
        home = await context.bot.get_chat(CHAT_ID)
        bot_user = await context.bot.get_me()
        bot_member = await context.bot.get_chat_member(home.id, bot_user.id)
        if bot_member.status not in ("administrator", "creator") or (
            bot_member.status != "creator" and not getattr(bot_member, "can_post_messages", False)
        ):
            await message.reply_text("У бота нет прав публикации в @cryptoping_ru.")
            return
        count = await context.bot.get_chat_member_count(home.id)
        ensure_home_channel(home.id, home.title or "CryptoPing RU", home.username or "cryptoping_ru", count)
        set_channel_status(home.id, "active")
        await message.reply_text("Участие @cryptoping_ru возобновлено.")
    except TelegramError:
        log.exception("Could not resume home cross-promo channel")
        await message.reply_text("Не удалось проверить права публикации в @cryptoping_ru.")


async def run_cross_promotion(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Publish one reciprocal promo per opted-in target when its cooldown expires."""
    try:
        home = await context.bot.get_chat(CHAT_ID)
        bot_user = await context.bot.get_me()
        home_member = await context.bot.get_chat_member(home.id, bot_user.id)
        if home_member.status not in ("administrator", "creator") or (
            home_member.status != "creator" and not getattr(home_member, "can_post_messages", False)
        ):
            log.warning("Cross-promo paused: bot lacks post permission in configured home channel")
            return
        home_count = await context.bot.get_chat_member_count(home.id)
        home_row = ensure_home_channel(
            home.id, home.title or "CryptoPing RU",
            home.username or "cryptoping_ru", home_count,
        )
        if home_row["status"] != "active":
            return
    except TelegramError:
        log.exception("Cross-promo could not verify the configured home channel")
        return

    interval = int(getattr(config, "CROSSPROMO_INTERVAL_HOURS", DEFAULT_INTERVAL_HOURS))
    targets = due_targets(interval)
    for target in targets:
        promoted = select_candidate(int(target["chat_id"]))
        if not promoted:
            continue
        link = promoted.get("username")
        if int(promoted["chat_id"]) == int(home.id) and target.get("home_invite_link"):
            destination = str(target["home_invite_link"])
        elif link:
            destination = f"https://t.me/{link}"
        else:
            log.warning("Cross-promo skipped channel without public username: %s", promoted["chat_id"])
            continue

        text = (
            f"🤝 Взаимное продвижение каналов\\n\\n"
            f"📣 {promoted['title']}\\n"
            f"👥 Подписчиков: {int(promoted['member_count'])}\\n"
            f"🔗 {destination}\\n\\n"
            "Публикация размещена в рамках согласованной сети взаимного продвижения."
        )
        try:
            sent = await context.bot.send_message(
                chat_id=int(target["chat_id"]),
                text=text,
                disable_web_page_preview=True,
            )
            mark_delivery(int(target["chat_id"]), int(promoted["chat_id"]), sent.message_id)
            log.info(
                "Cross-promo delivered target=%s promoted=%s message_id=%s",
                target["chat_id"], promoted["chat_id"], sent.message_id,
            )
        except RetryAfter as exc:
            mark_delivery_failed(int(target["chat_id"]), exc, disable=False)
            await asyncio.sleep(float(exc.retry_after))
        except (Forbidden, BadRequest) as exc:
            mark_delivery_failed(int(target["chat_id"]), exc, disable=True)
            log.warning(
                "Cross-promo target disabled after Telegram rejected post target=%s error=%s",
                target["chat_id"], exc,
            )
        except TelegramError as exc:
            mark_delivery_failed(int(target["chat_id"]), exc, disable=False)
            log.warning("Cross-promo temporary failure target=%s error=%s", target["chat_id"], exc)
        await asyncio.sleep(1.2)


def register_handlers(app: Application) -> None:
    """Register cross-promotion commands and the scheduler on the existing app."""
    init_db()
    app.add_handler(CommandHandler("crosspromo", help_command))
    app.add_handler(CommandHandler("crosspromo_add", add_channel_command))
    app.add_handler(CommandHandler("crosspromopending", pending_command))
    app.add_handler(CommandHandler("crosspromoapprove", approve_command))
    app.add_handler(CommandHandler("crosspromoreject", reject_command))
    app.add_handler(CommandHandler("crosspromolist", list_command))
    app.add_handler(CommandHandler("crosspromopause", pause_home_command))
    app.add_handler(CommandHandler("crosspromoresume", resume_home_command))

    if app.job_queue is None:
        raise RuntimeError(
            "JobQueue is unavailable; install requirements.txt with python-telegram-bot[job-queue]."
        )
    app.job_queue.run_repeating(
        run_cross_promotion,
        interval=5 * 60,
        first=45,
        name="cross-promotion-network",
        job_kwargs={"max_instances": 1, "coalesce": True},
    )
    log.info("Cross-promotion scheduler registered")
