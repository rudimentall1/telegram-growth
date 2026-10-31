# Organic distribution campaign ledger

The campaign ledger is the evidence record for manual, permission-based organic placements. It is separate from targets.json, which is only a discovery inventory.

## Status meanings

- candidate: discovered only; no current permission is implied.
- rules_checked: current in-chat rules reviewed and decision recorded; this is not posting approval.
- permission_confirmed: a human confirmed that this specific placement is allowed, with dated evidence and reviewer.
- published: the authorized post exists and has a post URL, date, campaign source key and tracked invite link.
- measured: post-publication observations are recorded. Views and Telegram join events are observations, not click counts.

Allowed permission decisions: approved_for_manual_post, not_allowed, needs_clarification. Only approved_for_manual_post permits progression to permission_confirmed.

## Operating sequence

1. Create a ledger record with a unique record_id and the original target_id.
2. Review the current pinned/in-chat rules. Record rules_checked_at, a direct rules_evidence_url permalink, rules_checked_by and permission_decision. A public group preview or directory description is not evidence that the rules were checked.
3. For an approved target, record the exact permission_evidence_url, who confirmed it and the date. A public directory description or old discovery note is not proof of current permission.
4. Create a unique bot invite link with /growthlink wave1_targetkey before a permitted post. Record the returned link and source key.
5. A human publishes the post. Record the public post URL and date. This workflow does not post to third-party communities.
6. Record views at 24 hours and 7 days where visible, attributed joins and observed leaves. Add D7 retained only after the cohort matures and relevant membership events were observed.

## First-wave public preview review (2026-10-31)

Public Telegram previews were checked for the five seeded candidates. The ledger records the preview date, a short description and the public preview URL for each target. This is discovery evidence only.

- @ifreepr: preview describes a free-advertising group for channels, groups and bots.
- @prchatik: preview advertises free and mutual promotion, links to related promotion channels, and also points to a price list and paid-placement contact.
- @prbirza1: preview describes a free mutual-promotion chat, links to related promotion channels, and also points to a price list and paid-placement contact.
- @p1rchat: preview explicitly invites users to publish posts in a free mutual-promotion chat and provides an admin/ban-contact route.
- @reklamabesplatnoz: preview advertises free placement for projects, websites, Telegram channels, products and services, and claims no bots or fake views.

The public previews do not expose enough information to verify current pinned rules, topic restrictions, post frequency limits, or whether a specific CryptoPing RU post is allowed. Therefore all five records deliberately remain candidate. No group was joined, no administrator was contacted, and no post was published. The next gate is a human review of the current in-chat rules and, where unclear, explicit moderator permission.

## Validation

Run:
    python scripts/validate_campaign_ledger.py
    python -m unittest discover -s tests -v

The validator is local and read-only. It checks evidence gates, dates, URLs, unique record IDs and non-negative metrics. It does not browse targets, contact administrators, create invite links, publish posts or access the production bot/database.

## Measurement limits

Telegram Bot API does not expose ordinary invite-link click counts. attributed_joins means join events attributed by the bot to the recorded invite link; it is not clicks or guaranteed unique reach. D7 retention must be interpreted against observed event coverage and the cohort definition documented by the retention report.

## Importing selected candidates

Use the seed helper to copy exact registry IDs into the ledger. It is a dry run unless --write is supplied:

    python scripts/seed_campaign_ledger.py --target-id ifreepr --target-id prchatik
    python scripts/seed_campaign_ledger.py --target-id ifreepr --target-id prchatik --write

The helper is idempotent and rejects unknown or duplicate registry IDs. Imported records are always candidate status. It copies discovery evidence only; it does not infer current posting permission, join a group, contact an admin, or publish anything.
