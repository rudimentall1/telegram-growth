"""Eligibility checks for Telegram group publishing.

A destination is eligible after Telegram reports that the bot joined it and
the owner has not explicitly paused/rejected it. Live Telegram permissions
are checked immediately before every send. There is no arbitrary cooldown,
daily cap, per-news destination cap, or human evidence-expiry timer.
"""
def evaluate_target(target, now=None, review_max_age_days=None, min_interval_days=0):
    status = target.get("status")
    policy = target.get("promotion_policy")
    if status in ("paused", "rejected"):
        return False, f"target status is {status}"
    if status != "approved":
        return False, f"target status is {status}"
    if policy == "prohibited":
        return False, "target is marked prohibited"
    if policy != "allowed":
        return False, f"promotion policy is {policy}"
    return True, "Telegram membership was registered; live send permission is checked before publication"
