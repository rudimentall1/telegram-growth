# Telegram Growth

Telegram-бот для учёта источников привлечения подписчиков и отчётов по вступлениям/отпискам.

## Команды бота

- `/growthlink source_name` — создать отдельную invite-ссылку для кампании. Бот возвращает ссылку и готовый короткий текст для публикации.
- `/growthreport` или `/growthreport all` — сводка по всей истории.
- `/growthreport 7d` и `/growthreport 30d` — события за выбранный период плюс текущие известные активные участники по источникам.
- `/allowpromo` — команда администратора группы, чтобы добровольно включить автоматические промопубликации CryptoPing RU в этой группе.
- `/disablepromo` — выключить автопромо в текущей группе.
- `/promotetargets` — показать включившие автопромо группы; доступно администраторам основной группы.
- `/help` — краткая справка для участников.

Планировщик проверяет согласившиеся группы каждые `PROMOTION_CHECK_INTERVAL_MINUTES` (по умолчанию 5 минут) и публикует в каждой группе не чаще одного раза за `PROMOTION_INTERVAL_HOURS` (по умолчанию 72 часа). Для включения администратор целевой группы должен добавить бота и вызвать `/allowpromo`; одного наличия группы в реестре недостаточно. Для публикаций используется отдельная отслеживаемая invite-ссылка. Если Telegram отклоняет публикацию из-за прав или доступа, цель автоматически отключается. Данные хранятся в SQLite.

Команды управления привлечением доступны администраторам текущей группы; команды отчёта и управления списком целей дополнительно защищены проверкой администратора основной группы или `GROWTH_ADMIN_IDS`.

## Ограничения и точность атрибуции

- Telegram Bot API не показывает число кликов по invite-ссылкам.
- `growth_events` считает события вступления/выхода, а не уникальные клики или гарантированную конверсию.
- Активные участники по источникам — только пользователи, чьи изменения членства бот наблюдал и чью текущую invite-атрибуцию сохранил. Это не полное число подписчиков канала.
- Если Telegram не передал известную invite-ссылку в событии, вступление попадает в `unattributed`.
- Для создания ссылок и получения событий бот должен быть администратором канала с необходимыми разрешениями. В настройках Telegram должны приходить обновления `chat_member`.

## Локальная проверка

Тесты используют временную SQLite-базу и не требуют Telegram-токена:

```bash
python -m unittest discover -s tests -v
```

Проверка синтаксиса:

```bash
python -m py_compile group_bot.py growth_db.py
```

## Настройка

1. Установите зависимости из `requirements.txt`.
2. Скопируйте `config.example.py` в `config.py`.
3. Заполните `TELEGRAM_TOKEN`, `GROUP_CHAT_ID` и `CHAT_ID`.
4. Не добавляйте `config.py`, токены, SQLite-файлы и логи в Git.

## Развёртывание

Пока это исходный проект и тестовый каркас, не готовый установщик для существующего сервера. Не запускайте deployment поверх действующего бота до проверки резервной копии, конфигурации и поведения systemd.


## Opt-in reciprocal channel cross-promotion

The bot now includes a cross-promotion network integrated into the existing
`python-telegram-bot` process and the same SQLite database. It does not start
a second poller or require an unrelated third-party bot to enter
`@cryptoping_ru`.

### How it works

- A channel owner adds our existing bot `@crypto_source_farm_bot` to their
  **own public channel**, granting only the post permission required for the
  exchange, then sends `/crosspromo_add @channel` to the bot.
- The bot verifies the sender is that channel's administrator and checks the
  bot has permission to publish. New channels enter a pending queue.
- A CryptoPing RU group administrator reviews and approves or rejects each
  submission. Approved channels receive at most one reciprocal promo post per
  `CROSSPROMO_INTERVAL_HOURS` (default 72 hours).
- The scheduler rotates partners, prefers channels with a comparable audience,
  and avoids repeating a partner in the same target channel within seven days
  when alternatives exist. CryptoPing RU uses a tracked invite link per partner
  when Telegram permits creating it; otherwise the public link is used.
- `/crosspromopause` pauses CryptoPing RU's participation. `/crosspromoresume`
  resumes it. No paid placement or unsolicited posting is used.

### Commands

- `/crosspromo` — help and requirements.
- `/crosspromo_add @channel` — submit a channel you administer.
- `/crosspromopending` — review queue (CryptoPing RU administrators).
- `/crosspromoapprove ID` / `/crosspromoreject ID` — moderate a submission.
- `/crosspromolist` — list currently active partners.
- `/crosspromopause` / `/crosspromoresume` — pause or resume our channel.

### Important limits

This creates the exchange mechanism; it does not manufacture an audience.
Until at least one other channel owner joins and is approved, there is nobody
to exchange posts with and the scheduler sends nothing. Results depend on real
partner channels and their audiences. A partner can stop participation by
removing the bot; delivery failures disable that target until its owner resolves
permissions and registers again. Minimum channel size is configurable and
defaults to 10 so small channels such as `@cryptoping_ru` are not excluded.

The implementation adapts the cross-promotion workflow described by the
MIT-licensed [channel-promo-bot](https://github.com/qilaidev/channel-promo-bot)
to this repository's existing `python-telegram-bot` application and SQLite
database; the upstream aiogram application is not launched as a second process.

## Automatic distribution

The GitHub Actions workflow `.github/workflows/free-distribution.yml` runs
`scripts/submit_directory.py`. It submits the public channel `@cryptoping_ru`
to TGFind, a public Telegram directory, and verifies the listing through the
directory's lookup API. The script is idempotent and retries daily until the
listing is visible; it does not repeatedly create duplicate listings.

This is a free organic discovery route, not a subscriber-growth guarantee.
It does not purchase ads or post unsolicited messages in third-party channels.
Posting in another channel requires its owner's permission or authorized
publishing access. Paid placement requires an authorized advertising account
and a budget. The current repository does not contain verified credentials for
those routes, so they are not represented as active.


## Free distribution target registry

The free target inventory is maintained in `distribution/targets.json`. It separates
public self-promotion candidates, opt-in cross-promotion networks, free directories
and adjacent audiences. Each entry records the available public description, the
permission evidence, the required publishing authorization, and whether it has
actually been connected. A public group listing does not by itself authorize a bot
to publish there. Targets marked `discovered_not_joined`,
`discovered_not_connected` or `discovered_rules_need_review` are research results,
not live distribution. Paid options are excluded.

The inventory currently contains 23 networks/bots for cross-promotion or free promotion,
125 community/group/channel targets and 26 free-directory/discovery candidates (174 entries total).
It includes the user-supplied targets `@chatik_piarvz`, `@vzaimnaya7`,
`@cryptoadminsVP`, `@Avto_Dubai_Arenda`, `@vzpodpiskachati`, `@vzpiarchatx`,
`@vzchatpiar_vz`, `@chatd_piar` and `@piar_chatiku`, plus public PR communities,
referral-exchange groups, free automated cross-promotion services, free promoter bots,
view-exchange options and directory submission candidates. Each record includes the
available public evidence and setup status. Many targets require rule/eligibility checks
or may prohibit bots; no third-party posting is claimed active until access and an
actual publication are verified. Only free promotion routes are tracked; paid upgrades
and paid placements are excluded.

Priority networks include free cross-promotion on Onflow Ads, Adpact and Trigram.
Public self-promotion candidates include `@ifreepr`, `@prchatik`, `@prbirza1`,
`@p1rchat`, `@TGvzaim` and related communities. The inventory also tracks
free directories and adjacent business audiences; these are not treated as
automatic placements unless their current rules and publishing permissions allow it.


## Publisher: community review and publication planning

The Publisher review module is part of this repository and reuses the curated
`distribution/targets.json` community inventory. It stores its review state and
content drafts in a separate `data/publisher.db` SQLite database; it does not
modify `data/growth.db` or the running bot's tables.

Import the existing community inventory and inspect candidates:

```bash
python -m publisher import-catalog
python -m publisher list-targets
```

Imported communities remain pending. A public description or a discovery record
is not treated as permission to publish. An operator must review current rules
and record explicit permission evidence before a target can become eligible.
The Publisher currently supports candidate review, draft approval and dry-run
planning only. It has no Telegram sender or MTProto session.

See [README_PUBLISHER.md](README_PUBLISHER.md) for commands, policy and tests.
