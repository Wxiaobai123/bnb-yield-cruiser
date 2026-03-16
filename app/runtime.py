from __future__ import annotations

from app.data_sources import load_opportunities
from app.live_binance import (
    LiveDataUnavailable,
    load_live_asset_overview,
    load_live_simple_earn_opportunities,
    merge_live_market_data,
)
from app.models import PlanResult, UserProfile
from app.planner import build_plan
from app.public_events import (
    PublicEventsUnavailable,
    load_public_event_opportunities,
    merge_public_event_data,
)


def generate_plan(
    profile: UserProfile,
    opportunities_path: str,
    mode: str = "auto",
    use_wallet_balances: bool = False,
    skip_public_events: bool = False,
    has_live_credentials: bool = False,
) -> PlanResult:
    opportunities = load_opportunities(opportunities_path)
    warnings: list[str] = []
    data_mode = "sample"
    asset_overview: dict | None = None

    if mode in {"auto", "live"}:
        try:
            if mode == "live" or has_live_credentials:
                asset_filter = {asset for asset in profile.balances.keys() if asset}
                if not asset_filter:
                    asset_filter = {"BNB", "USDT"}
                live_opportunities = load_live_simple_earn_opportunities(asset_filter=asset_filter)
                opportunities = merge_live_market_data(opportunities, live_opportunities)
                asset_overview = load_live_asset_overview(asset_filter=asset_filter)
                data_mode = "mixed-live"
                if use_wallet_balances:
                    live_balances = asset_overview.get("balances", {}) if asset_overview else {}
                    if live_balances:
                        profile.balances = live_balances
                        data_mode = "live"
                        warnings.append(
                            "实时资产口径已切换为可调度资产：现货 + 可赎回 Simple Earn 活期。已锁仓资产仅展示，不自动带入本次配置。"
                        )
                    else:
                        warnings.append(
                            "实时资产概览中没有匹配到当前资产，因此继续使用表单里的资产输入。"
                        )
            elif mode == "auto":
                warnings.append("未检测到实时 API 凭证，当前先使用演示样例数据。")
        except LiveDataUnavailable as exc:
            if mode == "live":
                raise
            warnings.append(f"实时数据回退：{exc}")

    if not skip_public_events and mode in {"auto", "live"}:
        try:
            public_events = load_public_event_opportunities(now=profile.now.astimezone())
            opportunities = merge_public_event_data(opportunities, public_events)
            if data_mode == "sample":
                data_mode = "mixed-public"
            elif data_mode in {"mixed-live", "live"}:
                data_mode = "live+public"
        except PublicEventsUnavailable as exc:
            warnings.append(f"公告事件回退：{exc}")

    plan = build_plan(profile, opportunities, data_mode=data_mode)
    plan.asset_overview = asset_overview
    plan.warnings = warnings
    return plan


def plan_to_dict(plan: PlanResult) -> dict:
    action_map = {
        "simple_earn_flexible": ("前往 Simple Earn", "https://www.binance.com/en/earn/simple-earn"),
        "simple_earn_locked": ("前往 Simple Earn", "https://www.binance.com/en/earn/simple-earn"),
        "launchpool": ("查看 Launchpool 公告", "https://www.binance.com/en/support/announcement/list/48"),
        "hodler_airdrop": ("查看 HODLer 公告", "https://www.binance.com/en/support/announcement/list/128"),
        "megadrop": ("查看 Megadrop 说明", "https://academy.binance.com/en/articles/what-is-binance-megadrop-and-how-to-use-it"),
        "soft_staking": ("前往软质押", "https://www.binance.com/en/earn/soft-staking"),
        "binance_loan": ("前往币安借币", "https://www.binance.com/en/loan"),
        "dual_investment": ("前往双币投资", "https://www.binance.com/en/dual-investment"),
        "onchain_yields": ("前往链上赚币", "https://www.binance.com/en/earn/onchain-yields"),
    }
    liquidity_map = {"high": "高流动性", "medium": "中等流动性", "low": "低流动性"}
    risk_map = {"core": "默认层", "advanced": "进阶层", "high_risk": "高风险层"}
    eligibility_map = {
        "launchpool": "可承接 Launchpool 资格",
        "hodler_airdrop": "可承接 HODLer 空投资格",
        "megadrop": "可承接 Megadrop 资格",
    }

    return {
        "profile": {
            "balances": plan.profile.balances,
            "liquidity_window_days": plan.profile.liquidity_window_days,
            "risk_tolerance": plan.profile.risk_tolerance,
            "allow_locked_products": plan.profile.allow_locked_products,
            "allow_advanced_products": plan.profile.allow_advanced_products,
            "wants_reminders": plan.profile.wants_reminders,
            "reminder_mode": plan.profile.reminder_mode,
            "prefers_bnb_native": plan.profile.prefers_bnb_native,
            "now": plan.profile.now.isoformat(),
        },
        "data_mode": plan.data_mode,
        "warnings": plan.warnings or [],
        "asset_overview": plan.asset_overview or {},
        "allocations": [
            {
                "bucket": item.bucket,
                "asset": item.asset,
                "amount": item.amount,
                "product_name": item.scored.opportunity.product_name,
                "fit": item.scored.include_reason,
                "note": item.scored.opportunity.notes,
                "score": item.scored.score,
                "apr_type": item.scored.opportunity.apr_type,
                "apr_value": item.scored.opportunity.apr_value,
                "lock_days": item.scored.opportunity.lock_days,
                "source_type": item.scored.opportunity.source_type,
                "confidence": item.scored.opportunity.confidence,
                "liquidity_label": liquidity_map.get(item.scored.opportunity.liquidity_level, item.scored.opportunity.liquidity_level),
                "risk_label": risk_map.get(item.scored.opportunity.risk_tier, item.scored.opportunity.risk_tier),
                "eligibility_note": " / ".join(
                    eligibility_map.get(name, name) for name in item.scored.opportunity.event_eligibility
                )
                if item.scored.opportunity.event_eligibility
                else "无额外活动资格要求",
                "action_label": action_map.get(item.scored.opportunity.category, ("查看来源", item.scored.opportunity.source_url))[0],
                "action_url": action_map.get(item.scored.opportunity.category, ("查看来源", item.scored.opportunity.source_url))[1],
                "source_url": item.scored.opportunity.source_url,
            }
            for item in plan.allocations
        ],
        "excluded": [
            {
                "product_name": item.opportunity.product_name,
                "asset": item.opportunity.asset,
                "score": item.score,
                "reason": item.exclude_reason,
                "source_type": item.opportunity.source_type,
                "source_url": item.opportunity.source_url,
            }
            for item in plan.excluded
        ],
        "reminders": [
            {
                "title": item.title,
                "when": item.when.isoformat(),
                "description": item.description,
                "source_url": item.source_url,
            }
            for item in plan.reminders
        ],
    }
