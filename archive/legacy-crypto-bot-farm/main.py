import re
import feedparser
import requests
import json
import os
import sys
import time
import calendar
import signal
from datetime import datetime, timedelta, timezone
from deep_translator import GoogleTranslator, MyMemoryTranslator
from config import TELEGRAM_TOKEN, CHAT_ID

BASE_DIR = os.path.dirname(__file__)
SEEN_FILE = os.path.join(BASE_DIR, "data", "seen.json")
STATS_FILE = os.path.join(BASE_DIR, "data", "source_stats.json")
LOCK_FILE = os.path.join(BASE_DIR, "data", "main.lock")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

HTTP_TIMEOUT = 10          # секунд на любой отдельный сетевой запрос
HARD_RUNTIME_LIMIT = 300   # секунд максимум на весь прогон (5 минут) - потом жёстко завершаем себя
LOCK_STALE_SECONDS = 600   # если .lock старше 10 минут - считаем его зависшим и перезаписываем

FOCUSED_FEEDS = [
    "https://cointelegraph.com/rss/tag/nft",
    "https://airdropalert.com/feed/rssfeed",
    "https://nftplazas.com/feed",
    "https://crypto.news/tag/testnet/feed",
]

GENERAL_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
    "https://cryptobriefing.com/feed",
    "https://thedefiant.io/feed",
    "https://crypto.news/feed",
    "https://www.prnewswire.com/rss/financial-services-latest-news/cryptocurrency-list.rss",
    "https://news.polymarket.com/feed",
    "https://satoshi.ru/rss",
]

TOPIC_KEYWORDS = [
    "airdrop", "retrodrop", "rewards", "reward", "claim", "eligible",
    "eligibility", "snapshot", "allocation", "whitelist",
    "testnet", "incentivized", "incentive", "points", "campaign",
    "quest", "tasks", "mission", "beta", "alpha",
    "nft", "mint", "free mint", "allowlist", "collection",
    "marketplace", "nft drop", "soulbound", "sbt",
    "mainnet", "launch", "protocol", "ecosystem", "blockchain",
    "validator", "node", "staking", "bridge", "faucet",
    "ambassador", "referral", "early access", "early adopter",
    "ecosystem rewards", "grant", "funding", "token generation event",
    "tge", "ido", "ico", "launchpool", "liquidity", "defi", "gamefi",
    "socialfi", "layer 2", "l2", "rollup", "zk", "zksync", "optimistic",
    "cosmos", "solana", "ethereum", "arbitrum", "base", "monad", "berachain",
    "аирдроп", "дроп", "ретродроп", "дропа", "нфт", "минт", "нода", "ноды",
    "тестнет", "стейкинг", "валидатор", "листинг",
]

HOT_KEYWORDS = [
    "testnet", "incentivized", "rewards", "points", "quest", "campaign",
    "mainnet", "launch", "validator", "node", "faucet", "airdrop",
    "snapshot", "eligible", "claim", "retrodrop", "ecosystem",
    "grant", "funding", "tge",
]

BAD_WORDS = [
    "sponsored", "advertisement", "sponsor", "partner content",
    "paid content", "presented by", "promoted",
]

MAX_POSTS_PER_RUN = 12
MAX_PER_FEED = 3
MIN_TITLE_LENGTH = 5
MAX_AGE_DAYS = 3

class TimeoutError_(BaseException):
    pass

def _raise_timeout(signum, frame):
    raise TimeoutError_("превышен общий лимит времени на прогон")

def acquire_lock():
    """Файл-блокировка: не даём второму прогону стартовать, пока первый не закончился.
    Если .lock старый (процесс явно завис/умер) - перезаписываем и идём дальше."""
    if os.path.exists(LOCK_FILE):
        age = time.time() - os.path.getmtime(LOCK_FILE)
        if age < LOCK_STALE_SECONDS:
            print(f"Другой прогон уже идёт (lock моложе {LOCK_STALE_SECONDS}с) - выходим")
            sys.exit(0)
        else:
            print(f"Найден устаревший lock ({int(age)}с) - считаем прошлый прогон зависшим, продолжаем")
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

def release_lock():
    try:
        os.remove(LOCK_FILE)
    except FileNotFoundError:
        pass

def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)

def translate(text):
    try:
        result = GoogleTranslator(source="auto", target="ru").translate(text)
        if result and not looks_like_error(result):
            return result
    except Exception:
        pass
    try:
        result = MyMemoryTranslator(source="en-GB", target="ru-RU").translate(text)
        if result and not looks_like_error(result):
            return result
    except Exception:
        pass
    return text

ERROR_SIGNS = ["error 500", "that\u2019s an error", "that\u2019s all we know", "server error"]

def looks_like_error(text):
    t = text.lower()
    return any(sign in t for sign in ERROR_SIGNS)

def get_emoji(title):
    t = title.lower()
    if keyword_matches(t, HOT_KEYWORDS):
        return "🚨"
    if keyword_matches(t, ["node", "validator", "нода", "валидатор"]):
        return "🖥"
    if keyword_matches(t, ["airdrop", "retrodrop", "testnet", "аирдроп"]):
        return "🪂"
    if keyword_matches(t, ["nft", "mint", "whitelist", "нфт"]):
        return "🖼"
    return "📰"

def keyword_matches(text, keywords):
    for kw in keywords:
        if " " in kw:
            if kw in text:
                return kw
        else:
            if re.search(r"\b" + re.escape(kw) + r"\b", text):
                return kw
    return None

def is_good(title, require_topic_match):
    if len(title) < MIN_TITLE_LENGTH:
        return False
    t = title.lower()
    if keyword_matches(t, BAD_WORDS):
        return False
    if require_topic_match and not keyword_matches(t, TOPIC_KEYWORDS):
        return False
    return True

def is_recent(entry):
    struct = entry.get("published_parsed") or entry.get("updated_parsed")
    if not struct:
        return True
    try:
        published = datetime.fromtimestamp(calendar.timegm(struct), tz=timezone.utc)
    except Exception:
        return True
    return (datetime.now(timezone.utc) - published) <= timedelta(days=MAX_AGE_DAYS)

def fetch_feed(feed_url):
    """Скачиваем RSS сами через requests с таймаутом, потом парсим - feedparser.parse(url)
    напрямую может зависнуть без таймаута, поэтому так надёжнее."""
    r = requests.get(feed_url, headers=HEADERS, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return feedparser.parse(r.content)

def get_feed_candidates(feed_url, require_topic_match, seen):
    try:
        feed = fetch_feed(feed_url)
    except Exception as e:
        print(f"Источник недоступен ({feed_url}): {e}")
        return []

    result = []
    for entry in feed.entries[:20]:
        link = entry.get("link", "")
        title = entry.get("title", "")

        if not link or link in seen:
            continue
        if not is_good(title, require_topic_match):
            continue
        if not is_recent(entry):
            continue

        result.append((title, link, feed_url))
        if len(result) >= MAX_PER_FEED:
            break
    return result

def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "disable_web_page_preview": False}, timeout=HTTP_TIMEOUT)
    except Exception as e:
        print("Ошибка сети при отправке:", e)
        return False
    if r.status_code != 200:
        print("Ошибка отправки:", r.status_code, r.text)
        return False
    return True

def run():
    seen_list = load_json(SEEN_FILE, [])
    seen = set(seen_list)
    stats = load_json(STATS_FILE, {})

    all_feeds = [(url, False) for url in FOCUSED_FEEDS] + [(url, True) for url in GENERAL_FEEDS]
    per_feed_items = [get_feed_candidates(url, topic_req, seen) for url, topic_req in all_feeds]

    for i, (url, _) in enumerate(all_feeds):
        candidates_count = len(per_feed_items[i])
        stats.setdefault(url, {"found": 0, "sent": 0})
        stats[url]["found"] += candidates_count

    final_items = []
    round_idx = 0
    while len(final_items) < MAX_POSTS_PER_RUN and any(per_feed_items):
        for items in per_feed_items:
            if round_idx < len(items):
                final_items.append(items[round_idx])
                if len(final_items) >= MAX_POSTS_PER_RUN:
                    break
        round_idx += 1
        if round_idx >= MAX_PER_FEED:
            break

    for title, link, source in final_items:
        has_cyrillic = any('а' <= ch.lower() <= 'я' for ch in title)
        title_ru = title if has_cyrillic else translate(title)
        emoji = get_emoji(title)
        ok = send(f"{emoji} {title_ru}\n\nОригинал: {title}\n{link}")
        if ok:
            seen.add(link)
            seen_list.append(link)
            stats.setdefault(source, {"found": 0, "sent": 0})
            stats[source]["sent"] += 1
            save_json(SEEN_FILE, seen_list[-3000:])
            save_json(STATS_FILE, stats)

    save_json(SEEN_FILE, seen_list[-3000:])
    save_json(STATS_FILE, stats)

if __name__ == "__main__":
    try:
        signal.signal(signal.SIGALRM, _raise_timeout)
        signal.alarm(HARD_RUNTIME_LIMIT)
        run()
        signal.alarm(0)
    except TimeoutError_ as e:
        print("Прогон прерван по таймауту:", e)
    finally:
        release_lock()
