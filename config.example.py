# Copy this file to config.py and fill in local values.
# Never commit config.py or a real Telegram token.

TELEGRAM_TOKEN = "PUT_BOT_TOKEN_HERE"
GROUP_CHAT_ID = -1000000000000
CHAT_ID = "@your_channel"

# Optional Telegram user IDs allowed to use /growthlink and /growthreport.
# Channel/group administrators are also checked through Telegram's getChatMember API.
GROWTH_ADMIN_IDS = set()

# Opt-in group promotion: one post per target per this many hours.
# Each target group must have the bot added and an administrator must run /allowpromo.
PROMOTION_INTERVAL_HOURS = 72
PROMOTION_CHECK_INTERVAL_MINUTES = 5
