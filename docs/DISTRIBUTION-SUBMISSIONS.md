# CryptoPing RU Distribution Submission Register

**Last checked:** 2026-11-04  
**Channel:** https://t.me/cryptoping_ru  
**Policy:** no external group admin rights for our bot; no paid placements or spam.

This is an operational register. A successful form/API response means the directory accepted a submission request, not that the channel is already published or generating traffic.

## Submitted

| Directory | Cost | Submission method | Receipt / reference | Current status | Next check |
|---|---:|---|---|---|---|
| [TeleSeeker](https://teleseeker.com/submit) | Free | Anonymous form, public channel URL only | Page returned HTTP 200 and “Submission received”; accepted `t.me/cryptoping_ru` | Background verification/indexing pending; site says usually within 24 hours. Immediate check of `https://teleseeker.com/c/cryptoping_ru` returned HTTP 404, so it is not yet verified as public. | Check listing again after 24 hours. Do not resubmit unless directory confirms the earlier request was lost. |
| [TGDirectory](https://telegramchannels.io/submit-channel) | Free | Anonymous JSON submission, public channel URL only | HTTP 201; `submitted=1`, `duplicates=0`, `invalid=0`; channel ID `cmw1wus2t00lky8o4drjiaeec` | `PENDING`; provider says AI pre-screen plus human review before public listing. Immediate `/channel/cryptoping_ru` request returned HTTP 200 but the first response slice did not establish a published listing. | Check the listing again in 1-2 days. Do not resubmit. |

## Evaluated, not submitted

| Directory / route | Reason | Decision |
|---|---|---|
| [TGMetrix](https://tgmetrix.com/en/add-channel/) | Free, but current form rules require at least 250 subscribers. Telegram Bot API reported 23 subscribers on 2026-11-04. | Not eligible yet. Recheck only after the public subscriber count reaches 250. |
| [TelegramGroups.co](https://telegramgroups.co/) | Basic listings exist, but CryptoPing falls in the crypto/finance category; its submit page showed a $49 one-time category fee. | Reject while budget is zero. |
| Groupsgyani | Public submission path redirects to account login/registration. | Hold; do not create another account just for a speculative listing. |
| TGLeads | Submission flow requires account login/registration. | Hold; revisit only if no-login submission becomes available and the directory quality is worth it. |
| [Telegram Channel Booster](https://t.me/TGChannelBooster) / `@TGDirectories` | Channel page advertises free listings, but the actual mechanism was not verified. Public preview of the linked feed showed low-quality generic channel-transfer posts rather than clear, targeted editorial promotion. | Low priority; do not submit until its exact free process and audience quality are verified. |
| TGMania | Basic listing is presented as free, but the visible directory contains mixed-quality entries. | Hold; do not prioritize over better-quality directories. |

## Rules

- Never send a duplicate submission while the original request is pending.
- Never pay for directory inclusion or featured placement without the user's explicit budget approval.
- Never provide private account details, API keys, bot tokens, or personal information to a directory.
- Keep the listing accurate: Russian-language crypto/Web3 news and educational explainers; no guaranteed-return claims.
- Check public subscriber count, profile presentation, and latest content before new submissions.
- Measure actual referral clicks and new Telegram joins; directory placement alone is not growth proof.

## Current channel distribution diagnosis (2026-11-04)

- Public Telegram Bot API count: 23 subscribers.
- Sample of the latest 100 public posts: view counters were mostly 2 per post, with some older items at 1-2. This is a snapshot, not a full retention or unique-reader metric.
- The sampled 100 posts span roughly 54 hours, equivalent to around 40-50 posts/day.
- Several subjects appear more than once within hours (e.g. multiple Ethereum post-quantum transition stories and two Coinbase/New Jersey staking stories).
- Most posts are headline/source-link style and add little channel-specific context in the visible snippet.

This points to a content-density and retention problem. More directory listings alone will not fix it. Before increasing promotion, improve deduplication, prioritization, source variety, and short original Russian summaries. Do not change production cadence or publishing rules without a separate explicit decision and tests.

## Next actions

1. Check TeleSeeker after its stated indexing window and TGDirectory after 1-2 days; update this register, never duplicate the pending requests.
2. Build a small shortlist of relevant Russian-language crypto/Web3 channels with actual editorial submission or Suggested Posts entry points. Do not infer DM availability from a generic `t.me/<username>?direct` URL alone.
3. Prepare one free, source-backed editorial suggestion for a specific channel only after its submission route is verified.
4. Design story-level deduplication using canonical source URL plus normalized title/event identity; test on a copy/sample before touching production.
5. Propose a lower-signal-volume content cadence and original summaries; measure joins, views and retention before changing production.


## Existing listing and further candidates (2026-11-04)

| Directory / route | Status | Notes |
|---|---|---|
| [TGFind](https://tgfind.net/en/resource/cryptoping_ru) | **Already listed** | Submit attempt returned `status=exists`; no duplicate created. Card showed 23 subscribers on 2026-10-28, rank 17,052 of 17,370 by members, one member-count observation. |
| [TeleNavo](https://telenavo.com/submit) | Not submitted | Free, moderator reviewed; form includes Cloudflare Turnstile. Privacy policy says submitter IP is stored with the listing metadata. Do not automate or bypass. Manual browser only if comfortable. |
| [TelegramDir](https://telegramdir.com/) | Not submitted | Free, manual review, community votes, but only 270 listings and sparse crypto category. Form has honeypot + form-open timestamp; do not automate around anti-abuse controls. |
| [TGbox](https://tgbox.cc/en/about/) | Not submitted | Free submit via DM to `@tgboxccbot`; directory mainly Chinese/English. Requires normal Telegram account to message bot. |
| [TG Compass](https://tgcompass.com/about) | Not submitted | Free directory, no-login browse, small editorial topic lists. Suggestions via `contact@tgcompass.com`, manually curated; most are not selected. No email sent. |

No further submissions were made while TeleSeeker and TGDirectory are still pending. See `docs/PROMOTION-PACK.md` for verified directory copy and manual submission text.
