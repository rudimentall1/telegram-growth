# Telegram Growth

Telegram-бот для учёта источников привлечения подписчиков и отчётов по вступлениям/отпискам.

## Что умеет текущая версия

- Создавать именованные invite-ссылки в Telegram-канале командой `/growthlink source_name`.
- Записывать события вступления и выхода, когда Telegram присылает `chat_member` update.
- Показывать статистику событий по источникам через `/growthreport`.
- Хранить данные в SQLite.

## Важные ограничения

- Telegram не предоставляет число кликов по invite-ссылкам через Bot API.
- `growth_events` считает события, а не уникальные клики.
- `active_count()` считает активных участников, известных локальной базе. Это не обязательно полное число подписчиков канала.
- Событие без известной invite-ссылки атрибутируется как `unattributed`.
- Бот должен быть администратором канала и иметь право создавать invite-ссылки. Для получения событий о членстве настройте бота и обновления Telegram соответствующим образом.

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
