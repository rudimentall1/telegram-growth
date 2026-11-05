#!/usr/bin/env python3
"""Read-only audit of a public Telegram channel preview.

Fetches public t.me/s pages only. Does not join chats, send messages, or use
Telegram credentials. It reports posting volume, view-counter snapshots,
repeated source URLs, and similar titles.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from difflib import SequenceMatcher


USER_AGENT = "CryptoPingRU-ChannelAudit/1.0"
STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "after", "over",
    "into", "its", "are", "was", "has", "have", "will", "more", "than",
    "как", "что", "для", "это", "после", "когда", "или", "его", "ее",
    "они", "также", "при", "из", "на", "в", "и", "а", "по", "к",
}


def fetch_page(url: str, timeout: int = 20) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def clean_text(fragment: str) -> str:
    fragment = re.sub(r"<br\s*/?>", " ", fragment, flags=re.I)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    fragment = html.unescape(fragment)
    return re.sub(r"\s+", " ", fragment).strip()


def canonical_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    query = [
        (key, value)
        for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
        and key.lower() not in {"ref", "source", "fbclid", "gclid"}
    ]
    path = parsed.path.rstrip("/") or "/"
    return urllib.parse.urlunsplit(
        (parsed.scheme.lower(), parsed.netloc.lower(), path, urllib.parse.urlencode(query), "")
    )


def tokenize(value: str) -> set[str]:
    words = re.findall(r"[a-zа-яё0-9]{3,}", value.lower())
    return {word for word in words if word not in STOPWORDS}


def parse_posts(page: str, channel: str) -> list[dict]:
    chunks = re.findall(
        r'<div class="tgme_widget_message_wrap.*?</div>\s*</div>\s*</div>',
        page,
        flags=re.S,
    )
    # Telegram's wrapper nesting can vary; split on the stable post marker.
    starts = list(re.finditer(r'<div class="tgme_widget_message_wrap[^>]*>', page))
    posts = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(page)
        chunk = page[match.start():end]
        post_match = re.search(r'data-post="' + re.escape(channel) + r'/(\d+)"', chunk)
        text_match = re.search(
            r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>',
            chunk,
            flags=re.S,
        )
        date_match = re.search(r'<time datetime="([^"]+)"', chunk)
        views_match = re.search(r'class="tgme_widget_message_views">([^<]+)</span>', chunk)
        if not post_match or not text_match:
            continue
        raw_text = clean_text(text_match.group(1))
        external = []
        for raw_url in re.findall(r'href="(https?://[^"]+)"', text_match.group(1)):
            candidate = html.unescape(raw_url)
            host = urllib.parse.urlsplit(candidate).netloc.lower()
            if host and not host.endswith("t.me") and host != "telegram.me":
                external.append(canonical_url(candidate))
        story_title = raw_text.split("Оригинал:", 1)[1] if "Оригинал:" in raw_text else raw_text
        story_title = re.split(r"https?://", story_title, maxsplit=1)[0].strip()
        posts.append({
            "id": int(post_match.group(1)),
            "date": date_match.group(1) if date_match else None,
            "views": views_match.group(1).strip() if views_match else None,
            "text": raw_text,
            "story_title": story_title,
            "urls": list(dict.fromkeys(external)),
        })
    return posts


def view_number(value: str | None) -> float | None:
    if not value:
        return None
    value = value.strip().lower().replace(",", ".")
    multiplier = 1
    if value.endswith("k"):
        multiplier, value = 1000, value[:-1]
    elif value.endswith("m"):
        multiplier, value = 1_000_000, value[:-1]
    try:
        return float(value) * multiplier
    except ValueError:
        return None


def audit(channel: str, pages: int, page_size: int) -> dict:
    all_posts: dict[int, dict] = {}
    before = None
    errors = []
    for _ in range(pages):
        query = f"?before={before}" if before else ""
        url = f"https://t.me/s/{channel}{query}"
        try:
            page = fetch_page(url)
        except (urllib.error.URLError, TimeoutError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            break
        current = parse_posts(page, channel)
        if not current:
            break
        for post in current:
            all_posts[post["id"]] = post
        oldest = min(item["id"] for item in current)
        if oldest == before or len(current) < 1:
            break
        before = oldest
        if len(all_posts) >= pages * page_size:
            break

    posts = sorted(all_posts.values(), key=lambda item: item["id"], reverse=True)
    timestamps = [
        datetime.fromisoformat(post["date"].replace("Z", "+00:00"))
        for post in posts if post.get("date")
    ]
    view_counts = [view_number(post.get("views")) for post in posts]
    view_counts = [value for value in view_counts if value is not None]

    by_url = defaultdict(list)
    for post in posts:
        for url in post["urls"]:
            by_url[url].append(post)
    repeated_urls = {
        url: [post["id"] for post in rows]
        for url, rows in by_url.items() if len(rows) > 1
    }

    similar_titles = []
    candidates = posts[:min(len(posts), 100)]
    token_sets = {post["id"]: tokenize(post.get("story_title") or post["text"]) for post in candidates}
    seen_pairs = set()
    for i, left in enumerate(candidates):
        left_tokens = token_sets[left["id"]]
        if len(left_tokens) < 4:
            continue
        for right in candidates[i + 1:]:
            pair = tuple(sorted((left["id"], right["id"])))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            right_tokens = token_sets[right["id"]]
            if len(right_tokens) < 4:
                continue
            union = left_tokens | right_tokens
            jaccard = len(left_tokens & right_tokens) / len(union) if union else 0
            sequence = SequenceMatcher(
                None, " ".join(sorted(left_tokens)), " ".join(sorted(right_tokens))
            ).ratio()
            score = max(jaccard, sequence)
            common_tokens = len(left_tokens & right_tokens)
            if score >= 0.50 and common_tokens >= 3:
                similar_titles.append({
                    "ids": [left["id"], right["id"]],
                    "similarity": round(score, 2),
                    "shared_tokens": common_tokens,
                    "titles": [left.get("story_title", left["text"])[:180], right.get("story_title", right["text"])[:180]],
                })

    hours = None
    if len(timestamps) >= 2:
        span = (max(timestamps) - min(timestamps)).total_seconds() / 3600
        hours = round(span, 1) if span > 0 else None
    return {
        "channel": channel,
        "posts_sampled": len(posts),
        "oldest_post_id": min((p["id"] for p in posts), default=None),
        "newest_post_id": max((p["id"] for p in posts), default=None),
        "time_span_hours": hours,
        "estimated_posts_per_day": round(len(posts) / hours * 24, 1) if hours else None,
        "view_counter_mean": round(statistics.mean(view_counts), 2) if view_counts else None,
        "view_counter_median": round(statistics.median(view_counts), 2) if view_counts else None,
        "repeated_external_urls": repeated_urls,
        "similar_story_pairs": similar_titles[:50],
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", default="cryptoping_ru")
    parser.add_argument("--pages", type=int, default=5)
    parser.add_argument("--page-size", type=int, default=20)
    parser.add_argument("--output", help="Optional JSON output path")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_]{5,32}", args.channel):
        parser.error("channel must be a public Telegram username")
    result = audit(args.channel, max(1, min(args.pages, 20)), max(1, min(args.page_size, 100)))
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as target:
            target.write(rendered + "\n")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
