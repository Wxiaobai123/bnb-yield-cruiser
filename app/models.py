from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class UserProfile:
    balances: dict[str, float]
    liquidity_window_days: int
    risk_tolerance: str
    allow_locked_products: bool
    allow_advanced_products: bool
    wants_reminders: bool
    reminder_mode: str
    prefers_bnb_native: bool
    now: datetime


@dataclass
class Opportunity:
    id: str
    product_name: str
    category: str
    source_type: str
    source_url: str
    asset: str
    apr_type: str
    apr_value: float
    lock_days: int
    liquidity_level: str
    event_eligibility: list[str]
    risk_tier: str
    confidence: float
    deadline: datetime | None
    notes: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Opportunity":
        deadline = raw.get("deadline")
        return cls(
            id=raw["id"],
            product_name=raw["product_name"],
            category=raw["category"],
            source_type=raw["source_type"],
            source_url=raw["source_url"],
            asset=raw["asset"],
            apr_type=raw["apr_type"],
            apr_value=float(raw["apr_value"]),
            lock_days=int(raw["lock_days"]),
            liquidity_level=raw["liquidity_level"],
            event_eligibility=list(raw.get("event_eligibility", [])),
            risk_tier=raw["risk_tier"],
            confidence=float(raw["confidence"]),
            deadline=datetime.fromisoformat(deadline) if deadline else None,
            notes=raw["notes"],
        )


@dataclass
class ScoredOpportunity:
    opportunity: Opportunity
    bucket: str
    score: float
    include_reason: str
    exclude_reason: str


@dataclass
class AllocationItem:
    bucket: str
    asset: str
    amount: float
    scored: ScoredOpportunity


@dataclass
class ReminderItem:
    title: str
    when: datetime
    description: str
    source_url: str


@dataclass
class PlanResult:
    profile: UserProfile
    data_mode: str
    allocations: list[AllocationItem]
    excluded: list[ScoredOpportunity]
    reminders: list[ReminderItem]
    asset_overview: dict[str, Any] | None = None
    warnings: list[str] | None = None
