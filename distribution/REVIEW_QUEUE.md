# CryptoPing RU: first manual review queue

This is a prioritization aid for the existing discovery inventory, not an approval list.
Every candidate remains `pending` with `promotion_policy=unknown` until a human checks
the current Telegram rules and records explicit permission evidence.

## Review order

### Priority 1: crypto / Web3 relevance

| Catalog ID | Community | Audience / fit | What must be verified |
|---|---|---|---|
| `cryptoadmins-vp` | [Криптоадмины - Реклама/ВП/Подборки](https://t.me/cryptoadminsVP) | RU crypto admins, cross-promotion, channel roundups; catalog snapshot: 7,111 members | Direct Telegram preview could not be retrieved in this check. Existing catalog description mentions advertising and cross-promotion, not confirmed free placement. Verify current pinned rules, reciprocal-post format, bot-authored posts, frequency and anti-flood limits. |
| `free-promotion-airdrop-links` | [Free Promotion Group | Crypto Promotion | Referral Links](https://t.me/free_promotion_airdrop_links) | Crypto, airdrops and referral links; Telegram preview showed 408 members on 2026-10-31 (catalog snapshot: 492; another search preview: 441). | Public preview confirms the group topic and join link, but exposes no posting rules. Member counts differ across snapshots. Verify whether channel introductions are allowed (not just referral links), free-post conditions, moderation and bot policy. |
| `marscatglobal` | [MarscatGlobal](https://t.me/marscatglobal) | English crypto / Web3 promotion; directory snapshot: 36,658 members, 562 messages / 30d and 40 active writers in the current directory listing. | Direct Telegram preview could not be retrieved. Directory describes discussion and promotion services for crypto/Web3 projects, but does not establish free posting. The inventory's 716 messages / 30d differs from the current listing. Verify free terms, external news-channel eligibility and audience quality before spending time here. |
| `nftconfessionn` | [NFT CONFESSION](https://t.me/NFTconfessionn) | RU NFT / project promotion; directory snapshot: 2,567 subscribers, 1,736 posts / 30d, reported reach 60 and ER 2.3%; subscriber trend -5. | Direct Telegram preview could not be retrieved. Directory confirms project promotion but the audience is NFT/confession-oriented, not clearly crypto-news focused. Low priority until channel fit and free submission rules are confirmed. |

### Priority 2: Russian-language organic promotion

| Catalog ID | Community | Audience / fit | What must be verified |
|---|---|---|---|
| `freeprtalk` | [FREE PR - GROUP](https://t.me/freeprtalk) | General free promotion; 1,749 members | Confirm pinned rules, whether crypto/finance content is accepted and whether a bot may post. |
| `p1rchat` | [ВзаимоПиар, Бесплатный пиар](https://t.me/p1rchat) | RU cross-promotion; 9,760 members | Exact reciprocal-posting conditions, frequency, topic restrictions and bot permission. |
| `prchat-cis` | [Взаимный Пиар | СНГ](https://t.me/PRchat) | RU-speaking Telegram channels; 3,282 members | Read pinned rules and `#правила`; establish whether free posts are possible without buying an ad service. |
| `pr-chat-engovatova` | [Взаимный пиар и нетворкинг чат](https://t.me/PR_chat_by_engovatova) | Scheduled self-promotion / networking; 515 members | Confirm the currently valid allowed days, post format, crypto topic fit and whether bot-authored messages are accepted. |
| `freereklchat` | [Бесплатная реклама](https://t.me/freereklchat) | RU free-advertising / PR chat; 989 members | Verify that the free route is genuinely free, current posting rules, finance/crypto restrictions and bot policy. |

## Public-source check: 2026-10-31

This is a limited public-web check, not a review of in-chat pinned messages or private moderator instructions. Telegram previews are unavailable for some candidates. Public directory statistics are snapshots and may disagree with the discovery inventory; treat them as directional, not audited analytics. The Telegram preview for `free_promotion_airdrop_links` showed 408 members, while the discovery record had 492 and a separate search preview had 441. This discrepancy is recorded rather than silently choosing one number.

Sources checked: [Telegram preview for Free Promotion Group](https://t.me/free_promotion_airdrop_links), [ChatCrawler crypto advertising directory](https://chatcrawler.link/ru/c/t/marketing/telegram_ads?lang=en), [ChatCrawler Russian promo-exchange directory](https://chatcrawler.link/ru/c/t/telegram/promo_exchange/channels).

No source checked here establishes explicit moderator permission for CryptoPing RU, free publication terms, or permission for bot-authored posts. All four candidates remain unapproved.

## Partnership lead, not a free placement

- [CRYPTO PARTY](https://t.me/CryptoPartyCrew) (`cryptopartycrew`): relevant RU crypto / airdrop / Web3 audience, catalog snapshot 15,658 members. The catalog records collaboration contacts, including a contact labelled "manager (без оплаты)", but does not establish free publication or permission to post. Treat it as an opt-in partnership conversation only. No post until terms are explicit.

## Manual review checklist

For each candidate, inspect the live group/channel and record:

1. Is the community currently accessible and active?
2. Are channel promotions explicitly allowed, not merely discussion or referral links?
3. Is the free route explicit? Exclude paid placements from this workflow.
4. Is CryptoPing RU's crypto / Web3 / airdrop news topic accepted?
5. Are posts from bots or automated publishers allowed? If not stated, ask a moderator.
6. What are the format, frequency, cooldown and anti-spam requirements?
7. Save the exact rules message/link or explicit moderator response as permission evidence.

Use `python -m publisher list-targets` to find the numeric target ID (the output includes
the catalog ID), then `python -m publisher show-target --id N` to inspect its source
record. Do not run `review-target --decision approve` until the permission evidence is
explicit and current.

## Scope boundary

The current Publisher is a local review and dry-run planner. It does not join groups,
scrape Telegram, contact moderators, send messages, or use an MTProto session.
