"""Domain models for community review and publication planning."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Target:
    id: int
    kind: str
    handle: str
    rules_url: Optional[str]
    status: str
    promotion_policy: str
    permission_evidence: Optional[str]
    reviewed_at: Optional[str]
    last_posted_at: Optional[str]


@dataclass(frozen=True)
class Draft:
    id: int
    title: str
    body: str
    status: str


@dataclass(frozen=True)
class PlanItem:
    target_id: int
    handle: str
    eligible: bool
    reason: str
