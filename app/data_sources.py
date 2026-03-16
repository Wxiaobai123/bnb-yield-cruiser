from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.models import Opportunity, UserProfile


@dataclass
class LoadedData:
    profile: UserProfile
    opportunities: list[Opportunity]
    data_mode: str
    warnings: list[str]


def profile_from_dict(raw: dict) -> UserProfile:
    return UserProfile(
        balances={asset: float(amount) for asset, amount in raw["balances"].items()},
        liquidity_window_days=int(raw["liquidity_window_days"]),
        risk_tolerance=raw["risk_tolerance"],
        allow_locked_products=bool(raw["allow_locked_products"]),
        allow_advanced_products=bool(raw["allow_advanced_products"]),
        wants_reminders=bool(raw["wants_reminders"]),
        reminder_mode=str(raw.get("reminder_mode", "deadline")),
        prefers_bnb_native=bool(raw.get("prefers_bnb_native", True)),
        now=datetime.fromisoformat(raw["now"]),
    )


def load_profile(path: str) -> UserProfile:
    raw = json.loads(Path(path).read_text())
    return profile_from_dict(raw)


def load_opportunities(path: str) -> list[Opportunity]:
    raw_items = json.loads(Path(path).read_text())
    return [Opportunity.from_dict(item) for item in raw_items]


def has_live_credentials() -> bool:
    return bool(os.getenv("BINANCE_API_KEY") and os.getenv("BINANCE_SECRET_KEY"))
