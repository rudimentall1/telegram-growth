"""Fail-closed eligibility checks for community promotion."""
from datetime import datetime, timedelta, timezone


def evaluate_target(target, now=None, review_max_age_days=30, min_interval_days=7):
    """Return (eligible, reason). Unknown or stale permission always fails closed."""
    now = now or datetime.now(timezone.utc)

    if target["status"] != "approved":
        return False, f"target status is {target['status']}"
    if target["promotion_policy"] != "allowed":
        return False, f"promotion policy is {target['promotion_policy']}"
    if not (target.get("permission_evidence") or "").strip():
        return False, "permission evidence is missing"

    reviewed_at = target.get("reviewed_at")
    if not reviewed_at:
        return False, "permission has not been reviewed"
    try:
        reviewed = datetime.fromisoformat(reviewed_at)
        if reviewed.tzinfo is None:
            reviewed = reviewed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return False, "review timestamp is invalid"

    if now - reviewed > timedelta(days=review_max_age_days):
        return False, "permission review is stale"

    last_posted_at = target.get("last_posted_at")
    if last_posted_at:
        try:
            last_posted = datetime.fromisoformat(last_posted_at)
            if last_posted.tzinfo is None:
                last_posted = last_posted.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return False, "last publication timestamp is invalid"
        if now - last_posted < timedelta(days=min_interval_days):
            return False, "target cooldown has not elapsed"

    return True, "approved permission and cooldown checks passed"
