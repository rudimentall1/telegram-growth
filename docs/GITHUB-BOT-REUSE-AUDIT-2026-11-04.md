# Telegram distribution inventory and GitHub reuse audit

**Checked:** 2026-11-04  
**Scope:** `/opt/telegram-growth/distribution/targets.json`, existing first/second bot architecture, public GitHub candidates.

## Existing repository inventory

The list the owner remembered is `distribution/targets.json`. It is already a substantial discovery register:

- **23 networks / promotion services**;
- **125 Telegram communities / groups / channel leads**;
- **26 directories / discovery services**.

It was last marked `checked_at: 2026-10-28`; records are mostly discovery candidates, not live-confirmed current permissions.

High-priority network entries already present:
- Onflow Ads Cross-Promotion — `https://onflowads.com/telegram/cross-promotion`
- Adpact — `https://adpact.app/guides/telegram-cross-promotion/`
- Trigram — `https://trigram.site/`
- TelegrAd — `https://telegrad.link/en`
- Onflow subscriber exchange — `https://onflowads.com/telegram/subscriber-exchange`
- Lyzem FreePromo — `https://t.me/Lyzembot`

Other bot/service candidates already registered include CrossPromer, ErzyNetWebBot, ROCKET | PROMOTION, Autobots Promotions, PR4PR, Free Promoter Bot, CrossPromotion Robot, LinkMyChannel, Member Swap Bot, Heaven Promotion and InfoHub Networks.

The 125-community list includes, among many others, the free-PR groups `@ifreepr`, `@prchatik`, `@prbirza1`, `@p1rchat`, `@reklamabesplatnoz`, `@freeprtalk`, `@PR_Free_chat`; crypto-specific leads `@cryptoadminsVP`, `@free_promotion_airdrop_links`, `@addyourreferral`, `@marscatglobal`; and analytics/business communities. The complete handles, URLs, categories and status fields remain in `distribution/targets.json`; do not duplicate this register into a second competing list.

## Existing two-bot system (already inspected)

- First publisher: `/root/crypto-bot-farm/main.py`, cron every 15 minutes, reads 12 RSS feeds and publishes to owned `@cryptoping_ru`.
- Second service: `/opt/telegram-growth/group_bot.py`, systemd `crypto-group-bot.service`; it extends the original group bot and has the Publisher pipeline.
- The two paths use the same Bot API identity/config; `config.py` and `data` in the second repo are symlinks into the first project's live directory.
- Existing second-project Bot API publisher is the appropriate implementation for an external public group **only when the bot is already a member and Telegram confirms send permission**. It must not auto-join or request admin rights.
- There is no reason to create a third Telegram bot or rebuild the basic Bot API sender.

## Public GitHub projects inspected

### 1. Best reuse candidate for a richer RSS/news pipeline
[`ispy4you/auto-telegram-news`](https://github.com/ispy4you/auto-telegram-news) — MIT, public, not archived, Python 3.12+, current README describes a production-oriented self-hosted MVP.

Includes Telegram source ingestion via Telethon, realtime listener + scheduler fallback, exact/fuzzy/semantic deduplication, AI post generation, per-target routes and schedules, Bot API publication via aiogram, retry tracking, admin panel, audit log and Docker deployment.

**Fit:** useful as a donor/reference if we decide to replace or substantially upgrade the first RSS-only collector. It is not a drop-in for external group promotion: publishing targets are channels where the bot has posting access, and it introduces PostgreSQL, Redis/arq, Docker, a Telethon user session, and an AI gateway. It would be a significant migration, not a quick install. Do not deploy over the current live publisher without a migration plan.

### 2. Channel cross-promotion manager
[`tytsxai/channel-promo-bot`](https://github.com/tytsxai/channel-promo-bot) — MIT per its README, but repository is archived.

Supports channel submission, admin approval, AI classification, scheduled reciprocal promotions, SQLite locking, health checks and systemd templates.

**Not a fit for the owner's fixed constraint:** the README explicitly requires the bot to be in participating channels with posting rights, and submitters must be channel admins/owners. It is archived. Do not adopt.

### 3. Forwarding / routing bot
[`kynoze/Auto-Post-Bot`](https://github.com/kynoze/Auto-Post-Bot) — GPL-3.0.

Supports one-to-many/many-to-one routing, media filters, captions, deduplication and forwarding through either a bot or connected Telegram account. Its setup requires API_ID/API_HASH, MongoDB and encrypted Telegram sessions; the README requires target-chat admin/owner for rule creation.

**Not a fit:** connected-user-account/MTProto forwarding is not the unattended mass-posting route we want, and its target access requirements do not solve the no-admin constraint. GPL-3.0 also brings copyleft obligations if distributed as a derivative.

### 4. Lightweight repost bot
[`Polinanime/TelegramAutoChannel`](https://github.com/Polinanime/TelegramAutoChannel) — public small project; RSS/channel repost features and frequency controls are described, but not enough evidence of production readiness or no-admin group distribution. Not selected.

## Decision

No inspected GitHub project is a safe, direct drop-in for automated posting into arbitrary third-party groups without joining them or receiving permissions. Most channel cross-promotion bots require posting rights in participating channels; forwarding projects that use a user session move into MTProto/userbot territory.

**Reuse decision:** keep the existing two-project deployment. Do not build another bot. Reuse the 125-community inventory and 23-network inventory. The only code gap to evaluate is whether the existing second project's publisher can use already-joined public groups under ordinary-member send permissions, and whether the actual target registry is correctly wired to it. Separately, evaluate Onflow / Adpact / Trigram / TelegrAd as opt-in swaps for our own channel, reading each current free-plan and permission requirement before connecting.

No code, service, cron, database rows, or Telegram messages were changed during this audit.


## Live wiring inspection — 2026-11-04

The discovery inventory is imported into the Publisher DB, but not all 125 records become publish targets:

- Registry: 125 community records.
- Publisher metadata: 119 records.
- Six records are invite-only URLs (t.me/+... or joinchat/...). publisher/links.py deliberately rejects invite links because it accepts only public usernames.
- Publisher targets: 120 rows total = 94 groups pending + 25 channels pending + 1 owned group approved.
- No external group is currently approved/member-confirmed. No external Bot API publication is therefore presently possible.
- publisher/cli.py exposes import-catalog; repository grep found no automatic scheduled import. The current DB already contains the 119 imported public targets.

The existing implementation already contains the required ordinary-member route:
- group_bot.py:on_bot_chat_membership receives MY_CHAT_MEMBER.
- On membership status member, administrator, creator, or restricted with is_member=true and can_send_messages=true, it calls review_target(..., approve, allowed, ...) automatically.
- On left / kicked, it pauses an approved target.
- publisher/telegram.py:publish_draft_to_target accepts ordinary group membership and checks current live send permissions before each send. External fan-out is restricted to group targets; channel targets are not used in that route.

**Actual blocker:** the bot has not been added as an ordinary member to any of the 94 candidate public groups (no external approved rows). The code path is already present; do not rebuild it. The next work is to reconcile the 94 public group candidates and determine the permitted, practical way for the bot to be added as an ordinary member where appropriate. Do not ask for admin promotion. The six invite-only entries need their public usernames or should remain outside the Bot API target list.
