# CryptoPing RU Publisher foundation

This Publisher module lives inside the existing `telegram-growth` repository. It is a separate review/planning subsystem and does not change the legacy RSS poster, Telegram group bot, cross-promotion scheduler, or growth attribution database.

## Current capability

- Register candidate Telegram groups/channels using canonical public usernames.
- Import candidate lists from CSV; normalize public t.me links and deduplicate usernames.
- Record a human review of each community's promotion rules.
- Approve a target only when promotion is explicitly allowed and permission evidence
  is recorded.
- Reject or pause unsuitable targets. Pausing preserves the candidate and its review history while immediately excluding it from plans.
- Save content drafts and mark them approved in the local SQLite database.
- Build a dry-run plan that excludes unreviewed, stale, prohibited, or recently used
  targets.

The planner performs no Telegram API calls and sends no messages.

## Run

Requires Python 3.10+ and only the Python standard library.

```bash
python -m publisher --help
python -m publisher add-target --kind group --handle https://t.me/community_name --rules-url https://t.me/community_name
python -m publisher import-candidates --csv candidates.csv
python -m publisher import-catalog
python -m publisher review-target --id 1 --decision approve --policy allowed --evidence "Rules explicitly allow one relevant promotional post"
python -m publisher list-targets
python -m publisher show-target --id 1
python -m publisher pause-target --id 1
python -m publisher add-draft --title "Airdrop checklist" --text "Useful original content with a transparent reference to @cryptoping_ru."
```

A draft must be marked approved in the database by an operator before planning. This
deliberate gate prevents an unreviewed draft from entering a publication plan.

```bash
python -m publisher plan --draft-id 1
```

Default database: `data/publisher.db`. Override it with the global `--db` option. The target list includes imported display name, language, discovery status and topic metadata where available. Use `show-target --id N` before review to inspect the full catalog description, source link, observed size, discovery status, notes and any separately recorded permission evidence. Use `pause-target` to suspend a previously reviewed target without deleting its record; a paused target is ineligible for planning.

The first manually prioritized review shortlist is in [distribution/REVIEW_QUEUE.md](distribution/REVIEW_QUEUE.md). It is a review queue only; none of its entries are approved.

The existing `distribution/targets.json` inventory is the canonical source for community discovery. `import-catalog` imports its `communities` array and preserves source metadata (name, language, topics, stated permission, member count, evidence URL and discovery status) in a separate metadata table. Imported targets always remain `pending` with `promotion_policy=unknown`; catalog descriptions are not treated as verified permission. Re-running the import updates metadata without duplicating targets.

CSV intake expects a header row with `kind,handle` and an optional `rules_url` column.
Accepted handles are public Telegram usernames (5-32 characters) or direct public
`t.me/<username>` / `t.me/s/<username>` links. Private invite links and non-Telegram
URLs are rejected. Import only registers candidates as `pending`; it does not verify
community rules or grant permission to post.

Example:

```csv
kind,handle,rules_url
group,https://t.me/example_group,https://t.me/example_group
channel,@example_channel,https://t.me/example_channel
```

## Policy

- Unknown rules are not permission.
- "Approval required" is not permission until a moderator explicitly grants it.
- A target is eligible only after a human records explicit permission evidence.
- Permission review expires after 30 days.
- A target has a seven-day cooldown after a recorded publication (publication
  integration is not part of this slice yet).
- Candidate intake is from the existing curated JSON inventory or CSV; no Telegram scraping or automatic discovery is enabled.
- This foundation intentionally has no MTProto session or automatic sender.

## Tests

```bash
python -m unittest discover -s tests -v
```
