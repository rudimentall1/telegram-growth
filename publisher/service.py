"""Dry-run planner. No Telegram network calls are made here."""
from .policy import evaluate_target


class PublisherService:
    def __init__(self, store):
        self.store = store

    def build_plan(self, draft_id, now=None):
        draft = self.store.get_draft(draft_id)
        if not draft:
            raise LookupError(f"draft {draft_id} not found")
        if draft["status"] != "approved":
            raise ValueError("draft must be approved before planning")

        from .models import PlanItem

        plan = []
        for target in self.store.list_targets():
            eligible, reason = evaluate_target(target, now=now)
            plan.append(PlanItem(
                target_id=target["id"],
                handle=target["handle"],
                eligible=eligible,
                reason=reason,
            ))
        return draft, plan
