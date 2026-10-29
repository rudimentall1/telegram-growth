# Telegram Growth

Telegram-бот для учёта источников привлечения подписчиков и отчётов по вступлениям/отпискам.

## Команды бота

- `/growthlink source_name` — создать отдельную invite-ссылку для кампании. Бот возвращает ссылку и готовый короткий текст для публикации.
- `/growthreport` или `/growthreport all` — сводка по всей истории.
- `/growthreport 7d` и `/growthreport 30d` — события за выбранный период плюс текущее число известных активных участников по источникам.
- `/help` — краткая справка для участников группы.

Команды роста доступны только администраторам целевой группы или пользователям из `GROWTH_ADMIN_IDS`. Бот хранит данные в SQLite.

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
