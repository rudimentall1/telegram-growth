import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import config
import group_bot


class GrowthAdminTests(unittest.IsolatedAsyncioTestCase):
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


if __name__ == "__main__":
    unittest.main()
