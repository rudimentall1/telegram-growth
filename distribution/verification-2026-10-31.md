# Free cross-promotion verification

**Checked:** 2026-10-31  
**Scope:** public first-party product pages and help documentation only. No account was created, no Telegram bot was started, no channel was connected, and no publishing permission was granted.

## Findings

| Platform | Free route | Confirmed conditions | Assessment |
|---|---|---|---|
| Trigram | Reciprocal channel post swaps | Official site says swaps are free for both channels, with no commission, no minimum subscriber count and no listing fee. Partners are matched by subscriber range, language and topics; both posts are published by the bot and checked for 24 hours. | **Priority A.** Best stated fit for a small channel. Live account flow and channel eligibility still need an operator check. |
| Onflow Ads | Reciprocal channel post swaps | Free plan is $0 and includes 5 new cross-promotions per month. Swaps are 1:1; bot publishes both approved posts and removes them after the agreed run. Public channels only; bot must be admin; account reliability score must be at least 5.0/10 (the guide says new accounts start at 8.0). | **Priority A.** Clear free quota and documented workflow. Check exact bot rights before connecting. |
| TelegrAd | Cross-promotions and keypads | Official site says getting started is free and the free plan includes the basics. Cross-promotion posts are published by the bot and checked for the agreed time. Setup instructions request post, edit, delete and invite-user permissions. | **Priority B / permission review.** Free route exists, but requested rights are broad. Do not connect until the app explains why invite-user and edit/delete permissions are necessary and whether narrower rights work. |
| Adpact | Reciprocal post swaps | Official site says swaps require no cash but use points earned in the app. The bot publishes and checks both posts; accepted swaps cost both channel owners points. | **Priority B.** Cash-free, not cost-free in effort/points. Check the points earning and spending rules in-app before committing. |

## Recommended order

1. Test Trigram's free cross-promotion workflow first. Its published terms explicitly include small channels and do not state a subscriber minimum or listing fee.
2. Test Onflow Ads next. Its free monthly initiation allowance is explicit and its moderation, scheduling and cleanup workflow is documented.
3. Keep TelegrAd on hold until its requested Telegram admin permissions are justified.
4. Use Adpact only after checking how many points a swap consumes and how reliably points can be earned without paid actions.

## Safety and measurement rules

- Do not grant any bot administrator access until its exact permission request is understood.
- Never enable paid placements, boosts, wallet funding or paid plans for this project.
- Do not accept a swap until both exact promo posts, target channels, publication time and retention period are visible and approved.
- Use a distinct tracked invite link for each platform/partner where Telegram permits it.
- Record baseline subscribers, post views, joins attributed to the link, and 7-day retention. Do not treat views or link clicks as subscribers.
- Keep all integrations marked `discovered_not_connected` until a real account connection and first verified delivery are evidenced.

## First-party sources

- Trigram: https://trigram.site/ru
- Onflow Ads free plan: https://onflowads.com/telegram/pricing
- Onflow Ads cross-promotion guide: https://docs.onflowads.com/cross-promo
- Onflow Ads FAQ: https://docs.onflowads.com/cross-promo/faq
- TelegrAd: https://telegrad.link/en
- Adpact: https://adpact.app/ru/
- Adpact cross-promotion guide: https://adpact.app/guides/telegram-cross-promotion/

## Evidence boundary

These findings verify what the platforms currently claim in their public first-party materials. They do **not** prove that a live account can register @cryptoping_ru, that a partner is available, that a post has been delivered, or that subscriber growth will result. Those require a real opt-in test and measured results.
