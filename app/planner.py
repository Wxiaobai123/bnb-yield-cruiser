from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from app.models import (
    AllocationItem,
    Opportunity,
    PlanResult,
    ReminderItem,
    ScoredOpportunity,
    UserProfile,
)

CORE_YIELD_CATEGORIES = {"simple_earn_flexible", "simple_earn_locked", "soft_staking"}
EVENT_CATEGORIES = {"launchpool", "hodler_airdrop", "megadrop"}
ADVANCED_CATEGORIES = {"binance_loan", "dual_investment", "onchain_yields", "smart_arbitrage"}

RISK_TIER_SCORE = {"core": 0, "advanced": 1, "high_risk": 2}
USER_RISK_SCORE = {"low": 0, "medium": 1, "high": 2}
LIQUIDITY_LEVEL_SCORE = {"high": 3, "medium": 2, "low": 1}
STABLE_ASSETS = {"USDT", "USDC", "FDUSD"}


def bucket_for_category(category: str) -> str:
    if category in CORE_YIELD_CATEGORIES:
        return "Core Yield"
    if category in EVENT_CATEGORIES:
        return "Event Capture"
    return "Advanced Optional"


def is_bnb_native(opportunity: Opportunity) -> bool:
    return opportunity.asset == "BNB" or "launchpool" in opportunity.category or "hodler" in opportunity.category


def reserve_ratio(profile: UserProfile, asset: str) -> float:
    base = 0.18
    if profile.risk_tolerance == "low":
        base += 0.12
    elif profile.risk_tolerance == "medium":
        base += 0.05

    if profile.liquidity_window_days <= 7:
        base += 0.15
    elif profile.liquidity_window_days <= 14:
        base += 0.08

    if asset in STABLE_ASSETS:
        base += 0.08

    return min(base, 0.55)


def main_exclude_reason(profile: UserProfile, opportunity: Opportunity) -> str:
    if opportunity.category == "dual_investment" and not profile.allow_advanced_products:
        return "当前未开启高级产品，因此双币投资默认不纳入推荐。"
    if opportunity.category == "dual_investment":
        return "双币投资存在到期转换资产的结果，对当前画像来说风险偏高。"
    if opportunity.category == "megadrop" and profile.liquidity_window_days <= 7:
        return "用户 7 天内需要流动性，Megadrop 对锁仓 BNB 依赖更强，因此优先级下降。"
    if opportunity.category == "binance_loan" and not profile.allow_advanced_products:
        return "当前未开启高级策略，因此借币桥接方案暂不展示。"
    if opportunity.lock_days > profile.liquidity_window_days and profile.liquidity_window_days > 0:
        return "锁仓周期长于用户的流动性窗口，不适合作为当前主方案。"
    if opportunity.risk_tier == "high_risk":
        return "高风险产品已从默认推荐空间中降级排除。"
    if opportunity.category == "soft_staking":
        return "软质押更适合作为对比备选，当前适配度低于 Simple Earn。"
    return "综合流动性、复杂度和活动资格后，这个方案的适配度更低。"


def include_reason(profile: UserProfile, opportunity: Opportunity) -> str:
    if opportunity.category == "simple_earn_flexible":
        return "活期方案保留了较强流动性，同时还能维持币安生态内的收益曝光。"
    if opportunity.category == "simple_earn_locked":
        return "用户允许一定锁仓，因此可以用定期方案换取更强的 BNB 原生收益。"
    if opportunity.category == "launchpool":
        return "Launchpool 能在不改变核心持仓方向的前提下增加 BNB 生态活动收益。"
    if opportunity.category == "hodler_airdrop":
        return "HODLer 空投更适合作为合格持仓上的被动奖励叠加。"
    if opportunity.category == "megadrop":
        return "Megadrop 更适合作为高级事件桶，因为它依赖锁仓 BNB 和更主动的时间管理。"
    if opportunity.category == "binance_loan":
        return "如果用户想保留收益仓位又需要现金流，借币更像一条流动性桥接路径。"
    if opportunity.category == "soft_staking":
        return "当资产保留在现货账户时，软质押可以作为低摩擦备选。"
    if opportunity.category == "dual_investment":
        return "双币投资只适合明确接受到期结算结果的高级用户。"
    if opportunity.category == "onchain_yields":
        return "链上赚币只适合作为高风险探索仓，不适合默认推荐。"
    return opportunity.notes


def profile_alignment_bonus(profile: UserProfile, opportunity: Opportunity) -> float:
    bonus = 0.0

    if opportunity.category == "simple_earn_flexible":
        if profile.liquidity_window_days <= 14:
            bonus += 0.8
        if profile.allow_advanced_products and profile.liquidity_window_days >= 21 and opportunity.asset == "BNB":
            bonus -= 0.35

    if opportunity.category == "simple_earn_locked":
        if profile.allow_locked_products and profile.liquidity_window_days >= opportunity.lock_days >= 14:
            bonus += 1.5
        elif profile.allow_locked_products and profile.liquidity_window_days >= 14:
            bonus += 0.4

    if opportunity.category == "hodler_airdrop":
        if profile.liquidity_window_days <= 7:
            bonus += 0.95
        elif profile.liquidity_window_days >= 21:
            bonus -= 0.2

    if opportunity.category == "launchpool":
        if 8 <= profile.liquidity_window_days <= 21:
            bonus += 1.0
        elif profile.liquidity_window_days <= 7:
            bonus -= 0.35

    if opportunity.category == "megadrop":
        if profile.allow_locked_products and profile.allow_advanced_products and profile.liquidity_window_days >= 21:
            bonus += 3.1
        elif profile.liquidity_window_days <= 14:
            bonus -= 0.8

    if opportunity.category == "dual_investment":
        if profile.allow_advanced_products and opportunity.asset in STABLE_ASSETS and profile.liquidity_window_days >= 7:
            bonus += 1.2
            if profile.risk_tolerance == "medium":
                bonus += 0.4

    if opportunity.category == "binance_loan":
        if profile.allow_advanced_products and profile.liquidity_window_days <= 7:
            bonus += 0.8

    if opportunity.category == "soft_staking" and profile.liquidity_window_days <= 7:
        bonus -= 0.4

    return bonus


def score_opportunity(profile: UserProfile, opportunity: Opportunity) -> ScoredOpportunity:
    risk_gap = max(RISK_TIER_SCORE[opportunity.risk_tier] - USER_RISK_SCORE[profile.risk_tolerance], 0)
    yield_value = min(opportunity.apr_value / 2.5, 4.0)
    liquidity_fit = LIQUIDITY_LEVEL_SCORE[opportunity.liquidity_level] * 0.8
    if opportunity.lock_days == 0:
        liquidity_fit += 0.6
    event_bonus = 0.0
    if opportunity.category in EVENT_CATEGORIES and profile.balances.get("BNB", 0.0) > 0:
        event_bonus += 1.4
    if is_bnb_native(opportunity) and profile.prefers_bnb_native:
        event_bonus += 0.6
    simplicity_bonus = 1.0 if opportunity.risk_tier == "core" else 0.2
    if opportunity.risk_tier == "high_risk":
        simplicity_bonus = -1.5
    lock_penalty = 0.0
    if opportunity.lock_days > 0 and not profile.allow_locked_products:
        lock_penalty += 2.5
    if profile.liquidity_window_days > 0 and opportunity.lock_days > profile.liquidity_window_days:
        lock_penalty += 2.0 + (opportunity.lock_days - profile.liquidity_window_days) / 14.0
    complexity_penalty = risk_gap * 1.5
    if opportunity.risk_tier != "core" and not profile.allow_advanced_products:
        complexity_penalty += 2.0
    downside_penalty = 0.0
    if opportunity.category == "dual_investment":
        downside_penalty += 2.8
    if opportunity.category == "binance_loan":
        downside_penalty += 1.2
    if opportunity.category in {"onchain_yields", "smart_arbitrage"}:
        downside_penalty += 3.5
    if opportunity.category == "megadrop":
        downside_penalty += 1.0
    confidence_bonus = max((opportunity.confidence - 0.5) * 2.0, 0.0)
    profile_bonus = profile_alignment_bonus(profile, opportunity)

    score = (
        yield_value
        + liquidity_fit
        + event_bonus
        + simplicity_bonus
        + confidence_bonus
        + profile_bonus
        - lock_penalty
        - complexity_penalty
        - downside_penalty
    )

    return ScoredOpportunity(
        opportunity=opportunity,
        bucket=bucket_for_category(opportunity.category),
        score=round(score, 2),
        include_reason=include_reason(profile, opportunity),
        exclude_reason=main_exclude_reason(profile, opportunity),
    )


def top_by_bucket(scored: list[ScoredOpportunity], asset: str) -> dict[str, ScoredOpportunity]:
    selected: dict[str, ScoredOpportunity] = {}
    for bucket in ("Core Yield", "Event Capture", "Advanced Optional"):
        bucket_items = [item for item in scored if item.bucket == bucket and item.opportunity.asset == asset]
        bucket_items.sort(key=lambda item: item.score, reverse=True)
        if bucket_items and bucket_items[0].score > 0:
            selected[bucket] = bucket_items[0]
    return selected


def bucket_mix(profile: UserProfile, asset: str, selected: dict[str, ScoredOpportunity]) -> dict[str, float]:
    if asset in STABLE_ASSETS:
        mix = {"Core Yield": 1.0}
        if profile.allow_advanced_products and "Advanced Optional" in selected and selected["Advanced Optional"].score > 2.4:
            mix = {"Core Yield": 0.82, "Advanced Optional": 0.18}
        return mix

    mix = {"Core Yield": 0.6, "Event Capture": 0.4}
    if "Event Capture" not in selected:
        mix = {"Core Yield": 1.0}
    if profile.allow_advanced_products and "Advanced Optional" in selected and selected["Advanced Optional"].score > 2.6:
        mix = {"Core Yield": 0.48, "Event Capture": 0.32, "Advanced Optional": 0.20}
    if profile.liquidity_window_days <= 7:
        mix["Core Yield"] = round(mix.get("Core Yield", 0.0) + 0.08, 2)
        if "Event Capture" in mix:
            mix["Event Capture"] = round(max(mix["Event Capture"] - 0.08, 0.0), 2)
    total = sum(mix.values())
    return {bucket: share / total for bucket, share in mix.items() if share > 0}


def build_reminders(selected_items: list[AllocationItem], now: datetime, reminder_mode: str = "deadline") -> list[ReminderItem]:
    reminders: list[ReminderItem] = []
    reminder_offsets: list[tuple[str, timedelta]] = []

    if reminder_mode == "deadline_and_24h":
        reminder_offsets.append(("24 小时前提醒", timedelta(hours=24)))
    elif reminder_mode == "deadline_and_1h":
        reminder_offsets.append(("1 小时前提醒", timedelta(hours=1)))

    reminder_offsets.append(("截止提醒", timedelta(0)))

    for item in selected_items:
        opportunity = item.scored.opportunity
        if not opportunity.deadline:
            continue
        if opportunity.deadline <= now:
            continue
        for suffix, offset in reminder_offsets:
            remind_at = opportunity.deadline - offset
            if remind_at <= now:
                continue
            reminders.append(
                ReminderItem(
                    title=f"{opportunity.product_name} {suffix}",
                    when=remind_at,
                    description=f"{opportunity.product_name} 在该时间点前需要重点关注。{opportunity.notes}",
                    source_url=opportunity.source_url,
                )
            )
    reminders.sort(key=lambda reminder: reminder.when)
    return reminders


def build_plan(profile: UserProfile, opportunities: list[Opportunity], data_mode: str = "sample") -> PlanResult:
    scored = [score_opportunity(profile, opportunity) for opportunity in opportunities]
    by_asset: dict[str, list[ScoredOpportunity]] = defaultdict(list)
    for item in scored:
        by_asset[item.opportunity.asset].append(item)

    allocations: list[AllocationItem] = []
    selected_ids: set[str] = set()

    for asset, balance in profile.balances.items():
        if balance <= 0:
            continue
        reserve_amount = round(balance * reserve_ratio(profile, asset), 4)
        reserve_choice = ScoredOpportunity(
            opportunity=Opportunity(
                id=f"{asset.lower()}-reserve",
                product_name="流动性预留",
                category="reserve",
                source_type="derived_plan",
                source_url="",
                asset=asset,
                apr_type="n/a",
                apr_value=0.0,
                lock_days=0,
                liquidity_level="high",
                event_eligibility=[],
                risk_tier="core",
                confidence=1.0,
                deadline=None,
                notes="预留为可随时调动的流动性缓冲。",
            ),
            bucket="Reserve",
            score=10.0,
            include_reason="先保留一部分可用余额，避免短期内被锁仓或活动窗口卡住。",
            exclude_reason="",
        )
        allocations.append(AllocationItem(bucket="Reserve", asset=asset, amount=reserve_amount, scored=reserve_choice))

        deployable = round(max(balance - reserve_amount, 0.0), 4)
        if deployable == 0:
            continue

        selected = top_by_bucket(by_asset.get(asset, []), asset)
        mix = bucket_mix(profile, asset, selected)
        allocated_total = 0.0
        for bucket, share in mix.items():
            chosen = selected.get(bucket)
            if not chosen:
                continue
            amount = round(deployable * share, 4)
            if amount <= 0:
                continue
            allocated_total += amount
            selected_ids.add(chosen.opportunity.id)
            allocations.append(AllocationItem(bucket=bucket, asset=asset, amount=amount, scored=chosen))

        leftover = round(balance - sum(item.amount for item in allocations if item.asset == asset), 4)
        if leftover > 0.0001:
            allocations.append(AllocationItem(bucket="Reserve", asset=asset, amount=leftover, scored=reserve_choice))

    selected_items = [item for item in allocations if item.bucket != "Reserve"]
    excluded = [item for item in scored if item.opportunity.id not in selected_ids]
    excluded.sort(key=lambda item: item.score, reverse=True)
    reminders = build_reminders(selected_items, profile.now, profile.reminder_mode) if profile.wants_reminders else []

    return PlanResult(
        profile=profile,
        data_mode=data_mode,
        allocations=allocations,
        excluded=excluded[:5],
        reminders=reminders,
    )
