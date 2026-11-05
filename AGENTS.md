# CryptoPing RU repository instructions

## Mandatory start-of-session rule

Before doing any work in this repository, in every new chat or work session:

1. Read `docs/SESSION-CHECKPOINT.md` first.
2. Read `docs/DISTRIBUTION-STRATEGY.md` before changing audience-growth or publishing workflows.
3. Treat the checkpoint as the current operational source of truth. Verify live state before making claims that a service, provider, scheduler, or deployment is healthy.
4. At the end of every work session, update `docs/SESSION-CHECKPOINT.md` with what changed, what was verified, what remains incomplete, and the exact next action.
5. When switching chats, leave enough detail in the checkpoint for another engineer to resume without asking the user to repeat context.

## Fixed distribution constraint

The user has explicitly ruled out getting administrator rights for our bot in external Telegram groups. Treat this as a permanent project constraint:

- Do not ask external group administrators to promote our bot to admin.
- Do not design external-group distribution around Bot API administrator access.
- Ordinary bot membership in a group is acceptable only when the group permits it,
  current rules explicitly allow relevant posts, and Telegram confirms send permission.
- Owner request (2026-11-04): when an external group's rules require the publisher to join another chat/channel first, the system should satisfy that prerequisite automatically where Telegram permits it. The current Telegram bot identity cannot do this itself: Bot API has no join-chat method; MTProto `channels.joinChannel` is documented as users-only; and Telegram's channel-invite method reports that bots can only be admins in channels. Do not implement a fake join call or substitute a personal user account while claiming the bot joined.
  - If the prerequisite is another group, an authorized group member must add the bot as an ordinary member. Once Telegram's `my_chat_member` update confirms the bot joined a public group as `member`, `administrator`, or `creator` (or restricted with `is_member=true` and `can_send_messages=true`), automatically register/approve that group as `allowed`.
  - If the prerequisite is a broadcast channel subscription, the bot cannot satisfy it under the owner's no-external-admin constraint. Keep the dependent destination non-sendable and record the reason; do not request channel admin rights.
  - Live send permission is checked immediately before each publication. This does not bypass group rules. Pause approved targets when Telegram reports the bot was removed.
- Do not keep proposing external bot-admin access as a next step.
- Prefer distribution methods that work without our bot being an admin: Telegram channel Suggested Posts, user-account posts only where group rules explicitly allow member posts, content submissions/direct-message workflows, owned social profiles, public directories, newsletters/RSS, and organic search.
- A human or channel owner may still choose to approve an individual Suggested Post or partnership. That is content approval, not granting our bot administrator privileges.
- Do not use unattended MTProto/userbot mass-posting, unsolicited DMs, mass invitations, repetitive link drops, or other spam-like automation. Respect platform rules and account safety.
- Never represent a candidate directory entry or public description as permission to publish. Verify each destination's current rules and accepted submission path before adding it to an executable queue.

## Operational safeguards

- Keep CryptoPing RU changes scoped to `/opt/telegram-growth`; do not disturb unrelated server projects.
- Never print, copy into chat, commit, or log API keys, bot tokens, or other secrets.
- Do not restart `crypto-group-bot.service` unless a code/config change requires it; verify the service after any intentional restart.
- Do not reset, rebase, merge, or force-push while local `main` and `origin/main` are divergent. Preserve the untracked `data/` directory and live SQLite databases.
- Keep moderation fail-closed: if all configured providers fail or return invalid output, do not publish.
- Test with isolated SQLite databases and mocked Telegram delivery before any live publication.


## Distribution research correction

Do not infer that a public channel forbids submissions because its Suggested Posts/DM control is not visible in a web preview or public catalogue. The prior reach shortlist was not a verified permissions list. Only mark a target prohibited when explicit current rules or a documented failed submission path support that conclusion. Prioritize our own public channel first: as of 2026-11-04 the production bot is confirmed administrator of `@cryptoping_ru` with `can_post_messages=true`. Preserve external-admin prohibition; never ask another channel/group to grant our bot admin rights.


## Two-project architecture source of truth

Before making any bot, publishing, or distribution change, read `docs/CURRENT-TELEGRAM-ARCHITECTURE-2026-11-04.md` in addition to the session checkpoint. The older `/root/crypto-bot-farm/main.py` is the existing 15-minute RSS publisher into `@cryptoping_ru`; the active systemd group bot is its later extension under `/opt/telegram-growth`. Do not call the RSS publishing function missing, do not claim credit for pre-existing bot infrastructure, and do not conflate internal owned-group promotion with external-channel distribution. Preserve the config/data symlinks and keep the two runtime paths distinct.


## Current distribution architecture (2026-11-04 owner decision)

- Disable and do not reintroduce periodic self-promotion of @cryptoping_ru inside
  our own @cryptoping_ru_chat group.
- Remove reciprocal channel cross-promotion that requires the bot to be an admin
  in third-party channels. cross_promo.py is decommissioned.
- The first project /root/crypto-bot-farm/main.py remains the existing RSS source
  publisher into @cryptoping_ru; do not recreate it.
- The second project captures those channel posts, AI-moderates them, sends
  approved news to our own group, then publishes to every eligible external
  public group where Telegram confirms the bot is a member and can send messages.
  External channels are not part of this route. No administrator rights are
  required; never auto-join or request admin rights.
- Do not impose invented daily caps, per-news destination caps, or cooldowns.
  Telegram's actual API limits and each group's real posting permissions govern
  delivery. Preserve per-draft/per-target duplicate protection and stop on
  permission errors, blocks, or Telegram flood-control responses. Keep content
  relevant and follow platform and group rules; do not spam.
- Only append a tracked invite to our public channel where a destination-specific
  invite can be created. No external affiliate/referral URL inventory was found
  in either repository at this checkpoint; never invent affiliate links.


## Owner-provided anti-ban guidance

- Use official Telegram interfaces or supported Bot API workflows within documented limits. The 30 messages/second figure is a platform ceiling, never a publishing target; actual chat limits and Telegram flood-control responses take precedence.
- Never send unsolicited promotional DMs or mass-message unrelated chats.
- Avoid waves of identical advertising posts with external links across multiple groups.
- Tailor useful content to each destination and include referral links only where current rules allow them.
- Candidate handles supplied by the owner are discovery leads, not verified permissions. Do not assume they are prohibited or permitted without checking current rules and actual submission routes. See `docs/OWNER-SUPPLIED-DISTRIBUTION-LEADS-2026-11-04.md`.
