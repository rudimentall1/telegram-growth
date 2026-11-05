# CryptoPing RU Distribution Strategy Without External Bot Admin Rights

**Owner constraint:** external Telegram group administrators will not grant our bot administrator privileges. This is not a route to negotiate repeatedly. No implementation may depend on it.

## Goal

Grow `@cryptoping_ru` and `@cryptoping_ru_chat` with free, permission-respecting distribution. Optimize for qualified readers interested in crypto/Web3, not raw views or spam volume.

## Channel matrix

| Route | Requires our bot as external admin | Permission/approval needed | Automation level | Priority |
|---|---:|---|---|---:|
| Telegram Suggested Posts to channels | No | Channel must enable DMs; owner approves each suggestion | Prepare automatically; submit from subscriber account / approved supported access | 1 |
| User-account posts in public groups | No | Current group rules must allow member posts | Research and prepare automatically; human posts manually | 2 |
| Editorial / directory submissions | No | Follow published submission process | Research and draft automatically; submit through stated route | 3 |
| Owned landing page + RSS + SEO | No | Control of domain/hosting | High, once domain is available | 4 |
| Organic contributions on Reddit and other communities | No | Community-specific rules | Draft and research automatically; publish selectively, no repetitive automation | 5 |
| Direct partner content exchange | No | Partner agrees to publish content themselves | Prepare assets and track partnership | 6 |
| Telegram Ads | No | Budget in TON; paid | Not a current zero-budget priority | Parked |
| External group Bot API posting as ordinary member | No admin rights; bot must already be a member | Current rules explicitly allow the content; Telegram confirms member send permission | Automated only for reviewed targets with strict caps | 2 |
| MTProto/userbot mass-posting | Not necessarily | Account/group restrictions; significant abuse risk | Prohibited for unattended promotion | NEVER |

## 1. Telegram Suggested Posts

This is the first workflow to test.

Telegram introduced Suggested Posts on 2025-07-01. Subscribers can suggest a post to a channel through the channel's Direct Messages interface. A suggestion can be free; payment in Stars or Toncoin is optional. The channel owner can accept, edit, schedule, or reject the proposal.

Official references:
- Product announcement: https://telegram.org/blog/checklists-suggested-posts
- Suggested Posts technical documentation: https://core.telegram.org/api/suggested-posts
- Bot/channel Direct Messages documentation: https://core.telegram.org/bots/features

Operational steps:
1. Find crypto/Web3 channels whose public profile exposes a Direct Messages entry point.
2. Confirm the channel accepts relevant editorial or community submissions; do not assume every channel wants promotions.
3. Generate a short, channel-specific suggested post. Lead with useful information, not an advertisement.
4. Include an unobtrusive source credit or channel link only where permitted.
5. Submit as a **free** suggested post from a normal subscriber account. Do not offer Stars or TON.
6. Record submission date, channel, content hash/title, and outcome. Do not resubmit the same rejected post.
7. If the channel accepts, record publication URL and track referral clicks separately.

Bot API note: Telegram documents that bots can send suggested posts to channel DM topics when they have the appropriate channel access. Do not treat that as universally available. First test with a destination that explicitly allows the bot's access, or use the user's normal Telegram client as the submission path. This does not require external group administrator privileges for our bot.

## 2. Public groups where ordinary members can post

Two distinct routes exist. A normal human account can post only where the rules
allow it. Separately, the Bot API can post to a group where the bot is already an
ordinary member and Telegram confirms that members can send messages. It does
not need administrator status. The bot cannot autonomously join a public group;
it must already have been added as a member.

**Required-subscription rule:** if a target group requires the publisher to join
another group first, an authorized member must add the bot to that prerequisite
group too; the existing `my_chat_member` handler then detects the membership.
If the target requires subscribing to a broadcast channel, the bot cannot join
as an ordinary subscriber: Telegram's MTProto `channels.joinChannel` method is
users-only, and `channels.inviteToChannel` reports `USER_BOT` because bots can
only be admins in channels. Since external channel admin rights are excluded,
such a target must remain non-sendable for this Bot API publisher. Do not use a
personal user session and mislabel its membership as the bot's.

Before enabling a Bot API destination, verify:
- the group is public and currently active;
- rules allow ordinary members to publish channel links or promotional/editorial posts;
- the rules do not prohibit bots, AI, crypto, referral links, or external channel promotion relevant to the proposed post;
- there is a clear posting cadence or designated promotion thread;
- no paid placement or reciprocal subscription is required unless the user explicitly chooses it.

Use a useful, discussion-relevant post. The bot publishes to every registered
public group where Telegram confirms that it is a member and has live permission
to send messages. No admin rights are required. Do not add arbitrary daily caps,
per-news destination caps, or per-target cooldowns; Telegram's actual API limits
apply. Per-draft/per-target duplicate protection remains to prevent accidental
repeat sends. Stop on Telegram permission errors or flood control. Never
auto-join, use userbots, or bypass group rules. Telegram's Terms and Spam FAQ
warn against spam and unsolicited advertising, and reports can limit accounts.

## 3. Editorial and directory submissions

Search for real submission mechanisms:
- channel catalogue submission forms;
- editorial/news tip email or web forms;
- community-created Web3 newsletters that accept links;
- public weekly "share your project/channel" threads;
- ecosystem event and resource directories.

A listing is not a promise of audience growth. Track acceptance, index status, link clicks, and any recurring contribution requirement. Never scrape private group members or send unsolicited mass DMs.

## 4. Owned surface: landing page, RSS and search

Inspect whether CryptoPing RU already controls a domain or public website. If not, do not purchase one without the user's explicit budget approval.

A minimal page should explain:
- what readers get (curated Web3/crypto news, explainers and opportunities);
- language and publication cadence;
- source/citation and risk-disclaimer policy;
- direct links to the Telegram channel and community;
- an RSS feed or public archive of selected posts.

Each post should be a useful standalone explainer or digest, not a thin page whose only purpose is repeating an invite link. Use stable canonical URLs and basic structured metadata only after the domain is confirmed.

## 5. Organic social/community participation

Use the user's existing accounts if available. First inventory platform/account access; do not assume accounts or credentials.

Recommended content packaging:
- one original research-backed explanation for the owned channel;
- a short summary for a social profile;
- a question or discussion prompt tailored to a relevant community;
- a link to a full source/article where allowed.

Reddit and similar communities require strict community-specific rules. Reddit's official guidance considers repeated unsolicited actions, mass-posting repeated content and promotional bots to be spam. Use genuine helpful contributions and designated promotion threads only.

## Measurement

Every destination or submission gets a record with:
- route type;
- platform and destination URL;
- permission source / current rules;
- required account (user or bot);
- free/paid status;
- submitted content ID and date;
- accepted / rejected / pending result;
- published URL;
- tagged referral link or UTM where appropriate;
- resulting clicks and joins if measurable.

Do not optimize for number of posts alone. Prioritize qualified joins and retention.

## Explicit exclusions

- Do not ask external group admins to make our bot an administrator.
- Do not request administrator rights in external groups. Ordinary bot membership
  is acceptable only when a group explicitly permits the bot and relevant posts.
- Do not attempt Bot API sends to external groups without confirmed membership,
  current rule evidence, and live send permission.
- Do not use unattended userbots, mass DMs, mass invites, repetitive link drops, or comment spam.
- Do not call a destination "free" unless the current terms say so.
- Do not claim a public catalogue description proves the current rules.
- Do not offer paid Telegram Ads or paid placements as the default while the project has no budget.

## Next execution order

1. Find 10-20 relevant Telegram channels with channel DMs enabled and review whether they accept free Suggested Posts.
2. Test one free submission manually from the user's normal Telegram account; record the response.
3. Audit external group records for existing bot membership and rule evidence;
   keep uncertain targets non-sendable. The bot cannot join groups autonomously.
4. Inventory currently controlled social accounts and any owned domain/site.
5. Build a small submission tracker and a content-pack generator before any further platform automation.

## Initial live leads checked on 2026-11-04

These are research leads, not automatic publishing permissions. No submission or message has been sent.

| Lead | Publicly visible evidence | Route without our bot admin | Current verdict |
|---|---|---|---|
| [TeleSeeker](https://teleseeker.com/submit) | Its submission page says any public Telegram channel/group/bot can be listed for free, with no login or ownership proof; live Telegram verification and indexing within 24 hours are claimed. | Submit the public @cryptoping_ru channel URL through the public form. | Strong first zero-cost directory test. Independent directory, not Telegram; indexing is not guaranteed traffic. Submission not yet performed. |
| [Telegram Channel Booster](https://t.me/TGChannelBooster) | Public channel page showed about 4,257 members and states free channel/group listing with bilingual tags and re-broadcast to @TGDirectories. | Follow its published free listing procedure once verified. | Promising, but actual submission steps, current activity and quality of resulting traffic still need checking. No listing submitted. |
| [CRYPTO PARTY](https://t.me/CryptoPartyCrew) | Public preview showed about 15.5K subscribers and listed advertising/collaboration contacts plus contacts labelled "manager (без оплаты)". | A direct, human partnership/content proposal to the listed contact; no bot rights. | Relevant audience, but the public page does not guarantee a free post. Treat as a partnership lead, not confirmed free inventory. |
| [@katalogtelegramkanalov](https://t.me/katalogtelegramkanalov) | Public page showed about 210 subscribers, manual moderation, and a linked free-promotion chat. The catalogue's own channel listing price is shown as 100 RUB. | Could investigate the separate free chat only if its rules permit ordinary member posts. | Weak audience and paid catalogue listing; do not pay. Check any separate free chat carefully. |
| [@katalogkanalow](https://t.me/katalogkanalow) | Preview showed about 46 subscribers; free mutual promotion is described for channels with at least 300 subscribers, while direct channel submission is shown as 50 RUB. | Free mutual-promotion eligibility only if the current threshold is met. | Stale/low-value lead, paid listing. Do not pay or prioritize. |
| [@cryptoadmincenter](https://t.me/cryptoadmincenter) | Public page showed about 612 members; it says direct resource advertising is prohibited and a pinned post costs 50 USDT. | None for direct advertising under the visible rules. | Reject for the current zero-budget plan. |

**Correction to an earlier conversational lead:** the prior mention of @cryptoadminsVP and an approximately 8K-member audience has not been substantiated by the exact-handle search. Do not use that claim or target without fresh verification. The similarly named @cryptoadmincenter is a different entity with paid pinned advertising and direct ads prohibited.

### New priority order

1. Verify and, after the user's go-ahead, submit the public channel to TeleSeeker. It requires no Telegram group membership and no admin rights.
2. Check the exact free submission path for Telegram Channel Booster; do not assume its bot or any external admin role is needed.
3. Prepare one concise, editorial-style partnership proposal for CRYPTO PARTY's listed manager; do not send without user approval.
4. In parallel, inspect candidate Telegram channels for a visible Direct Messages/Suggest Post path. Only channels with DMs enabled can receive Suggested Posts through that workflow.
5. Discard paid listings and placements while the budget is zero.


## Additional verified directory and editorial routes (2026-11-04)

- **TGFind already lists CryptoPing RU** at https://tgfind.net/en/resource/cryptoping_ru. A direct submit attempt returned `status=exists` and the page link rather than creating a duplicate. Its card showed 23 subscribers from its last check on 2026-10-28 and rank 17,052 of 17,370 channel listings by members. One count observation exists, so the trend is not calculated. This is an existing footprint, not a new submission.
- **TeleNavo** (https://telenavo.com/submit) says listings are free and manually reviewed. The form asks for public link, category, language, optional country/tags/description, and includes Cloudflare Turnstile. Privacy policy says it stores the submitter IP plus the public link and metadata. No submission was made; do not bypass Turnstile. The user can use the normal browser only if comfortable with that data handling.
- **TelegramDir** (https://telegramdir.com/) describes free submissions and manual review, with community voting. It is a small directory (270 total listings at inspection) with a small Crypto/Finance/Bots category. The form uses a hidden honeypot and a form-open timestamp, so do not automate around those anti-abuse controls. No submission was made.
- **TGbox** (https://tgbox.cc/en/about/) offers free listing via a private DM to `@tgboxccbot`, but the directory's interfaces are Simplified Chinese, Traditional Chinese and English. It requires a normal Telegram user to message the bot; our bot cannot be used as a cross-bot sender and no external group permissions are involved. No DM was sent.
- **TG Compass** (https://tgcompass.com/about) is free and no-login for browsing. It has a short hand-written Crypto & Finance topic list and says suggestions can be emailed to `contact@tgcompass.com`, but most suggestions do not make the edited lists. This is an editorial tip, not guaranteed listing.

Do not submit to every directory indiscriminately. Prefer the three outcomes with verified value so far: TGFind existing listing, TeleSeeker pending, TGDirectory pending. Check pending results before considering more entries.


## 6. First-party public-channel publishing (verified live, 2026-11-04)

The project already owns a public channel, `@cryptoping_ru`. A read-only Bot API check on 2026-11-04 confirmed `@crypto_source_farm_bot` is its administrator and has `can_post_messages=true`, `can_edit_messages=true`, and `can_delete_messages=true`. No message was sent during the permission check. Therefore, no new channel and no third-party permission are required to prove automated publishing.

Current implementation is reversed: `group_bot.py:on_source_channel_post` captures content already posted into `@cryptoping_ru`; `publish_captured_channel_posts` and `publisher.telegram.publish_captured_source_posts` then moderate and relay selected posts to the owned community `@cryptoping_ru_chat`. This does not create or ingest original news into the public channel.

Recommended build: free RSS/public-source intake -> source validation -> event-level deduplication -> Russian editorial summary with source links -> conservative scam/financial-risk moderation -> rate-limited publication into the owned public channel. Keep the existing channel-to-community relay intact. Shadow-test before changing cadence. The 2026-11-04 feed audit showed ~43.6 posts/day and median public view counter 2, so simply publishing more is not a valid growth strategy.

Important correction: the earlier channels `@gen_m`, `@mendeleevshina`, and `@slezisatoshi` were chosen by public reach estimates only. They were not established as channels that prohibit submissions. Lack of a visible Suggested Posts button in a web preview is inconclusive. Never label such channels prohibited without explicit policy evidence. The user should not be asked to manually repeat the same checks by default.


## Owner-supplied candidate inventory and anti-ban rules (2026-11-04)

See `docs/OWNER-SUPPLIED-DISTRIBUTION-LEADS-2026-11-04.md` for the full list of candidate RU crypto shilling/airdrop groups, analytics/startup communities, editorial bots, channels and blog platforms supplied by the owner. Treat these as discovery leads, not as verified open-posting destinations. The list's "free", "no moderation" and "any referral link" claims require current, destination-specific verification.

Publishing safety rules:
- Use official Telegram interfaces and supported Bot API workflows within documented limits. 30 messages/second is a ceiling, not a target; actual chat limits and Telegram flood-control responses take precedence.
- No unsolicited promotional DMs, mass messaging, or waves of identical external-link posts.
- Tailor content to the destination and publish referral links only where current rules explicitly allow them.
- Do not reject a destination without evidence, and do not mark it sendable based only on a public catalogue description.
- Investigate channel editorial bots / Suggested Posts separately from the channel's admin-only posting permissions. Prepare unique useful material rather than generic channel promotion.


## Owner decision — closed-group candidates reduced (2026-11-04)

The owner specified that only the former invite-only `piar-mega-news` candidate should remain, using the public handle `https://t.me/piar_mega`. The following five invite-only entries were removed from `distribution/targets.json`: `bookdialog`, `channel-sales-cross-promo`, `free-promotion-club-invite`, `free-promotion-link-share`, and `free-promotion-any-link`.

- `piar-mega-news` remains under its existing catalog ID, but its `url` and `evidence_url` now use `https://t.me/piar_mega`.
- Registry validates as JSON: 120 community entries, zero remaining invite-only `+`/`joinchat` community URLs, `piar-mega-news` resolves to the owner-supplied public username, and all five excluded IDs are absent.
- Ran `publisher.cli import-catalog`: processed=120, rejected=0.
- Read-only live DB verification: 121 total targets, 96 groups (including the owned group), 25 channels, 120 catalog metadata rows. New target row is id=121, kind=`group`, handle=`@piar_mega`, status=`pending`, policy=`unknown`, catalog_id=`piar-mega-news`.
- The new target is not yet approved or known to be a current member; do not publish until the public handle/group identity and current rules are verified, and the publisher bot is added as an ordinary member if allowed.
- No Telegram joins or posts were made. No service restart, code change, deletion of existing DB history, commit, or push. Git branch remains divergent; unrelated local changes were left untouched.


## 2026-11-04: owner-subscribed Telegram groups replaced

The owner supplied 72 lines, normalized to 66 unique public group usernames. The previous external group catalog and external group target rows were replaced by this list. Duplicate entries were removed. The original @TGvzaim/1 message URL is preserved as evidence; the destination username is @tgvzaim.

Preserved: all 25 Telegram channel catalog entries and database targets; the owned @cryptoping_ru_chat target and its existing publication history. The latter is required by the existing second-bot automatic publishing route.

The 66 external targets are registered as pending/unknown until Telegram sends a my_chat_member update confirming that the existing publisher bot has joined. The owner explicitly authorized CryptoPing RU news publication to this list. The publisher checks Telegram's live send permission before each delivery. Bot administrator rights are not required where ordinary members may send. No Telegram posts were sent during this registry update; no service restart was performed.

Counts: input lines=72, unique external groups=66, duplicates removed=6, channels preserved=25, owned group preserved=1.
SQLite backup: /root/crypto-bot-farm/data/publisher.db.bak-owner-groups-20261104
Catalog backup: /opt/telegram-growth/distribution/targets.json.bak-owner-groups-20261104

Owner-supplied external groups:
@ifreepr
@prchatik
@prbirza1
@p1rchat
@tgvzaim
@vzaim_pr
@reklamabesplatnoz
@vzaimopiar_chat
@chatik_piarvz
@vzaimnaya7
@cryptoadminsvp
@vzpodpiskachati
@vzpiarchatx
@vzchatpiar_vz
@piar_chatiku
@teamofpr
@vzaimnotiktok1
@instagram_aktivnost1
@vzaimnoe_pohmelie
@chati_piar
@piar_vzaimka
@piargrupa2
@pr_free_chat
@chat_pr_raskrutka
@vzaimnyipr
@piar17
@telegavzaimki
@piarta
@shat37
@mediaspampr
@vzaivpiar
@piar_chata
@piarchat00
@vzaimnyepodpi
@vzaimno_piarc
@addyourreferral
@piar_mega
@pr_freeee
@p1rchats
@freereklchat
@prprprchat
@piarix_chat
@advertising_piar
@freemarketru
@infobizz1
@w2_chat
@freelance_in_telegram
@marscatglobal
@chat_piarvz1
@freeprtalk
@p_rgroup3
@chat_piarj
@freelead
@chat_kovalev
@chatpetra_sineguba
@freelancechat2
@bisrocket
@smmspecialisty
@prchat
@vzaimnay_podpiskatg
@pr_chat_by_engovatova
@birzha_reklamy4
@byrzha_reklamy2
@birzha_reklamy5
@byrzha_reklami2
@birzha_reklamy23

