import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from telegram.error import Forbidden, NetworkError

from publisher.storage import PublisherStore
from publisher.telegram import publish_draft_to_target


class PublisherTelegramTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = PublisherStore(str(Path(self.temp.name) / "publisher.db"))
        self.target_id = self.store.add_target("channel", "@sample_channel")
        self.store.review_target(
            self.target_id, "approve", "allowed",
            "Moderator rules explicitly allow one relevant promotional post",
        )
        self.draft_id = self.store.add_draft("CryptoPing", "Useful crypto news digest.")
        self.store.approve_draft(self.draft_id)
        self.bot = SimpleNamespace(
            get_chat=AsyncMock(return_value=SimpleNamespace(
                id=-100123456789, type="channel", username="sample_channel"
            )),
            get_me=AsyncMock(return_value=SimpleNamespace(id=777)),
            get_chat_member=AsyncMock(return_value=SimpleNamespace(
                status="administrator", can_post_messages=True
            )),
            send_message=AsyncMock(return_value=SimpleNamespace(message_id=99)),
        )

    def tearDown(self):
        self.temp.cleanup()

    async def test_send_checks_rights_and_records_publication_once(self):
        first = await publish_draft_to_target(
            self.bot, self.store, self.draft_id, self.target_id
        )
        self.assertEqual(first["status"], "sent")
        self.assertEqual(first["message_url"], "https://t.me/sample_channel/99")
        self.bot.get_chat_member.assert_awaited_once_with(-100123456789, 777)
        self.bot.send_message.assert_awaited_once_with(
            chat_id=-100123456789,
            text="Useful crypto news digest.",
            disable_web_page_preview=True,
        )
        delivery = self.store.get_delivery(self.draft_id, self.target_id)
        self.assertEqual(delivery["status"], "sent")
        self.assertEqual(delivery["telegram_message_id"], 99)
        self.assertIsNotNone(self.store.get_target(self.target_id)["last_posted_at"])

        second = await publish_draft_to_target(
            self.bot, self.store, self.draft_id, self.target_id
        )
        self.assertEqual(second["status"], "sent")
        self.bot.send_message.assert_awaited_once()

    async def test_publication_appends_and_reuses_target_specific_community_invite(self):
        self.bot.create_chat_invite_link = AsyncMock(return_value=SimpleNamespace(
            invite_link="https://t.me/+trackedInvite"
        ))
        first = await publish_draft_to_target(
            self.bot, self.store, self.draft_id, self.target_id,
            community_chat_id=-1004298750600,
        )
        self.assertEqual(first["status"], "sent")
        self.bot.create_chat_invite_link.assert_awaited_once_with(
            chat_id=-1004298750600,
            name=f"cp-pub-{self.draft_id}-{self.target_id}",
            creates_join_request=False,
        )
        sent_text = self.bot.send_message.await_args.kwargs["text"]
        self.assertIn("Наше сообщество: https://t.me/+trackedInvite", sent_text)
        self.assertEqual(self.store.get_target_invite(self.target_id), "https://t.me/+trackedInvite")

    async def test_non_admin_bot_is_rejected_before_delivery_claim(self):
        self.bot.get_chat_member.return_value = SimpleNamespace(status="member")
        with self.assertRaises(PermissionError):
            await publish_draft_to_target(
                self.bot, self.store, self.draft_id, self.target_id
            )
        self.assertIsNone(self.store.get_delivery(self.draft_id, self.target_id))
        self.bot.send_message.assert_not_awaited()

    async def test_channel_without_post_permission_is_rejected(self):
        self.bot.get_chat_member.return_value = SimpleNamespace(
            status="administrator", can_post_messages=False
        )
        with self.assertRaises(PermissionError):
            await publish_draft_to_target(
                self.bot, self.store, self.draft_id, self.target_id
            )
        self.bot.send_message.assert_not_awaited()

    async def test_target_kind_must_match_actual_chat_type(self):
        self.bot.get_chat.return_value = SimpleNamespace(
            id=-100123456789, type="supergroup", username="sample_channel"
        )
        with self.assertRaises(PermissionError):
            await publish_draft_to_target(
                self.bot, self.store, self.draft_id, self.target_id
            )
        self.bot.send_message.assert_not_awaited()

    async def test_stale_permission_is_skipped_without_telegram_call(self):
        old = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        with self.store.connect() as db:
            db.execute(
                "UPDATE targets SET reviewed_at=? WHERE id=?",
                (old, self.target_id),
            )
        result = await publish_draft_to_target(
            self.bot, self.store, self.draft_id, self.target_id
        )
        self.assertEqual(result["status"], "skipped")
        self.bot.get_chat.assert_not_awaited()
        self.bot.send_message.assert_not_awaited()

    async def test_network_error_becomes_unknown_and_is_never_retried(self):
        self.bot.send_message.side_effect = NetworkError("connection lost")
        first = await publish_draft_to_target(
            self.bot, self.store, self.draft_id, self.target_id
        )
        self.assertEqual(first["status"], "unknown")
        second = await publish_draft_to_target(
            self.bot, self.store, self.draft_id, self.target_id
        )
        self.assertEqual(second["status"], "unknown")
        self.bot.send_message.assert_awaited_once()
        self.assertEqual(
            self.store.get_delivery(self.draft_id, self.target_id)["status"],
            "unknown",
        )

    async def test_definitive_telegram_failure_can_be_retried_manually(self):
        self.bot.send_message.side_effect = [Forbidden("posting forbidden"), SimpleNamespace(message_id=100)]
        first = await publish_draft_to_target(
            self.bot, self.store, self.draft_id, self.target_id
        )
        self.assertEqual(first["status"], "failed")
        second = await publish_draft_to_target(
            self.bot, self.store, self.draft_id, self.target_id
        )
        self.assertEqual(second["status"], "sent")
        self.assertEqual(
            self.store.get_delivery(self.draft_id, self.target_id)["attempt_count"],
            2,
        )

    async def test_unapproved_draft_cannot_be_sent(self):
        draft_id = self.store.add_draft("Not approved", "Do not publish.")
        with self.assertRaises(ValueError):
            await publish_draft_to_target(
                self.bot, self.store, draft_id, self.target_id
            )
        self.bot.send_message.assert_not_awaited()

    async def test_oversized_draft_is_rejected(self):
        draft_id = self.store.add_draft("Too long", "x" * 4097)
        self.store.approve_draft(draft_id)
        with self.assertRaises(ValueError):
            await publish_draft_to_target(
                self.bot, self.store, draft_id, self.target_id
            )
        self.bot.send_message.assert_not_awaited()


    async def test_batch_sends_only_reviewed_targets(self):
        from publisher.telegram import publish_draft_to_eligible_targets

        second_id = self.store.add_target("channel", "@second_channel")
        self.store.review_target(
            second_id, "approve", "allowed",
            "Moderator explicitly approved one promotional post",
        )
        pending_id = self.store.add_target("group", "@pending_group")

        self.bot.get_chat.side_effect = [
            SimpleNamespace(id=-100123456789, type="channel", username="sample_channel"),
            SimpleNamespace(id=-100987654321, type="channel", username="second_channel"),
        ]
        self.bot.get_chat_member.side_effect = [
            SimpleNamespace(status="administrator", can_post_messages=True),
            SimpleNamespace(status="administrator", can_post_messages=True),
        ]
        self.bot.send_message.side_effect = [
            SimpleNamespace(message_id=101),
            SimpleNamespace(message_id=102),
        ]

        draft, results, _ = await publish_draft_to_eligible_targets(
            self.bot, self.store, self.draft_id, delay_seconds=0
        )
        self.assertEqual(draft["id"], self.draft_id)
        self.assertEqual([row["target_id"] for row in results], [self.target_id, second_id, pending_id])
        self.assertEqual([row["status"] for row in results], ["sent", "sent", "skipped"])
        self.assertIsNone(self.store.get_delivery(self.draft_id, pending_id))
        self.assertEqual(self.bot.send_message.await_count, 2)


    async def test_autonomous_source_pipeline_approves_and_publishes_only_captured_source_posts(self):
        from publisher.telegram import publish_captured_source_posts
        source_draft = self.store.capture_source_post(
            -100111, 55, "Own channel news", "Fresh crypto market update from our own channel.",
            "https://t.me/cryptoping_ru/55",
        )[0]
        manual_draft = self.store.add_draft("Manual draft", "Must remain unapproved.")
        review = {
            "provider": "openai", "model": "gpt-6-luna",
            "decision": "allow", "confidence": 0.97, "category": "news",
            "reason": "Relevant informational market update.",
            "flags": [], "raw_response": '{"decision":"allow"}',
        }
        with patch("publisher.telegram.moderate_source_post", new=AsyncMock(return_value=review)):
            result = await publish_captured_source_posts(
                self.bot, self.store, self.target_id, limit=10
            )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["draft_id"], source_draft)
        self.assertEqual(result[0]["status"], "sent")
        self.assertEqual(result[0]["moderation"], "allow")
        self.assertEqual(self.store.get_draft(source_draft)["status"], "approved")
        self.assertEqual(self.store.get_draft(manual_draft)["status"], "draft")
        self.assertEqual(self.store.list_source_posts()[0]["moderation_decision"], "allow")
        self.bot.send_message.assert_awaited_once()

    async def test_commands_are_held_but_short_informational_posts_can_be_allowed(self):
        from publisher.telegram import publish_captured_source_posts
        command_id = self.store.capture_source_post(-100111, 56, "/pubsources", "/pubsources")[0]
        short_id = self.store.capture_source_post(-100111, 57, "Tiny", "tiny")[0]
        review = {
            "provider": "openai", "model": "gpt-6-luna",
            "decision": "allow", "confidence": 0.96, "category": "news",
            "reason": "Short but relevant informational update.",
            "flags": [], "raw_response": '{"decision":"allow"}',
        }
        with patch("publisher.telegram.moderate_source_post", new=AsyncMock(return_value=review)) as moderator:
            result = await publish_captured_source_posts(self.bot, self.store, self.target_id)
        self.assertEqual([x["draft_id"] for x in result], [command_id, short_id])
        self.assertEqual([x["status"] for x in result], ["held", "sent"])
        moderator.assert_awaited_once_with("Tiny", "tiny")
        self.assertEqual(self.store.get_draft(command_id)["status"], "draft")
        self.assertEqual(self.store.get_draft(short_id)["status"], "approved")
        self.bot.send_message.assert_awaited_once()

    async def test_moderation_error_fails_closed_and_is_not_retried_immediately(self):
        from publisher.telegram import publish_captured_source_posts
        draft_id = self.store.capture_source_post(
            -100111, 58, "Crypto news", "A new protocol testnet was announced today."
        )[0]
        with patch(
            "publisher.telegram.moderate_source_post",
            new=AsyncMock(side_effect=RuntimeError("openai_timeout")),
        ):
            result = await publish_captured_source_posts(self.bot, self.store, self.target_id)
        self.assertEqual(result[0]["status"], "error")
        self.assertEqual(self.store.get_draft(draft_id)["status"], "draft")
        self.assertIsNone(self.store.get_delivery(draft_id, self.target_id))
        self.assertEqual(self.store.list_source_posts()[0]["moderation_decision"], "error")
        self.assertEqual(self.store.list_unprocessed_source_posts(), [])
        self.bot.send_message.assert_not_awaited()

    async def test_low_confidence_allow_is_held(self):
        from publisher.telegram import publish_captured_source_posts
        draft_id = self.store.capture_source_post(
            -100111, 59, "Possible market update", "A token may be listed soon."
        )[0]
        review = {
            "provider": "openai", "model": "gpt-6-luna",
            "decision": "allow", "confidence": 0.72, "category": "news",
            "reason": "Not enough context to classify with high confidence.",
            "flags": [], "raw_response": '{"decision":"allow"}',
        }
        with patch("publisher.telegram.moderate_source_post", new=AsyncMock(return_value=review)):
            result = await publish_captured_source_posts(self.bot, self.store, self.target_id)
        self.assertEqual(result[0]["status"], "held")
        self.assertEqual(self.store.get_draft(draft_id)["status"], "draft")
        self.assertEqual(self.store.list_source_posts()[0]["moderation_decision"], "hold")
        self.bot.send_message.assert_not_awaited()

    async def test_command_registration_exposes_guarded_publisher_controls(self):
        from publisher.telegram import register_handlers

        class FakeApp:
            def __init__(self):
                self.handlers = []

            def add_handler(self, handler):
                self.handlers.append(handler)

        async def admin_check(update, context):
            return True

        app = FakeApp()
        register_handlers(app, admin_check)
        commands = {next(iter(handler.commands)) for handler in app.handlers}
        self.assertEqual(commands, {
            "pubhelp", "pubtargets", "pubdraft", "pubapprove",
            "pubsources", "pubreview", "pubplan", "pubsend", "pubsendall", "pubdelivery",
        })


    async def test_batch_limit_defers_remaining_targets_and_next_run_continues(self):
        from publisher.telegram import publish_draft_to_eligible_targets

        second_id = self.store.add_target("channel", "@second_channel")
        self.store.review_target(
            second_id, "approve", "allowed",
            "Moderator explicitly approved one promotional post",
        )
        self.bot.get_chat.side_effect = [
            SimpleNamespace(id=-100123456789, type="channel", username="sample_channel"),
        ]
        self.bot.get_chat_member.side_effect = [
            SimpleNamespace(status="administrator", can_post_messages=True),
        ]
        self.bot.send_message.side_effect = [SimpleNamespace(message_id=201)]

        _, first_run, cursor = await publish_draft_to_eligible_targets(
            self.bot, self.store, self.draft_id, delay_seconds=0, max_targets=1
        )
        self.assertEqual([row["status"] for row in first_run], ["sent", "deferred"])
        self.assertEqual(cursor, self.target_id)

        self.bot.get_chat.side_effect = [
            SimpleNamespace(id=-100987654321, type="channel", username="second_channel"),
        ]
        self.bot.get_chat_member.side_effect = [
            SimpleNamespace(status="administrator", can_post_messages=True),
        ]
        self.bot.send_message.side_effect = [SimpleNamespace(message_id=202)]
        _, second_run, second_cursor = await publish_draft_to_eligible_targets(
            self.bot, self.store, self.draft_id, delay_seconds=0, max_targets=1,
            after_target_id=cursor,
        )
        self.assertEqual([row["status"] for row in second_run], ["sent"])
        self.assertEqual(second_cursor, second_id)
        self.assertEqual(self.bot.send_message.await_count, 2)

    async def test_non_admin_cannot_execute_publish_command(self):
        from publisher.telegram import register_handlers

        class FakeApp:
            def __init__(self):
                self.handlers = []

            def add_handler(self, handler):
                self.handlers.append(handler)

        async def deny_admin(update, context):
            return False

        app = FakeApp()
        register_handlers(app, deny_admin)
        handler = next(item for item in app.handlers if "pubsend" in item.commands)
        reply_text = AsyncMock()
        update = SimpleNamespace(
            effective_message=SimpleNamespace(reply_text=reply_text)
        )
        context = SimpleNamespace(args=["1", "1"], bot=self.bot)
        await handler.callback(update, context)
        reply_text.assert_awaited_once_with("Administrator access required.")
        self.bot.send_message.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()

[executed on device: Gensyn2.play2go.cloud (03201713-0ab1-4309-bc64-9b0566307ce7)]