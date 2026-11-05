# CryptoPing RU — public feed quality audit

**Audit date:** 2026-11-04  
**Public source:** https://t.me/s/cryptoping_ru  
**Tool:** scripts/audit_public_channel_feed.py  
**Raw result:** docs/CONTENT-AUDIT-2026-11-04.json

## Snapshot

| Measure | Result |
|---|---:|
| Public posts sampled | 100 |
| Post ID range | 6207–6306 |
| Time span | 55.0 hours |
| Estimated publication rate | 43.6 posts/day |
| Mean view counter | 1.9 |
| Median view counter | 2 |
| Exact repeated external source URLs | 0 |

This is a snapshot of Telegram's public view counters, not a measure of unique readers, retention or referral conversions. The public channel currently has 23 subscribers according to the Bot API check recorded in this session.

## Candidate repeated stories

Exact article URLs did not repeat in this sample. However, the source feed contains multiple articles about the same underlying event from different publishers. The audit script compares source headlines (the text after “Оригинал:”), not entire posts, and reports likely pairs for editor review.

| Event cluster | Post IDs | Why it looks repetitive |
|---|---|---|
| Stellar Protocol 30 / Bell testnet upgrade | #6304, #6284 | Two publisher headlines with 0.93 title similarity about the same upgrade and mainnet vote. |
| Ethereum post-quantum transition targeting 2028 | #6303, #6302, #6289 | Three headlines about the same target year / post-quantum roadmap. They may contain different details, but should be combined or explicitly differentiated. |
| Coinbase / New Jersey staking order and lawsuit | #6301, #6300, #6256, #6254, #6248, #6247 | Six related headlines on the same legal reversal and restoration of staking access. |
| BitGo / Stacks Bitcoin staking | #6295, #6275 | Two reports on the same BitGo / Stacks staking product development. |
| Binance hack and stolen-fund recovery | #6306, #6271, #6260, #6264, #6224 | Multiple successive articles on the same hack, fund movement, recovery and coverage. Not necessarily duplicates, but should be sequenced into one evolving story. |
| Aztec network upgrade | #6270, #6269 | Two headlines about the same Aztec upgrade, likely different angles. |
| Tom Lee / Binance hack commentary | #6266, #6235 | Similar headline angle referencing the same Tom Lee comment. |

The detector is a candidate generator, not an automatic truth filter. The similarity threshold can produce false positives when stories share broad terms. A human/editor should compare the source articles before suppressing or merging anything.

## What this means

At roughly 44 posts/day with a median public counter of two views, raw posting volume is not producing visible reach. Adding more posts at the current rate risks making the feed noisier without increasing reader value.

The strongest immediate improvement is not more automation. It is story-level editorial control:
1. Group incoming articles by event, not only by exact source URL.
2. Keep one primary story record for each event.
3. Update that story only when a later report adds a material new fact, official statement, correction or status change.
4. When multiple publishers report the same event, use one post with a short comparison and links to sources, rather than separate near-identical headlines.
5. Prioritize material changes, security incidents, protocol upgrades, regulation and useful educational explainers over repetitive low-signal promotions/airdrops.
6. Add an original Russian explanation: what happened, what is confirmed, why it matters and what remains uncertain.

## Proposed controlled test (not deployed)

Run a seven-day shadow test on a copy of the latest source feed:
- calculate exact URL duplicates;
- normalize source headlines and form event clusters;
- let the model suggest merges, but require a human/editor to confirm the cluster;
- draft one concise Russian summary per event;
- compare candidate post volume with the current schedule;
- score the candidate output for factual traceability and relevance.

A starting editorial target to discuss is 6–10 strong posts/day plus one digest, rather than 40+ headlines/day. This is a proposal, not a live configuration change. Do not alter the production scheduler or auto-publish policy until the shadow test is reviewed and the user explicitly approves a rollout.

## Limitations

- Only the latest 100 public posts were sampled.
- Public view counters can lag and do not reveal unique readers or subscribers gained per post.
- Headlines are translated and may differ despite describing the same event.
- Story-similarity flags are not proof of duplicate content.
- No changes were made to production posts, database rows, scheduler or publishing logic during this audit.
