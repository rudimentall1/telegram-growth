"""Permission-checked Telegram delivery for explicitly approved Publisher drafts."""
import asyncio

from telegram.error import NetworkError, RetryAfter, TelegramError, TimedOut

from config import CHAT_ID

from .moderator import can_auto_publish, configured_model, moderate_source_post
from .policy import evaluate_target
from .service import PublisherService
from .storage import PublisherStore
from .trial_targets import TRIAL_EXTERNAL_GROUPS


MAX_TELEGRAM_TEXT_LENGTH = 4096
MAX_BATCH_TARGETS = 20


async def publish_draft_to_target(bot, store, draft_id, target_id, community_chat_id=None, min_interval_days=0, referral_chat_id=None):
    draft = store.get_draft(draft_id)
    if not draft:
        raise LookupError("draft not found")
    if draft["status"] != "approved":
        raise ValueError("draft must be approved before publication")

    target = store.get_target(target_id)
    if not target:
        raise LookupError("target not found")

    existing = store.get_delivery(draft_id, target_id)
    if existing and existing["status"] in ("sent", "unknown", "sending"):
        return {
            "status": existing["status"],
            "reason": "existing delivery blocks duplicate send",
            "message_url": existing.get("message_url"),
        }

    eligible, reason = evaluate_target(target, min_interval_days=min_interval_days)
    if not eligible:
        return {"status": "skipped", "reason": reason}

    body = (draft.get("body") or "").strip()
    if not body:
        raise ValueError("draft body is empty")
    # A unique, persistent invite to our own community is appended per approved target.
    # No invite is created for pending/rejected targets because policy is checked above.
    if community_chat_id is not None and referral_chat_id is not None:
        raise ValueError("choose either a community invite or a channel referral invite")
    if community_chat_id is not None:
        invite_link = store.get_target_invite(target_id)
        if not invite_link:
            invite = await bot.create_chat_invite_link(
                chat_id=community_chat_id,
                name=f"cp-pub-{draft_id}-{target_id}"[:32],
                creates_join_request=False,
            )
            invite_link, _ = store.get_or_create_target_invite(
                target_id, invite.invite_link
            )
        body = f"{body.rstrip()}\n\nНаше сообщество: {invite_link}"
    if referral_chat_id is not None:
        referral_link = store.get_target_referral_link(target_id)
        if not referral_link:
            try:
                invite = await bot.create_chat_invite_link(
                    chat_id=referral_chat_id,
                    name=f"cp-ref-{draft_id}-{target_id}"[:32],
                    creates_join_request=False,
                )
                candidate_link = invite.invite_link
            except TelegramError:
                # The public channel URL remains a safe fallback if invite-link
                # creation is unavailable; never let attribution break delivery.
                public_name = str(referral_chat_id).strip().lstrip("@")
                if not public_name or public_name.startswith("-"):
                    raise
                candidate_link = f"https://t.me/{public_name}"
            referral_link, _ = store.get_or_create_target_referral_link(
                target_id, candidate_link
            )
        body = f"{body.rstrip()}\n\nCryptoPing RU: {referral_link}"
    if len(body) > MAX_TELEGRAM_TEXT_LENGTH:
        raise ValueError("draft plus community invite exceeds Telegram's 4096-character text limit")

    # Check the live destination and bot permissions before claiming a delivery.
    chat = await bot.get_chat(target["handle"])
    chat_type = getattr(chat, "type", None)
    if chat_type not in ("group", "supergroup", "channel"):
        raise PermissionError("destination is not a Telegram group or channel")
    if target["kind"] == "channel" and chat_type != "channel":
        raise PermissionError("registered target kind does not match Telegram destination")
    if target["kind"] == "group" and chat_type not in ("group", "supergroup"):
        raise PermissionError("registered target kind does not match Telegram destination")

    bot_user = await bot.get_me()
    membership = await bot.get_chat_member(chat.id, bot_user.id)
    status = getattr(membership, "status", None)

    if target["kind"] == "channel":
        if status not in ("administrator", "creator"):
            raise PermissionError("bot must be a channel administrator to publish")
        if status != "creator" and not bool(getattr(membership, "can_post_messages", False)):
            raise PermissionError("bot administrator lacks can_post_messages")
    else:
        # In groups, an ordinary bot member is sufficient when Telegram's live
        # group permissions allow messages. No administrator promotion needed.
        if status in ("administrator", "creator"):
            if status != "creator" and getattr(membership, "can_send_messages", True) is False:
                raise PermissionError("bot administrator cannot send messages in this group")
        elif status == "member":
            permissions = getattr(chat, "permissions", None)
            if permissions is None or getattr(permissions, "can_send_messages", None) is not True:
                raise PermissionError("group does not expose explicit permission for members to send messages")
        elif status == "restricted":
            permissions = getattr(membership, "permissions", None)
            if not bool(getattr(membership, "is_member", False)) or (
                permissions is None or getattr(permissions, "can_send_messages", None) is not True
            ):
                raise PermissionError("bot is restricted or cannot send messages in this group")
        else:
            raise PermissionError("bot is not a permitted member of this group")

    if not store.claim_delivery(draft_id, target_id):
        existing = store.get_delivery(draft_id, target_id) or {}
        return {
            "status": existing.get("status", "in_progress"),
            "reason": "existing delivery blocks duplicate send",
            "message_url": existing.get("message_url"),
        }

    try:
        sent = await bot.send_message(
            chat_id=chat.id,
            text=body,
            disable_web_page_preview=True,
        )
    except (TimedOut, NetworkError) as exc:
        store.mark_delivery_unknown(draft_id, target_id, exc)
        return {
            "status": "unknown",
            "reason": "network outcome is ambiguous; automatic retry is blocked",
        }
    except TelegramError as exc:
        store.mark_delivery_failed(draft_id, target_id, exc)
        return {"status": "failed", "reason": str(exc)[:300]}
    except Exception as exc:
        store.mark_delivery_unknown(draft_id, target_id, exc)
        return {
            "status": "unknown",
            "reason": "unexpected error after send attempt; retry is blocked",
        }

    username = getattr(chat, "username", None)
    message_url = f"https://t.me/{username}/{sent.message_id}" if username else None
    store.mark_delivery_sent(
        draft_id=draft_id,
        target_id=target_id,
        chat_id=chat.id,
        message_id=sent.message_id,
        message_url=message_url,
    )
    return {
        "status": "sent",
        "message_id": sent.message_id,
        "message_url": message_url,
    }


async def publish_draft_to_eligible_targets(
    bot, store, draft_id, delay_seconds=1.2, max_targets=MAX_BATCH_TARGETS,
    after_target_id=0, community_chat_id=None,
):
    """Publish sequentially to a bounded batch and return a stable continuation cursor."""
    if max_targets < 1:
        raise ValueError("max_targets must be at least 1")
    draft, plan = PublisherService(store).build_plan(draft_id)
    results = []
    attempts = 0
    last_processed_id = after_target_id
    remaining = [item for item in plan if item.target_id > after_target_id]

    for item in remaining:
        if not item.eligible:
            results.append({
                "target_id": item.target_id,
                "handle": item.handle,
                "status": "skipped",
                "reason": item.reason,
            })
            last_processed_id = item.target_id
            continue
        if attempts >= max_targets:
            results.append({
                "target_id": item.target_id,
                "handle": item.handle,
                "status": "deferred",
                "reason": "batch limit reached; continue from the last processed target ID",
            })
            continue

        try:
            result = await publish_draft_to_target(
                bot, store, draft_id, item.target_id,
                community_chat_id=community_chat_id,
            )
        except (PermissionError, TelegramError, LookupError, ValueError) as exc:
            result = {"status": "blocked", "reason": str(exc)[:300]}
        results.append({
            "target_id": item.target_id,
            "handle": item.handle,
            **result,
        })
        attempts += 1
        last_processed_id = item.target_id
        if delay_seconds > 0 and attempts < max_targets:
            await asyncio.sleep(delay_seconds)
    return draft, results, last_processed_id



async def publish_captured_source_posts(bot, store, target_id, limit=3):
    """LLM-moderate captured own-channel posts before publishing to our community."""
    outcomes = []
    for source in store.list_unprocessed_source_posts(limit=limit):
        draft_id = source["draft_id"]
        body = (source.get("body") or "").strip()
        title = (source.get("title") or "").strip()

        # Deterministic gates run before any model call.
        rule_reason = None
        if not body:
            rule_reason = "source post is empty"
        elif len(body) > MAX_TELEGRAM_TEXT_LENGTH:
            rule_reason = "source post exceeds Telegram's text limit"
        elif body.startswith("/"):
            rule_reason = "bot commands are never reposted"

        if rule_reason:
            store.record_moderation_review(draft_id, {
                "provider": "rules",
                "model": "publisher-rules-v1",
                "decision": "hold",
                "confidence": 1.0,
                "category": "other",
                "reason": rule_reason,
            })
            outcomes.append({"draft_id": draft_id, "status": "held", "reason": rule_reason})
            continue

        try:
            review = await moderate_source_post(title, body)
        except Exception as exc:
            reason = str(exc).strip()[:240] or type(exc).__name__
            store.record_moderation_review(draft_id, {
                "provider": "openai",
                "model": configured_model(),
                "decision": "error",
                "category": "other",
                "reason": reason,
            })
            outcomes.append({"draft_id": draft_id, "status": "error", "reason": reason})
            continue

        if not can_auto_publish(review):
            decision = review.get("decision")
            if decision == "allow":
                decision = "hold"
                reason = (
                    f"{review.get('reason', 'Model review did not meet the auto-publish policy')} "
                    "(automatic publication threshold not met)"
                )
            else:
                decision = decision if decision in ("hold", "block") else "hold"
                reason = review.get("reason") or "Model did not explicitly approve this post"
            review_to_store = {
                **review,
                "decision": decision,
                "reason": reason[:400],
            }
            store.record_moderation_review(draft_id, review_to_store)
            outcomes.append({
                "draft_id": draft_id,
                "status": "blocked" if decision == "block" else "held",
                "reason": reason[:240],
                "confidence": review.get("confidence"),
                "category": review.get("category"),
            })
            continue

        store.record_moderation_review(draft_id, review)
        try:
            store.approve_draft(draft_id)
            result = await publish_draft_to_target(
                bot, store, draft_id, target_id,
                referral_chat_id=CHAT_ID,
                min_interval_days=0,
            )
            external_results = []
            if result.get("status") == "sent":
                # Publish to every group where Telegram has confirmed bot
                # membership. Live send permission is checked for each target.
                from .policy import evaluate_target
                candidates = [
                    row for row in store.list_targets()
                    if row["kind"] == "group"
                    and row["id"] != target_id
                    and row["handle"].lower() in TRIAL_EXTERNAL_GROUPS
                    and evaluate_target(row, min_interval_days=0)[0]
                ]
                candidates.sort(key=lambda row: row["id"])
                for candidate in candidates:
                    try:
                        delivery = await publish_draft_to_target(
                            bot, store, draft_id, candidate["id"],
                            referral_chat_id=CHAT_ID,
                            min_interval_days=0,
                        )
                        external_results.append({
                            "target_id": candidate["id"],
                            "handle": candidate["handle"],
                            **delivery,
                        })
                    except (PermissionError, TelegramError, LookupError, ValueError) as exc:
                        external_results.append({
                            "target_id": candidate["id"],
                            "handle": candidate["handle"],
                            "status": "blocked",
                            "reason": str(exc)[:240],
                        })
                        # Telegram's own flood-control response is authoritative:
                        # stop this batch rather than retrying against more groups.
                        if isinstance(exc, RetryAfter):
                            break
            outcomes.append({
                "draft_id": draft_id,
                "moderation": "allow",
                "confidence": review.get("confidence"),
                **result,
                "external": external_results if result.get("status") == "sent" else [],
            })
        except Exception as exc:
            outcomes.append({"draft_id": draft_id, "status": "error", "reason": str(exc)[:240]})
    return outcomes



async def publish_pending_external_drafts(bot, store, owned_target_id, limit=5):
    """Retry external delivery for news already published to the owned group."""
    pending = store.list_pending_external_drafts(
        owned_target_id, TRIAL_EXTERNAL_GROUPS, limit=limit
    )
    if not pending:
        return []

    from .policy import evaluate_target

    targets = [
        row for row in store.list_targets()
        if row["kind"] == "group"
        and row["handle"].lower() in TRIAL_EXTERNAL_GROUPS
        and evaluate_target(row, min_interval_days=0)[0]
    ]
    targets.sort(key=lambda row: row["id"])
    if not targets:
        return [
            {"draft_id": item["draft_id"], "status": "waiting_for_trial_membership"}
            for item in pending
        ]

    results = []
    for item in pending:
        for target in targets:
            try:
                delivery = await publish_draft_to_target(
                    bot, store, item["draft_id"], target["id"],
                    referral_chat_id=CHAT_ID,
                    min_interval_days=0,
                )
                results.append({
                    "draft_id": item["draft_id"],
                    "handle": target["handle"],
                    **delivery,
                })
                if delivery.get("status") == "sent":
                    await asyncio.sleep(1.2)
            except (PermissionError, TelegramError, LookupError, ValueError) as exc:
                results.append({
                    "draft_id": item["draft_id"],
                    "handle": target["handle"],
                    "status": "blocked",
                    "reason": str(exc)[:240],
                })
                if isinstance(exc, RetryAfter):
                    return results
    return results


def register_handlers(app, admin_check, community_chat_id=None):
    """Register Publisher operator commands on the existing Telegram application."""

    async def require_admin(update, context):
        if not await admin_check(update, context):
            await update.effective_message.reply_text("Administrator access required.")
            return False
        return True

    async def pub_help(update, context):
        if not await require_admin(update, context):
            return
        await update.effective_message.reply_text(
            "Publisher commands (administrators only):\n"
            "/pubtargets - show registered destinations\n"
            "/pubdraft Title | message text - create a draft\n"
            "/pubsources - show latest posts captured from our news channel\n"
            "New posts from our own channel are checked by the AI moderator; only high-confidence informational posts are auto-published. Unclear posts are held.\n"
            "External destinations remain blocked until their permission is verified.\n"
            "/pubapprove DRAFT_ID - approve a draft\n"
            "/pubreview TARGET_ID allow | evidence\n"
            "/pubreview TARGET_ID reject | reason\n"
            "/pubplan DRAFT_ID - preview eligible destinations\n"
            "/pubsend DRAFT_ID TARGET_ID - publish to one destination\n"
            "/pubsendall DRAFT_ID [AFTER_TARGET_ID] - publish a batch and continue\n"
            "/pubdelivery DRAFT_ID TARGET_ID - inspect delivery state"
        )

    async def pub_targets(update, context):
        if not await require_admin(update, context):
            return
        rows = PublisherStore().list_targets()
        if not rows:
            await update.effective_message.reply_text("No destinations registered.")
            return
        lines = [
            f"#{row['id']} {row.get('display_name') or row['handle']} "
            f"[{row['kind']}] {row['status']}/{row['promotion_policy']}"
            for row in rows[:50]
        ]
        await update.effective_message.reply_text("\n".join(lines))

    async def pub_draft(update, context):
        if not await require_admin(update, context):
            return
        raw = update.effective_message.text.partition(" ")[2]
        if "|" not in raw:
            await update.effective_message.reply_text(
                "Format: /pubdraft Title | publication text"
            )
            return
        title, body = (part.strip() for part in raw.split("|", 1))
        try:
            draft_id = PublisherStore().add_draft(title, body)
        except ValueError as exc:
            await update.effective_message.reply_text(str(exc))
            return
        await update.effective_message.reply_text(
            f"Draft #{draft_id} created. Approve it with /pubapprove {draft_id}."
        )

    async def pub_sources(update, context):
        if not await require_admin(update, context):
            return
        rows = PublisherStore().list_source_posts(10)
        if not rows:
            await update.effective_message.reply_text("Пока нет новых текстовых постов из канала.")
            return
        lines = ["Последние посты канала и статус автоматической публикации:"]
        for row in rows:
            source = row.get("source_url") or f"message {row['source_message_id']}"
            moderation = row.get("moderation_decision") or "pending"
            confidence = row.get("moderation_confidence")
            score = f" ({confidence:.2f})" if confidence is not None else ""
            reason = (row.get("moderation_reason") or "")[:160]
            lines.append(
                f"Draft #{row['draft_id']} [{row['draft_status']}] {row['title']}\n{source}\n"
                f"AI moderator: {moderation}{score} {reason}"
            )
        await update.effective_message.reply_text("\n\n".join(lines)[:4000])

    async def pub_approve(update, context):
        if not await require_admin(update, context):
            return
        try:
            if len(context.args) != 1:
                raise ValueError("Format: /pubapprove DRAFT_ID")
            draft_id = int(context.args[0])
            PublisherStore().approve_draft(draft_id)
        except (ValueError, LookupError) as exc:
            await update.effective_message.reply_text(str(exc))
            return
        await update.effective_message.reply_text(f"Draft #{draft_id} approved.")

    async def pub_review(update, context):
        if not await require_admin(update, context):
            return
        raw = update.effective_message.text.partition(" ")[2]
        head, separator, evidence = raw.partition("|")
        parts = head.split()
        if len(parts) != 2 or not separator or not evidence.strip():
            await update.effective_message.reply_text(
                "Format: /pubreview TARGET_ID allow|reject | evidence"
            )
            return
        try:
            target_id = int(parts[0])
            decision = parts[1].lower()
            if decision == "allow":
                PublisherStore().review_target(
                    target_id, "approve", "allowed", evidence.strip()
                )
            elif decision == "reject":
                PublisherStore().review_target(
                    target_id, "reject", "prohibited", evidence.strip()
                )
            else:
                raise ValueError("decision must be allow or reject")
        except (ValueError, LookupError) as exc:
            await update.effective_message.reply_text(str(exc))
            return
        await update.effective_message.reply_text(
            f"Target #{target_id} review recorded: {decision}."
        )

    async def pub_plan(update, context):
        if not await require_admin(update, context):
            return
        try:
            if len(context.args) != 1:
                raise ValueError("Format: /pubplan DRAFT_ID")
            draft, items = PublisherService(PublisherStore()).build_plan(
                int(context.args[0])
            )
        except (ValueError, LookupError) as exc:
            await update.effective_message.reply_text(str(exc))
            return
        lines = [f"Plan for draft #{draft['id']} ({draft['title']}):"]
        for item in items[:40]:
            state = "ELIGIBLE" if item.eligible else "SKIP"
            lines.append(f"{state}: {item.handle} - {item.reason}")
        await update.effective_message.reply_text("\n".join(lines)[:4000])

    async def pub_send(update, context):
        if not await require_admin(update, context):
            return
        try:
            if len(context.args) != 2:
                raise ValueError("Format: /pubsend DRAFT_ID TARGET_ID")
            result = await publish_draft_to_target(
                context.bot, PublisherStore(),
                int(context.args[0]), int(context.args[1]),
                community_chat_id=community_chat_id,
            )
        except (ValueError, LookupError, PermissionError, TelegramError) as exc:
            await update.effective_message.reply_text(
                f"Publication blocked: {str(exc)[:500]}"
            )
            return
        details = result.get("message_url") or result.get("reason") or ""
        await update.effective_message.reply_text(
            f"Status: {result['status']}. {details}"[:1000]
        )

    async def pub_send_all(update, context):
        if not await require_admin(update, context):
            return
        try:
            if len(context.args) not in (1, 2):
                raise ValueError("Format: /pubsendall DRAFT_ID [AFTER_TARGET_ID]")
            after_target_id = int(context.args[1]) if len(context.args) == 2 else 0
            draft, results, last_processed_id = await publish_draft_to_eligible_targets(
                context.bot, PublisherStore(), int(context.args[0]),
                after_target_id=after_target_id,
                community_chat_id=community_chat_id,
            )
        except (ValueError, LookupError) as exc:
            await update.effective_message.reply_text(str(exc))
            return
        sent = sum(row["status"] == "sent" for row in results)
        skipped = sum(row["status"] == "skipped" for row in results)
        blocked = sum(row["status"] == "blocked" for row in results)
        deferred = sum(row["status"] == "deferred" for row in results)
        failed = sum(row["status"] in ("failed", "unknown") for row in results)
        lines = [
            f"Campaign #{draft['id']}: sent={sent}, skipped={skipped}, "
            f"blocked={blocked}, deferred={deferred}, failed/unknown={failed}."
        ]
        for row in results:
            lines.append(
                f"{row['handle']}: {row['status']} {row.get('reason', '')}"
            )
        if deferred:
            lines.append(
                f"Continue with: /pubsendall {draft['id']} {last_processed_id}"
            )
        await update.effective_message.reply_text("\n".join(lines)[:4000])

    async def pub_delivery(update, context):
        if not await require_admin(update, context):
            return
        try:
            if len(context.args) != 2:
                raise ValueError("Format: /pubdelivery DRAFT_ID TARGET_ID")
            row = PublisherStore().get_delivery(
                int(context.args[0]), int(context.args[1])
            )
        except ValueError as exc:
            await update.effective_message.reply_text(str(exc))
            return
        if not row:
            await update.effective_message.reply_text("No delivery record found.")
            return
        await update.effective_message.reply_text(
            f"Status: {row['status']}\nAttempts: {row['attempt_count']}\n"
            f"Message: {row.get('message_url') or row.get('telegram_message_id') or '-'}\n"
            f"Error: {row.get('error') or '-'}"
        )

    from telegram.ext import CommandHandler

    app.add_handler(CommandHandler("pubhelp", pub_help))
    app.add_handler(CommandHandler("pubtargets", pub_targets))
    app.add_handler(CommandHandler("pubdraft", pub_draft))
    app.add_handler(CommandHandler("pubsources", pub_sources))
    app.add_handler(CommandHandler("pubapprove", pub_approve))
    app.add_handler(CommandHandler("pubreview", pub_review))
    app.add_handler(CommandHandler("pubplan", pub_plan))
    app.add_handler(CommandHandler("pubsend", pub_send))
    app.add_handler(CommandHandler("pubsendall", pub_send_all))
    app.add_handler(CommandHandler("pubdelivery", pub_delivery))

