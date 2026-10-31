# CryptoPing RU: first manual review queue

This is a prioritization aid for the existing discovery inventory, not an approval list.
Every candidate remains `pending` with `promotion_policy=unknown` until a human checks
the current Telegram rules and records explicit permission evidence.

## Review order

### Priority 1: crypto / Web3 relevance

| Catalog ID | Community | Audience / fit | What must be verified |
|---|---|---|---|
| `cryptoadmins-vp` | [Криптоадмины - Реклама/ВП/Подборки](https://t.me/cryptoadminsVP) | RU crypto admins, cross-promotion, channel roundups; catalog snapshot: 7,111 members | Whether free reciprocal posts are allowed, accepted formats, bot-authored posts, frequency and anti-flood limits. The public description mentions advertising and cross-promotion, not a confirmed free placement. |
| `free-promotion-airdrop-links` | [Free Promotion Group | Crypto Promotion | Referral Links](https://t.me/free_promotion_airdrop_links) | Crypto, airdrops and referral links; 492 members | Whether a channel introduction is allowed, or only individual referral links; moderation, anti-scam rules and posting limits. |
| `marscatglobal` | [MarscatGlobal](https://t.me/marscatglobal) | English crypto / Web3 promotion; 36,658 members | Whether free posts exist, whether external news channels are accepted, and whether the audience is active and relevant. Directory description alone is not permission. |
| `nftconfessionn` | [NFT CONFESSION](https://t.me/NFTconfessionn) | RU NFT / project promotion; 2,567 members | Whether a crypto-news channel fits the community, free submission method, current activity and moderation rules. |

### Priority 2: Russian-language organic promotion

| Catalog ID | Community | Audience / fit | What must be verified |
|---|---|---|---|
| `freeprtalk` | [FREE PR - GROUP](https://t.me/freeprtalk) | General free promotion; 1,749 members | Confirm pinned rules, whether crypto/finance content is accepted and whether a bot may post. |
| `p1rchat` | [ВзаимоПиар, Бесплатный пиар](https://t.me/p1rchat) | RU cross-promotion; 9,760 members | Exact reciprocal-posting conditions, frequency, topic restrictions and bot permission. |
| `prchat-cis` | [Взаимный Пиар | СНГ](https://t.me/PRchat) | RU-speaking Telegram channels; 3,282 members | Read pinned rules and `#правила`; establish whether free posts are possible without buying an ad service. |
| `pr-chat-engovatova` | [Взаимный пиар и нетворкинг чат](https://t.me/PR_chat_by_engovatova) | Scheduled self-promotion / networking; 515 members | Confirm the currently valid allowed days, post format, crypto topic fit and whether bot-authored messages are accepted. |
| `freereklchat` | [Бесплатная реклама](https://t.me/freereklchat) | RU free-advertising / PR chat; 989 members | Verify that the free route is genuinely free, current posting rules, finance/crypto restrictions and bot policy. |

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
