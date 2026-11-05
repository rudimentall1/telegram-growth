# Legacy RSS publisher handoff patch

The RSS publisher is a separate live program at `/root/crypto-bot-farm/main.py` and has no Git repository of its own. Its only production change for the Publisher integration is stored here as a reviewable patch.

## Apply on the Gensyn2 host

1. Back up the current RSS script:

   `cp -a /root/crypto-bot-farm/main.py /root/crypto-bot-farm/main.py.before-publisher-handoff`

2. From the RSS publisher directory, apply the patch once:

   `cd /root/crypto-bot-farm && patch -p1 < /opt/telegram-growth/integrations/legacy-rss-publisher/main.py.patch`

3. Check the script without running a real feed cycle:

   `/root/crypto-bot-farm/venv/bin/python -m py_compile /root/crypto-bot-farm/main.py`

The runtime handoff module is maintained in this repository at `publisher/rss_handoff.py`. It writes successful Telegram message IDs to the shared Publisher database and falls back to a durable JSONL outbox when the database is temporarily unavailable.

The patch does not change RSS sources, filters, translation, post content, frequency, Telegram destination, or cron schedule. It does not contain credentials. Do not commit the live `config.py`, `.env`, SQLite databases, or runtime state.
