# CryptoPing RU — reconciliation of the two bot projects

**Inspection date:** 2026-11-04  
**Host:** Gensyn2  
**Scope:** `/root/crypto-bot-farm` and `/opt/telegram-growth`  
**No production code, scheduler, service, database rows, or Telegram messages were changed during this inspection.**

## 1. Correct high-level architecture

There is one Telegram Bot API identity, `@crypto_source_farm_bot`, used by two different execution paths. These are not two separately-tokened Telegram bot accounts.

1. **RSS news publisher:** `/root/crypto-bot-farm/main.py`, launched by root crontab every 15 minutes. It fetches RSS feeds, filters headlines, translates titles and sends news directly to `@cryptoping_ru` using Bot API `sendMessage`.
2. **Long-running group/growth bot:** systemd service `crypto-group-bot.service`, currently launched from `/opt/telegram-growth/group_bot.py`. It polls Telegram updates and handles group replies, member tracking, growth commands, opt-in group promos, reciprocal channel cross-promotion, and the added Publisher module.

Both paths import the same `TELEGRAM_TOKEN` and the same `CHAT_ID` / `GROUP_CHAT_ID` configuration. The systemd service's config path is a symlink to the old project:
- `/opt/telegram-growth/config.py -> /root/crypto-bot-farm/config.py`
- `/opt/telegram-growth/data -> /root/crypto-bot-farm/data`

The new project therefore shares the old project's live config and database/state directory. Do not treat them as isolated deployments.

## 2. First project: existing RSS publisher

**Code:** `/root/crypto-bot-farm/main.py` (269 lines; old live directory has no `.git` repository).  
**Scheduler:** root crontab:
`*/15 * * * * cd /root/crypto-bot-farm && flock ... timeout ... venv/bin/python /root/crypto-bot-farm/main.py`

It uses 12 RSS endpoints:
- Focused: Cointelegraph NFT, AirdropAlert, NFTPlazas, Crypto.news testnet.
- General: Cointelegraph, Decrypt, Crypto Briefing, The Defiant, Crypto.news, PR Newswire crypto, Polymarket News, Satoshi.ru.

Processing:
- Fetch up to 20 entries/feed, HTTP timeout 10 seconds.
- Ignore already-seen URLs.
- Require title length at least 5 and reject a short list of sponsored-content words.
- General feeds must match topic keywords. The four focused feeds set `require_topic_match=False`, so they do not get that keyword gate.
- Reject items older than 3 days only when a publication/update timestamp exists. Missing or unparsable timestamps are accepted.
- Translate the **title only** with GoogleTranslator, then MyMemory as fallback. This is not an LLM editorial/research step.
- Publish a Telegram text containing emoji, translated headline, original headline and source URL. No article body extraction, event clustering, multi-source comparison, link verification or fact-checking occurs in this script.

Current stored counters:
- `source_stats.json`: 5,029 candidates found and 4,992 successful send responses cumulatively across 11 feeds.
- `seen.json`: 2,921 stored link entries, 2,918 unique entries at inspection. This file is capped to the last 3,000 entries, so it is not a complete publication history and cannot reconcile the cumulative send counter by itself.
- Last state-file modification observed: 2026-11-04 10:00 UTC.
- The script does not log a positive line/message ID on each successful send. Its cron log is therefore mostly errors, not a complete send ledger.

Observed feed reliability issues in `logs/cron.log`: repeated 403/429 responses, 502/500/404 responses, DNS failures and 10-second timeouts across several feeds (including Crypto.news, CryptoBriefing, The Defiant, NFTPlazas, PR Newswire and Satoshi.ru). The source-stat file has cumulative totals, not per-source last-success timestamps.

Relevant quality risks:
- URL-level deduplication only; different publisher URLs covering the same event can all be posted.
- `seen.json` is truncated to 3,000 entries.
- Missing publication dates bypass the age check.
- Focused feeds bypass the main topical keyword gate.
- No AI moderation or factual verification is called from `main.py`.
- No durable per-post delivery ledger or success log exists.
- A file-lock helper is defined, but the cron's actual overlap protection is the external `flock` wrapper.

The channel content audit on 2026-11-04 sampled 100 public posts over 55 hours: approximately 43.6 posts/day, median public view counter 2. The sampled feed contained multiple same-event clusters. This means the existing RSS publisher is active, but volume and relevance controls need improvement; adding another raw RSS firehose is not the right fix.

## 3. Original group bot and current second project

The original `/root/crypto-bot-farm/group_bot.py` was a separate long-polling process for the same Bot API identity. It handled:
- new-member welcome messages;
- `/help` and keyword auto-replies;
- channel `chat_member` updates and basic join/leave attribution;
- growth invite links and source reporting.

The Git project `/opt/telegram-growth` is the later tracked extension of that group/growth bot. It is the target of the active systemd unit. It has additional promotion/publisher modules, but it is **not** the RSS source collector.

Current runtime:
- `crypto-group-bot.service` is active.
- Main process executes `/opt/telegram-growth/group_bot.py`.
- The crontab RSS job remains separate and runs `/root/crypto-bot-farm/main.py`.
- Both use the same token; the RSS job makes outbound Bot API calls and does not run a second Telegram long-polling loop.

## 4. What the second project actually does today

### A. Group onboarding and analytics
The long-running process welcomes new group members, answers configured keywords, tracks observed member changes in the public channel, and provides `/growthlink`, `/growthreport`, and `/growthretention`.

Live database observations:
- Four growth events total: three joins and one leave.
- Three tracked invite links exist, including test/smoke-test and the owned-group promo link.
- These observations are not enough to claim reliable campaign acquisition attribution.

### B. Legacy opt-in group promotion
The `/allowpromo` route lets a group administrator explicitly authorize periodic channel promotion in that group. Its scheduler checks every 5 minutes; default cooldown is 72 hours.

Live DB contains exactly one enabled promotion target: our own `@cryptoping_ru_chat`. Journal confirms an automatic promo was sent there on 2026-11-04 at 07:53:32 UTC (message 7279). There are no external groups in this live table. This feature is working only on our owned group today.

### C. Reciprocal public-channel cross-promotion
`cross_promo.py` is a different mechanism:
- A channel owner/admin must add our bot to their **own public channel** as an administrator with posting rights.
- They then submit `/crosspromo_add @channel`.
- The CryptoPing RU administrator approves it.
- The five-minute scheduler chooses another active partner channel and posts a reciprocal channel recommendation, by default no more often than every 72 hours per channel.

Live DB contains exactly one active channel, our own `@cryptoping_ru`. The scheduler explicitly returns no due targets until at least two active channels exist. `crosspromo_deliveries` has zero rows. Therefore no external partner is currently participating and no cross-promotion has occurred.

This code is not Telegram Suggested Posts. It depends on the partner channel owner granting our bot channel-admin/post access. Do not confuse the two workflows.

### D. Publisher module
The Publisher module is operator-controlled and permission-checked:
- 120 destination records exist in `data/publisher.db`.
- One target, our own `@cryptoping_ru_chat`, is approved/allowed.
- The other 119 targets remain pending/unknown.
- External sends are not active. A human must review destination rules and the bot's live permission before an explicit `/pubsend` or `/pubsendall`.
- It does not auto-join groups, scrape private Telegram data, or send unsolicited DMs.

The module also has a 60-second job that attempts to process captured posts from our own channel and relay approved items to our own group. This is downstream of the RSS publisher; it is not the code that discovers or writes news to `@cryptoping_ru`.

At inspection:
- `source_posts` contained one captured item only: message 6218, title/body `/pubsources`, captured 2026-11-02.
- `source_moderation_reviews` contained zero rows.
- Drafts: one unapproved channel-intro draft and the archived `/pubsources` command draft.
- One delivery record is marked sent to our own group (message 7175).
- There is no evidence in this database that actual RSS news posts are being AI-reviewed and relayed through this Publisher pipeline.

The LLM moderator added in the second project is therefore not a pre-publication editor for the RSS feed. It only sits in the downstream captured-source-to-own-group path.

## 5. Additional organic distribution already configured

`.github/workflows/free-distribution.yml` schedules `scripts/submit_directory.py` daily at 09:17 UTC and on relevant pushes/manual dispatch. It targets the public TGFind directory and is intended to be idempotent. This is a directory submission workflow, not a Telegram public-channel posting network. The workflow file exists; this inspection did not query GitHub Actions run history.

## 6. What is actually missing for the user's distribution goal

The existing systems already:
- collect RSS headlines and publish them to our owned public channel;
- keep the existing owned group active with welcome/keyword responses;
- post our channel link into our own group periodically;
- track basic acquisition events;
- contain unfilled mechanisms for opt-in partner channels/groups;
- contain a permission-checked manual publisher for external destinations.

They do **not** currently provide an implemented route to submit a content post to an unrelated public channel for free without the partner granting our bot admin/post privileges. Telegram Suggested Posts / channel Direct Messages are not implemented in either codebase. The earlier shortlist of third-party channels was only based on public reach estimates; absence of a DM button in a web preview is not evidence of a ban on publications.

So the actual gap is external distribution and audience acquisition, not a missing RSS news bot and not the ability to publish to our own channel. Keep these as separate workstreams.

## 7. Safety and maintenance notes

- No code, service, cron schedule, DB, or live Telegram post was changed during this architecture inspection.
- Preserve the existing active RSS cron and long-running group bot unless a scoped change is tested.
- The first project directory has no Git metadata. Before editing `/root/crypto-bot-farm/main.py`, create a timestamped backup and bring the source under version control or otherwise maintain an inspectable patch.
- `/opt/telegram-growth` has an existing divergent Git branch (main ahead 3 / behind 8) and untracked `data/`; preserve both. Do not reset/rebase/merge/push without explicit reconciliation.
- The second project's `config.py` and `data` are symlinks into the first project's live directory. Do not replace or remove these links casually.
- Never reveal the Telegram token, API keys, or private user/member IDs.


## 8. Owner decision and implementation update (2026-11-04)

The owner explicitly rejected two old mechanisms:

1. Periodic self-promotion of @cryptoping_ru inside @cryptoping_ru_chat.
2. Reciprocal channel cross-promotion requiring our bot to be a channel
   administrator in third-party channels.

Both schedulers/command handlers have been removed from group_bot.py. The
cross_promo.py implementation and its tests have been deleted. The live
promotion_targets row was disabled (not deleted); the live crosspromo_channels
row was paused (not deleted) to preserve history.

The existing first bot remains unchanged. The second bot now has the following
source-to-distribution path:

1. Capture each new text/caption post from @cryptoping_ru.
2. Run the existing fail-closed AI moderation.
3. Publish an allowed news/analysis/education post into the owned group
   @cryptoping_ru_chat.
4. Append a target-specific invite link to the public CryptoPing RU channel;
   register generated links in growth attribution so channel joins can be
   associated with their destination.
5. After a successful owned-group delivery, send the news to every eligible
   external public group where Telegram confirms the bot is a member and can
   send messages. Membership events automatically enable/disable destinations;
   no separate human evidence-expiry gate or project-imposed cooldown is used.
   No external admin rights are requested.

No project-imposed daily, per-news, or destination cooldown caps. Every
eligible external group can receive each approved news item. Live Telegram
membership and send permission are checked before every send. Channels are
excluded from this automated external route. Targets are automatically enabled
when Telegram reports the bot joined; removed memberships are paused.

Owner request checked on 2026-11-04: automatically satisfy a destination's
required subscription before posting. This is not possible with the current bot
identity. Bot API has no join-chat operation; MTProto `channels.joinChannel` is
users-only; Telegram's `channels.inviteToChannel` reports bots can only be admins
in channels. Therefore, for a prerequisite group an authorized member must add
the bot as an ordinary member; a prerequisite broadcast channel cannot be joined
by this bot without excluded admin access. Do not silently switch to a userbot or
claim a user's membership as the bot's. Keep targets requiring an impossible
channel subscription non-sendable and record the reason. No unsolicited DMs or
repetitive mass posting.

### External membership check

A read-only Bot API membership audit started across the 95 group records in
publisher.db. Telegram returned status=left for the first 29 external groups
checked. The next request hit Telegram flood control (retry-after about 52s),
so the audit stopped. The remaining groups are unverified, not presumed
available. The only confirmed writable group remains our own @cryptoping_ru_chat.
No external message was sent.

### Current implementation files

- group_bot.py: no self-promo or cross-promo handlers/schedulers; source relay
  remains scheduled.
- publisher/telegram.py: ordinary-member group send support; channel posts still
  require channel admin post permission; automatic external delivery after the
  owned-group send.
- publisher/storage.py: target-specific channel referral-link table and
  delivery-history reporting; no daily counter is used to block publication.
- group_bot.py: my_chat_member handler automatically enables a public group
  when the bot joins and pauses it when the bot is removed.
- growth_db.py: idempotent referral-link registration for attribution.
- README.md, README_PUBLISHER.md, AGENTS.md, docs/DISTRIBUTION-STRATEGY.md:
  updated to match the owner's architecture.
- config.example.py and CI compile command: removed obsolete scheduler settings
  and cross_promo module references.

No first-bot RSS code, cron schedule, shared config symlink, or shared data
symlink was modified. No real Telegram publication was sent during tests.


### Final deployment verification

The refactor was deployed on 2026-11-04 at 10:44 UTC. The service is active and
the only scheduled job registered by the new process is
publisher-own-channel-autopublish. The first bot's 15-minute RSS cron is
unchanged. Full unit suite passed (125 tests); compileall and git diff --check
passed. There are currently zero approved external group targets and 94 pending
external group targets. Therefore the owned-group relay is active, but external
publishing will remain idle until the bot is added as an ordinary member to a
public group, current rules are checked, and that target is approved. No live
external post was sent.


## Owner correction — external distribution limits removed (2026-11-04)

The prior limits of 3 posts per 24 hours, one group per news item, and a
seven-day destination cooldown were assistant-invented and are removed. Manual
permission-evidence expiry is also removed. When Telegram reports that the bot
joined a public group, that group becomes eligible automatically. Each send
still performs live Telegram membership and send-permission checks. A successful
owned-group publication is then delivered to every eligible external group.
Per-draft/per-target duplicate protection remains; Telegram's native API
rate/flood control is respected. No admin rights, auto-joining, or userbots.
