"""Normalize public Telegram usernames and links for candidate intake."""
import re
from urllib.parse import urlparse


_USERNAME = re.compile(r"^[A-Za-z0-9_]{5,32}$")


def normalize_public_target(value):
    """Return a canonical @username; reject invite links and private references."""
    if not isinstance(value, str):
        raise ValueError("Telegram target must be text")
    value = value.strip()
    if not value:
        raise ValueError("Telegram target is empty")

    if value.startswith("@"):
        username = value[1:]
    else:
        candidate = value if "://" in value else "https://" + value
        parsed = urlparse(candidate)
        if parsed.netloc.lower() not in ("t.me", "www.t.me", "telegram.me", "www.telegram.me"):
            raise ValueError("only public t.me or telegram.me links are accepted")
        parts = [part for part in parsed.path.split("/") if part]
        if parts and parts[0] == "s":
            parts = parts[1:]
        if len(parts) != 1:
            raise ValueError("link must point directly to a public username")
        username = parts[0]

    if username.startswith("+") or username.lower() == "joinchat":
        raise ValueError("invite links are not supported; add a public username")
    if not _USERNAME.fullmatch(username):
        raise ValueError("invalid public Telegram username")
    return "@" + username.lower()
