# CryptoPing RU: first-wave organic distribution plan

**Prepared:** 2026-10-31  
**Repository baseline:** `main` at `7ad6183048d901610e6da2fb4019cb152c023ec4`  
**Scope:** free, permission-based acquisition only. This plan does not claim that any external group has been joined, any post has been published, or any subscriber has been acquired.

## Current verified state

- `distribution/targets.json` contains 23 promotion networks, 125 communities and 26 directory candidates.
- The 125 community records are discovery evidence, not a permission grant. The current inventory marks 16 as `discovered_not_joined`, 81 as `discovered_rules_need_review`, 18 as `needs_verification`, and the remaining records as other unverified discovery states.
- 9 of the 125 community records have no `checked_at` date; the other 116 are dated 2026-10-28 or 2026-10-29. A date on a discovery record does not establish that current in-chat rules or posting permission were verified.
- The main README documents the existing `/growthlink` attribution command and the opt-in reciprocal cross-promotion network. The latter still needs real partner owners to join before it can generate exchanges.
- The TGFind workflow is configured to submit and then look up `@cryptoping_ru`. A configured workflow is not proof of a successful listing; the Actions run and public lookup must be checked before claiming it is live.

## First-wave shortlist

These are candidates for a human rule check and a small, measured test. Public descriptions are not a substitute for reading pinned rules and current moderator instructions.

| Order | Target | Why it is worth checking | Gate before posting |
|---|---|---|---|
| 1 | [@cryptoadminsVP](https://t.me/cryptoadminsVP) | Strongest topical match: crypto, channel admins, advertising offers and cross-promotion are explicitly mentioned. | Confirm free posts are permitted, frequency limits and whether admin approval is needed. |
| 2 | [@ifreepr](https://t.me/ifreepr) | Public description explicitly says free advertising of channels, groups and bots. | Read pinned rules; check whether crypto/finance content is allowed and whether a post template is required. |
| 3 | [@prchatik](https://t.me/prchatik) | Public description points to free PR and mutual-promotion communities. | Identify the exact permitted posting destination and current rules; do not infer permission from linked groups. |
| 4 | [@prbirza1](https://t.me/prbirza1) | Public description labels it free PR and mutual promotion. | Check current rules, spam limits and topic restrictions. |
| 5 | [@p1rchat](https://t.me/p1rchat) | Public description explicitly invites promotional posts. | Check whether crypto projects and channel links are allowed; follow the required format. |
| 6 | [@reklamabesplatnoz](https://t.me/reklamabesplatnoz) | Public description offers free advertising for projects and Telegram resources. | Check current rules, moderation and whether a free post is actually available. |
| 7 | [@katalogtelegramkanalov](https://t.me/s/katalogtelegramkanalov?before=27) | A published post invites channel owners to submit topic, link, reach and subscriber count for free mutual promotion. | Reply only in the specific submission thread/post and follow its instructions. |
| 8 | [@TGvzaim](https://t.me/TGvzaim) | Public description mentions free channel/group promotion. | Check if the mechanism requires reciprocal subscriptions or engagement; reject artificial-engagement tasks. |

## Publication rules

1. No unsolicited DMs, scraping member lists, mass-joining, mass-commenting or repeated reposting.
2. No bot is added as an administrator to a third-party group as part of this plan.
3. No posting until the current pinned rules and the exact permitted location are checked.
4. No fake subscribers, forced subscriptions, reaction farms, view exchanges or engagement manipulation.
5. One test post per approved destination. Respect its cooldown and stop immediately if moderators object.
6. Use a distinct Telegram invite link per destination via the existing `/growthlink <source_name>` command where the bot can create and observe the link. If it cannot, mark attribution as unavailable rather than inventing clicks.
7. Record baseline subscriber count, post URL/time, post views at 24h and 7d, attributed joins, observed unsubscribes and 7-day retention. Telegram does not expose invite-link clicks through the Bot API; do not report clicks unless an external analytics source provides them.

## Promo positioning

Use a useful, factual description, not profit promises:

> CryptoPing RU — русскоязычный канал о крипторынке, Web3 и важных событиях индустрии. Короткие разборы проектов, технологий и рисков без обещаний доходности. Подписка: https://t.me/cryptoping_ru

Before using the copy, check that the target community permits crypto/finance promotion. Adapt the wording to the community's required format; do not repost identical text repeatedly.

## Execution checklist

- [ ] Inspect current pinned rules for each candidate.
- [ ] Record the rule URL/message and moderator restrictions.
- [ ] Mark each candidate `approved_for_manual_post`, `not_allowed` or `needs_clarification` in the operating log.
- [ ] Create a unique `/growthlink` source for each approved destination.
- [ ] Publish one compliant test post manually or through an explicitly authorized posting interface.
- [ ] Capture evidence and read `/growthreport 7d` after the test window.
- [ ] Scale only destinations that produce attributable, retained subscribers.

## Evidence boundary

This document is a prioritization and operating plan based on the public descriptions already recorded in `distribution/targets.json`. It is not evidence that current rules were inspected, that an account was connected, that a placement was accepted, or that the channel listing is live.
