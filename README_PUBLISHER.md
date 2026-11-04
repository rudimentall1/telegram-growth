# CryptoPing RU Publisher

Publisher is an opt-in publication workflow integrated into the existing
`group_bot.py` application. It uses the same Telegram Bot API client and process;
it does not start a second polling process. Its review, draft and delivery state
lives in `data/publisher.db`, separate from the legacy growth database.

## Local setup and candidate intake

Requires Python 3.10+ and the repository dependencies.

```powershell
python -m publisher --help
python -m publisher import-catalog
python -m publisher list-targets
python -m publisher show-target --id 1
```

Imported candidates remain pending. Discovery descriptions and directory
snapshots are not permission to publish. A human must inspect current in-chat
rules and record explicit permission evidence.

```powershell
python -m publisher review-target --id 1 --decision approve --policy allowed --evidence "Rules message URL and moderator permission"
python -m publisher add-draft --title "CryptoPing RU" --text "A useful, relevant post with a transparent channel reference."
python -m publisher approve-draft --id 1
python -m publisher plan --draft-id 1
```

Permission review expires after 30 days. A target has a seven-day cooldown
after a successful publication. Pausing a target preserves its review history.

## Telegram operator commands

The following commands are registered on the existing bot and restricted by
the existing growth administrator check:

- `/pubhelp` - show Publisher commands.
- `/pubtargets` - show registered destinations and review state.
- `/pubdraft Title | message text` - create a draft.
- `/pubapprove DRAFT_ID` - approve a draft for publication.
- `/pubreview TARGET_ID allow | evidence` - record explicit permission.
- `/pubreview TARGET_ID reject | reason` - reject a destination.
- `/pubplan DRAFT_ID` - show eligible and excluded destinations.
- `/pubsend DRAFT_ID TARGET_ID` - send to one destination.
- `/pubsendall DRAFT_ID [AFTER_TARGET_ID]` - send a batch and continue from a stable target-ID cursor.
- `/pubdelivery DRAFT_ID TARGET_ID` - inspect delivery state.

A draft must be approved and the target must have a fresh human approval with
`promotion_policy=allowed` and non-empty evidence. Immediately before sending,
the bot resolves the public destination and checks its live Telegram membership
and administrator rights. Channels additionally require `can_post_messages`.
A destination whose Telegram type does not match the registered target kind is
blocked. Text-only posts are limited to Telegram's 4096-character text limit.

Bulk publishing is operator-triggered, sequential, limited to 20 target
attempts per command, and waits 1.2 seconds between attempts. If more targets
remain, the bot returns a continuation command with the last processed target
ID. Targets already sent are protected by the seven-day cooldown. There is no
background mass-post scheduler, automatic joining, scraping, unsolicited direct
messaging, or paid placement.

## Delivery safety and recovery

Every draft/target pair has one unique delivery record:

- `sent`: Telegram returned a message ID; repeat sends are blocked.
- `failed`: Telegram definitively rejected the request; an administrator may
  explicitly retry with `/pubsend` or `/pubsendall`.
- `unknown`: a network failure occurred after the send attempt; retry is
  blocked because Telegram may have accepted the post.
- `sending`: an in-flight or interrupted attempt; repeat sends are blocked.

Unknown outcomes require manual inspection in the destination before any
recovery decision. This avoids duplicate posts after ambiguous network errors.
Successful publication timestamps update the target cooldown. Public message
links are stored when Telegram exposes a public username.

## Tests

```powershell
python -m unittest discover -s tests -v
python -m compileall -q group_bot.py growth_db.py cross_promo.py publisher scripts
```

Telegram delivery tests use mocked Bot API responses. They verify permission
checks, target-kind matching, draft approval, stale-review rejection,
duplicate-send protection, cooldown behavior, manual retry of definitive
failures, and non-retry of ambiguous network outcomes. They do not claim that a
live bot has permissions in any real community; those rights must be verified
at runtime before the first actual post.

## Autonomous AI moderation

Captured posts from `@cryptoping_ru` are checked by the moderation model before
the bot approves or sends them to the owned community `@cryptoping_ru_chat`.
Only a high-confidence `allow` for `news`, `analysis`, or `education`
with no risk flags can pass automatically. Promotions, referrals, uncertain
claims, off-topic posts, and borderline cases are held. Clear phishing, wallet
theft, malware, impersonation, and fraud are blocked.

The model classifies the supplied text; it does not independently verify facts,
open links, or certify a project's claims. A successful model verdict is not a
fact-check.

Configure the service environment using `.env.example`:

- `OPENAI_API_KEY` - API Platform key.
- `CRYPTOPING_MODERATOR_MODEL` - defaults to `gpt-6-luna`.
- `CRYPTOPING_MODERATOR_TIMEOUT_SECONDS` - defaults to 30 seconds.

The API key is not included in this repository. ChatGPT subscriptions and API
Platform billing are separate. Without a valid API key, when the API times out,
or when the response fails schema validation, the post stays unpublished and
the error is recorded for retry after ten minutes. Final allow/hold/block
decisions are retained in `source_moderation_reviews` and visible to the bot
administrator through `/pubsources`.

The moderator uses the OpenAI Responses API with strict JSON-schema output.
The classifier is not a promise of perfect fraud detection. External
destinations remain subject to the separate permission and live-membership
checks described above.
