import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import config
import group_bot


class GrowthAdminTests(unittest.IsolatedAsyncioTestCase):
    async def test_telegram_service_account_is_allowed_only_in_target_group_without_api_lookup(self):
        update = SimpleNamespace(
            effective_message=SimpleNamespace(sender_chat=None, from_user=None),
            effective_chat=SimpleNamespace(id=group_bot.GROUP_CHAT_ID),
            effective_user=SimpleNamespace(id=777000),
            update_id=5,
        )
        context = SimpleNamespace(bot=SimpleNamespace(get_chat_member=AsyncMock()))
        with patch.object(config, "GROWTH_ADMIN_IDS", set()):
            allowed = await group_bot._growth_admin(update, context)
        self.assertTrue(allowed)
        context.bot.get_chat_member.assert_not_awaited()

    async def test_telegram_service_account_in_another_chat_does_not_get_special_access(self):
        update = SimpleNamespace(
            effective_message=SimpleNamespace(sender_chat=None, from_user=None),
            effective_chat=SimpleNamespace(id=123),
            effective_user=SimpleNamespace(id=777000),
            update_id=6,
        )
        context = SimpleNamespace(
            bot=SimpleNamespace(
                get_chat_member=AsyncMock(return_value=SimpleNamespace(status="member"))
            )
        )
        with patch.object(config, "GROWTH_ADMIN_IDS", set()):
            allowed = await group_bot._growth_admin(update, context)
        self.assertFalse(allowed)
        context.bot.get_chat_member.assert_awaited_once_with(group_bot.GROUP_CHAT_ID, 777000)

    async def test_configured_admin_is_allowed_without_api_lookup(self):
        update = SimpleNamespace(
            effective_message=SimpleNamespace(sender_chat=None),
            effective_chat=SimpleNamespace(id=123),
            effective_user=SimpleNamespace(id=456),
            update_id=1,
        )
        context = SimpleNamespace(bot=SimpleNamespace(get_chat_member=AsyncMock()))
        with patch.object(config, "GROWTH_ADMIN_IDS", {456}):
            allowed = await group_bot._growth_admin(update, context)
        self.assertTrue(allowed)
        context.bot.get_chat_member.assert_not_awaited()


    async def test_anonymous_group_identity_is_denied_outside_target_group(self):
        update = SimpleNamespace(
            effective_message=SimpleNamespace(
                sender_chat=SimpleNamespace(id=group_bot.GROUP_CHAT_ID),
                from_user=None,
            ),
            effective_chat=SimpleNamespace(id=123),
            effective_user=None,
            update_id=7,
        )
        context = SimpleNamespace(bot=SimpleNamespace(get_chat_member=AsyncMock()))
        with patch.object(config, "GROWTH_ADMIN_IDS", set()):
            allowed = await group_bot._growth_admin(update, context)
        self.assertFalse(allowed)
        context.bot.get_chat_member.assert_not_awaited()

    async def test_regular_member_is_denied(self):
        update = SimpleNamespace(
            effective_message=SimpleNamespace(sender_chat=None, from_user=None),
            effective_chat=SimpleNamespace(id=123),
            effective_user=SimpleNamespace(id=456),
            update_id=2,
        )
        context = SimpleNamespace(
            bot=SimpleNamespace(
                get_chat_member=AsyncMock(return_value=SimpleNamespace(status="member"))
            )
        )
        with patch.object(config, "GROWTH_ADMIN_IDS", set()):
            allowed = await group_bot._growth_admin(update, context)
        self.assertFalse(allowed)
        context.bot.get_chat_member.assert_awaited_once_with(group_bot.GROUP_CHAT_ID, 456)

    async def test_telegram_group_admin_is_allowed(self):
        update = SimpleNamespace(
            effective_message=SimpleNamespace(sender_chat=None, from_user=None),
            effective_chat=SimpleNamespace(id=123),
            effective_user=SimpleNamespace(id=456),
            update_id=3,
        )
        context = SimpleNamespace(
            bot=SimpleNamespace(
                get_chat_member=AsyncMock(return_value=SimpleNamespace(status="administrator"))
            )
        )
        with patch.object(config, "GROWTH_ADMIN_IDS", set()):
            allowed = await group_bot._growth_admin(update, context)
        self.assertTrue(allowed)

    async def test_api_error_fails_closed(self):
        update = SimpleNamespace(
            effective_message=SimpleNamespace(sender_chat=None, from_user=None),
            effective_chat=SimpleNamespace(id=123),
            effective_user=SimpleNamespace(id=456),
            update_id=4,
        )
        context = SimpleNamespace(
            bot=SimpleNamespace(get_chat_member=AsyncMock(side_effect=RuntimeError("API unavailable")))
        )
        with patch.object(config, "GROWTH_ADMIN_IDS", set()):
            allowed = await group_bot._growth_admin(update, context)
        self.assertFalse(allowed)



class GrowthLinkCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_unauthorized_user_cannot_create_invite_link(self):
        update = SimpleNamespace(
            effective_message=SimpleNamespace(reply_text=AsyncMock()),
            effective_user=SimpleNamespace(id=456),
        )
        context = SimpleNamespace(
            args=["campaign"],
            bot=SimpleNamespace(create_chat_invite_link=AsyncMock()),
        )
        with patch.object(group_bot, "_growth_admin", new=AsyncMock(return_value=False)):
            await group_bot.growth_link(update, context)
        context.bot.create_chat_invite_link.assert_not_awaited()
        update.effective_message.reply_text.assert_awaited_once_with(
            "Команда доступна только администраторам группы."
        )

    async def test_invalid_source_is_rejected_before_api_call(self):
        update = SimpleNamespace(
            effective_message=SimpleNamespace(reply_text=AsyncMock()),
            effective_user=SimpleNamespace(id=456),
        )
        context = SimpleNamespace(
            args=["bad source"],
            bot=SimpleNamespace(create_chat_invite_link=AsyncMock()),
        )
        with patch.object(group_bot, "_growth_admin", new=AsyncMock(return_value=True)):
            await group_bot.growth_link(update, context)
        context.bot.create_chat_invite_link.assert_not_awaited()
        update.effective_message.reply_text.assert_awaited_once_with(
            "Источник: 1–32 символа, только латиница, цифры, _ и -."
        )


    async def test_successful_growth_link_includes_ready_campaign_copy(self):
        update = SimpleNamespace(
            effective_message=SimpleNamespace(reply_text=AsyncMock()),
            effective_user=SimpleNamespace(id=456),
        )
        invite = SimpleNamespace(invite_link="https://t.me/+campaignA")
        context = SimpleNamespace(
            args=["campaign_a"],
            bot=SimpleNamespace(create_chat_invite_link=AsyncMock(return_value=invite)),
        )
        with (
            patch.object(group_bot, "_growth_admin", new=AsyncMock(return_value=True)),
            patch.object(group_bot.growth_db, "save_link") as save_link,
        ):
            await group_bot.growth_link(update, context)

        save_link.assert_called_once_with("https://t.me/+campaignA", "campaign_a", 456)
        response = update.effective_message.reply_text.await_args.args[0]
        self.assertIn("Отслеживаемая ссылка: https://t.me/+campaignA", response)
        self.assertIn("Готовый текст для размещения", response)
        self.assertIn("Подписаться: https://t.me/+campaignA", response)


class ChannelMembershipHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_join_event_is_recorded_with_invite_link(self):
        member = SimpleNamespace(id=789, is_bot=False)
        invite = SimpleNamespace(invite_link="https://t.me/+testCampaign", name="test_campaign")
        event = SimpleNamespace(
            chat=SimpleNamespace(id=1234, type="channel"),
            old_chat_member=SimpleNamespace(status="left"),
            new_chat_member=SimpleNamespace(status="member", user=member),
            invite_link=invite,
        )
        update = SimpleNamespace(chat_member=event, update_id=44)
        context = SimpleNamespace(
            bot=SimpleNamespace(get_chat=AsyncMock(return_value=SimpleNamespace(id=1234)))
        )
        with patch.object(group_bot.growth_db, "record_member") as record:
            await group_bot.track_channel_member(update, context)
        record.assert_called_once_with(44, 789, "https://t.me/+testCampaign", True)

    async def test_membership_event_from_wrong_chat_is_ignored(self):
        member = SimpleNamespace(id=789, is_bot=False)
        event = SimpleNamespace(
            chat=SimpleNamespace(id=9999, type="channel"),
            old_chat_member=SimpleNamespace(status="left"),
            new_chat_member=SimpleNamespace(status="member", user=member),
            invite_link=None,
        )
        update = SimpleNamespace(chat_member=event, update_id=45)
        context = SimpleNamespace(
            bot=SimpleNamespace(get_chat=AsyncMock(return_value=SimpleNamespace(id=1234)))
        )
        with patch.object(group_bot.growth_db, "record_member") as record:
            await group_bot.track_channel_member(update, context)
        record.assert_not_called()


class GrowthReportTests(unittest.IsolatedAsyncioTestCase):
    async def test_report_accepts_period_and_shows_source_active_counts(self):
        update = SimpleNamespace(
            effective_message=SimpleNamespace(reply_text=AsyncMock()),
            effective_user=SimpleNamespace(id=456),
        )
        context = SimpleNamespace(args=["7d"])
        rows = [("campaign_a", 2, 1, 1, 3), ("unattributed", 1, 1, 0, 1)]

        with (
            patch.object(group_bot, "_growth_admin", new=AsyncMock(return_value=True)),
            patch.object(group_bot.growth_db, "source_report", return_value=rows) as report,
        ):
            await group_bot.growth_report(update, context)

        report.assert_called_once_with(7)
        text = update.effective_message.reply_text.await_args.args[0]
        self.assertIn("Период: последние 7 дн.", text)
        self.assertIn("Активны сейчас в базе: 4", text)
        self.assertIn("campaign_a: +2 вступл., −1 отписок, баланс 1, активны сейчас 3", text)
        self.assertIn("не полное число подписчиков канала", text)

    async def test_report_rejects_unsupported_period(self):
        update = SimpleNamespace(
            effective_message=SimpleNamespace(reply_text=AsyncMock()),
            effective_user=SimpleNamespace(id=456),
        )
        context = SimpleNamespace(args=["0d"])
        with patch.object(group_bot, "_growth_admin", new=AsyncMock(return_value=True)):
            await group_bot.growth_report(update, context)
        self.assertIn(
            "Укажи период",
            update.effective_message.reply_text.await_args.args[0],
        )


class OptInPromotionTests(unittest.IsolatedAsyncioTestCase):
    async def test_allowpromo_rejects_non_admin(self):
        chat = SimpleNamespace(id=-100123456789, type="supergroup", title="Test group", username="test_group")
        update = SimpleNamespace(
            effective_chat=chat,
            effective_message=SimpleNamespace(reply_text=AsyncMock(), sender_chat=None),
            effective_user=SimpleNamespace(id=456),
        )
        context = SimpleNamespace(
            bot=SimpleNamespace(
                get_chat_member=AsyncMock(return_value=SimpleNamespace(status="member")),
                create_chat_invite_link=AsyncMock(),
            )
        )
        await group_bot.allow_promotion(update, context)
        context.bot.create_chat_invite_link.assert_not_awaited()
        self.assertIn(
            "только администратор",
            update.effective_message.reply_text.await_args.args[0],
        )

    async def test_allowpromo_admin_registers_tracked_target(self):
        chat = SimpleNamespace(id=-100123456789, type="supergroup", title="Test group", username="test_group")
        update = SimpleNamespace(
            effective_chat=chat,
            effective_message=SimpleNamespace(reply_text=AsyncMock(), sender_chat=None),
            effective_user=SimpleNamespace(id=456),
        )
        invite = SimpleNamespace(invite_link="https://t.me/+campaignGroup")
        context = SimpleNamespace(
            bot=SimpleNamespace(
                get_chat_member=AsyncMock(return_value=SimpleNamespace(status="administrator")),
                create_chat_invite_link=AsyncMock(return_value=invite),
            )
        )

        with (
            patch.object(group_bot.growth_db, "save_link") as save_link,
            patch.object(group_bot.growth_db, "enable_promotion_target") as enable_target,
            patch.object(config, "PROMOTION_INTERVAL_HOURS", 72, create=True),
        ):
            await group_bot.allow_promotion(update, context)

        source = f"promo_{abs(chat.id)}"
        context.bot.create_chat_invite_link.assert_awaited_once_with(
            chat_id=group_bot.CHAT_ID,
            name=source,
            creates_join_request=False,
        )
        save_link.assert_called_once_with("https://t.me/+campaignGroup", source, 456)
        enable_target.assert_called_once_with(
            chat_id=chat.id,
            title="Test group",
            username="test_group",
            invite_link="https://t.me/+campaignGroup",
            authorized_by=456,
        )
        self.assertIn(
            "не чаще одного раза в 72 ч.",
            update.effective_message.reply_text.await_args.args[0],
        )

    async def test_disablepromo_disables_current_chat(self):
        chat = SimpleNamespace(id=-100123456789, type="supergroup")
        message = SimpleNamespace(reply_text=AsyncMock())
        update = SimpleNamespace(effective_chat=chat, effective_message=message)
        context = SimpleNamespace()
        with (
            patch.object(group_bot, "_current_chat_admin", new=AsyncMock(return_value=True)),
            patch.object(group_bot.growth_db, "disable_promotion_target", return_value=True) as disable,
        ):
            await group_bot.disable_promotion(update, context)
        disable.assert_called_once_with(chat.id)
        self.assertIn("отключено", message.reply_text.await_args.args[0])

    async def test_scheduler_sends_to_opted_in_target_and_records_message(self):
        chat_id = -100123456789
        context = SimpleNamespace(
            bot=SimpleNamespace(
                send_message=AsyncMock(return_value=SimpleNamespace(message_id=321))
            )
        )
        target = (chat_id, "Test group", "test_group", "https://t.me/+campaignGroup")
        with (
            patch.object(group_bot.growth_db, "due_promotion_targets", return_value=[target]) as due,
            patch.object(group_bot.growth_db, "mark_promotion_sent") as mark_sent,
            patch.object(group_bot.growth_db, "mark_promotion_failed") as mark_failed,
            patch.object(group_bot.asyncio, "sleep", new=AsyncMock()),
            patch.object(config, "PROMOTION_INTERVAL_HOURS", 72, create=True),
        ):
            await group_bot.publish_due_promotions(context)

        due.assert_called_once_with(72)
        context.bot.send_message.assert_awaited_once_with(
            chat_id=chat_id,
            text=group_bot._promotion_text("https://t.me/+campaignGroup"),
            disable_web_page_preview=True,
        )
        mark_sent.assert_called_once_with(chat_id, 321)
        mark_failed.assert_not_called()

    async def test_scheduler_disables_target_after_permission_error(self):
        from telegram.error import Forbidden

        chat_id = -100123456789
        context = SimpleNamespace(
            bot=SimpleNamespace(send_message=AsyncMock(side_effect=Forbidden("forbidden")))
        )
        target = (chat_id, "Test group", "test_group", "https://t.me/+campaignGroup")
        with (
            patch.object(group_bot.growth_db, "due_promotion_targets", return_value=[target]),
            patch.object(group_bot.growth_db, "mark_promotion_sent") as mark_sent,
            patch.object(group_bot.growth_db, "mark_promotion_failed") as mark_failed,
            patch.object(group_bot.asyncio, "sleep", new=AsyncMock()),
        ):
            await group_bot.publish_due_promotions(context)

        mark_sent.assert_not_called()
        self.assertEqual(mark_failed.call_args.args[0], chat_id)
        self.assertTrue(mark_failed.call_args.kwargs["disable"])


if __name__ == "__main__":
    unittest.main()
