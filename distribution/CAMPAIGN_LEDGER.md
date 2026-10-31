# Organic distribution campaign ledger

The campaign ledger is the evidence record for manual, permission-based organic placements. It is separate from targets.json, which is only a discovery inventory.

## Status meanings

- candidate: discovered only; no current permission is implied.
- rules_checked: current rules reviewed and decision recorded; this is not posting approval.
- permission_confirmed: a human confirmed that this specific placement is allowed, with dated evidence and reviewer.
- published: the authorized post exists and has a post URL, date, campaign source key and tracked invite link.
- measured: post-publication observations are recorded. Views and Telegram join events are observations, not click counts.

Allowed permission decisions: approved_for_manual_post, not_allowed, needs_clarification. Only approved_for_manual_post permits progression to permission_confirmed.

## Operating sequence

1. Create a ledger record with a unique record_id and the original target_id.
2. Review current pinned rules and record rules_checked_at plus permission_decision.
3. For an approved target, record the exact permission evidence URL, who confirmed it and the date. A public directory description or old discovery note is not proof of current permission.
4. Create a unique bot invite link with /growthlink wave1_targetkey before a permitted post. Record the returned link and source key.
5. A human publishes the post. Record the public post URL and date. This workflow does not post to third-party communities.
6. Record views at 24 hours and 7 days where visible, attributed joins and observed leaves. Add D7 retained only after the cohort matures and relevant membership events were observed.

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
