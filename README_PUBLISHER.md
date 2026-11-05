# CryptoPing RU Publisher

Publisher is an opt-in publication workflow integrated into the existing
`group_bot.py` application. It uses the same Telegram Bot API client and process;
it does not start a second polling process. Its review, draft and delivery state
lives in `data/publisher.db`, separate from the legacy growth database.

## Local setup and candidate intake

Requires Python 3.10+ and the repository dependencies.

```powershell
python -m publisher --help
python -m publisher import-catalog
python -m publisher list-targets
python -m publisher show-target --id 1
```

Imported candidates remain pending. Discovery descriptions and directory
snapshots are not permission to publish. A human must inspect current in-chat
rules and record explicit permission evidence.

```powershell
python -m publisher review-target --id 1 --decision approve --policy allowed --evidence "Rules message URL and moderator permission"
python -m publisher add-draft --title "CryptoPing RU" --text "A useful, relevant post with a transparent channel reference."
python -m publisher approve-draft --id 1
python -m publisher plan --draft-id 1
```

A group becomes eligible when Telegram reports that the bot joined it as a
member. Live membership and send permissions are checked immediately before
each post. Pausing a target preserves its review history.

## Telegram operator commands

The following commands are registered on the existing bot and restricted by
the existing growth administrator check:

- `/pubhelp` - show Publisher commands.
- `/pubtargets` - show registered destinations and review state.
- `/pubdraft Title | message text` - create a draft.
- `/pubapprove DRAFT_ID` - approve a draft for publication.
- `/pubreview TARGET_ID allow | evidence` - record explicit permission.
- `/pubreview TARGET_ID reject | reason` - reject a destination.
- `/pubplan DRAFT_ID` - show eligible and excluded destinations.
- `/pubsend DRAFT_ID TARGET_ID` - send to one destination.
- `/pubsendall DRAFT_ID [AFTER_TARGET_ID]` - send a batch and continue from a stable target-ID cursor.
- `/pubdelivery DRAFT_ID TARGET_ID` - inspect delivery state.

A draft must be approved and the target must have a fresh human approval with
`promotion_policy=allowed` and non-empty evidence. Immediately before sending,
the bot resolves the public destination and checks its live Telegram membership
and live membership/send permissions. For groups, ordinary bot membership is
sufficient when the group's default permissions allow members to send messages;
the bot does not need administrator rights. Channels still require
administrator status with can_post_messages.
A destination whose Telegram type does not match the registered target kind is
blocked. Text-only posts are limited to Telegram's 4096-character text limit.

Manual bulk publishing is operator-triggered, sequential, limited to 20 target
attempts per command, and waits 1.2 seconds between attempts. The autonomous
source pipeline appends a target-specific invite to our public channel (with
join attribution), then sends the moderated news item to every eligible
external group where Telegram confirms bot membership and live send permission.
There are no project-imposed daily, per-news, or destination cooldown caps.
Telegram's own API limits apply. Duplicate delivery protection remains per
draft and destination. The bot must already be a member of each group; it never
requests administrator rights or joins automatically. When Telegram reports
that the bot joined a public group, it is automatically registered as eligible.
If the bot is removed, the destination is paused. There is no scraping,
unsolicited direct messaging, or paid placement.

## Delivery safety and recovery

Every draft/target pair has one unique delivery record:

- `sent`: Telegram returned a message ID; repeat sends are blocked.
- `failed`: Telegram definitively rejected the request; an administrator may
  explicitly retry with `/pubsend` or `/pubsendall`.
- `unknown`: a network failure occurred after the send attempt; retry is
  blocked because Telegram may have accepted the post.
- `sending`: an in-flight or interrupted attempt; repeat sends are blocked.

Unknown outcomes require manual inspection in the destination before any
recovery decision. This avoids duplicate posts after ambiguous network errors.
Successful publication timestamps are retained for reporting, not used as a
cooldown. Public message links are stored when Telegram exposes a public username.

## Tests

```powershell
python -m unittest discover -s tests -v
python -m compileall -q group_bot.py growth_db.py publisher scripts
```

Telegram delivery tests use mocked Bot API responses. They verify permission
checks, target-kind matching, draft approval, stale-review rejection,
duplicate-send protection, no arbitrary permission expiry or destination
cooldown, manual retry of definitive failures, and non-retry of ambiguous network outcomes. They do not claim that a
live bot has permissions in any real community; those rights must be verified
at runtime before the first actual post.

## Autonomous AI moderation

New posts from @cryptoping_ru are captured and checked by the moderation model
before the bot sends them to the owned community @cryptoping_ru_chat. During the
initial external-distribution trial, the same approved item can be sent to the
two selected destinations @ifreepr and @prchatik. Delivery remains disabled for
each destination until Telegram confirms that the bot is a member and the
group's ordinary member permissions allow messages. The bot does not need
administrator rights.
Only a high-confidence `allow` for `news`, `analysis`, or `education`
with no risk flags can pass automatically. Promotions, referrals, uncertain
claims, off-topic posts, and borderline cases are held. Clear phishing, wallet
theft, malware, impersonation, and fraud are blocked.

The model classifies the supplied text; it does not independently verify facts,
open links, or certify a project's claims. A successful model verdict is not a
fact-check.

Configure the service environment using `.env.example`:

- `CRYPTOPING_MODERATOR_PROVIDER` selects the primary provider (`gemini`, `groq`, or `openai`).
- `GEMINI_API_KEY` and `CRYPTOPING_MODERATOR_GEMINI_MODEL` configure Gemini.
- `GROQ_API_KEY` and `CRYPTOPING_MODERATOR_GROQ_MODEL` configure Groq.
- `OPENAI_API_KEY` and `CRYPTOPING_MODERATOR_MODEL` are optional OpenAI fallback settings.
- `CRYPTOPING_MODERATOR_TIMEOUT_SECONDS` defaults to 30 seconds.

The moderator tries the selected provider first, then other configured providers
when an API request fails or the response is invalid. If no provider succeeds,
the post stays unpublished (fail-closed). Provider keys are not included in
this repository and must never be committed. Free-tier quotas, availability,
and provider data-use terms are controlled by each provider and can change.
Final allow/hold/block decisions are retained in `source_moderation_reviews`
and visible to the bot administrator through `/pubsources`.

The moderator uses structured JSON output and a common validation gate across
providers. It classifies supplied text only; it does not independently verify
facts, open links, or certify a project's claims. The classifier is not a
promise of perfect fraud detection.

## Distribution without external bot administrator rights

The user has ruled out obtaining administrator rights for our bot in external
Telegram groups. Do not design external distribution around that requirement.
See `AGENTS.md`, `docs/SESSION-CHECKPOINT.md`, and
`docs/DISTRIBUTION-STRATEGY.md` before making distribution changes. Preferred
routes include free Telegram Suggested Posts, member-level posts where current
rules allow them, editorial/directory submissions, owned web/RSS assets, and
organic contributions that comply with community rules. Do not use unattended
userbot mass-posting, unsolicited DMs, or repetitive link drops.


## Current architecture and known limitations (reviewed 2026-11-05)

The source of this autonomous relay is the public channel `@cryptoping_ru`, populated by the existing RSS publisher at `/root/crypto-bot-farm/main.py`. The second bot captures channel posts; it does not currently ingest messages from the owned discussion group or arbitrary third-party groups. It moderates eligible source posts and relays them to `@cryptoping_ru_chat`.

External fan-out is currently restricted in code to `@ifreepr` and `@prchatik`. The bot must already be a member of a destination and Telegram must confirm live send permission. Ordinary group membership can be sufficient; administrator rights are not universally required. The bot cannot join groups autonomously. A catalogue entry is not permission to publish.

The publisher appends a persistent, target-specific referral invite to the public channel `@cryptoping_ru` (the configured `CHAT_ID`). Links are cached per target, not rotated for every message. Change the referral destination only after an explicit owner decision.

There are no project-imposed daily, per-news or per-target cooldown caps in the current policy. A 24-hour delivery counter exists in storage but is not connected to the policy gate. Do not describe numeric caps as implemented. The owner has not approved new arbitrary caps. Telegram flood-control responses, destination rules, live permission checks and per-draft/per-target duplicate protection remain authoritative.

The autonomous moderation path requires at least one working configured LLM provider. If no provider key is configured or all providers fail, the post remains unpublished. There is no publish-without-moderation fallback.

Do not replace the Bot API publisher with an unattended Telethon/Pyrogram promotional userbot. No unsolicited DMs, mass invitations, repetitive link drops or spam-like automation. For the full assessment and prioritized gaps, see `docs/THREE-ADVICE-TECHNICAL-REVIEW-2026-11-05.md`.
