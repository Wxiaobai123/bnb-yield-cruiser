from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import os
from threading import Lock
from time import monotonic
from typing import Any

from app.models import Opportunity


class LiveDataUnavailable(RuntimeError):
    """Raised when Binance live data cannot be loaded."""


_LIVE_CACHE_LOCK = Lock()
_LIVE_CACHE: dict[str, tuple[float, Any]] = {}
_LIVE_CACHE_TTLS = {
    "asset_overview": 20.0,
    "simple_earn": 20.0,
}


def _wrap_live_error(scope: str, exc: Exception) -> LiveDataUnavailable:
    message = str(exc)
    if "timed out" in message.lower():
        return LiveDataUnavailable(f"{scope}暂时超时，请稍后重试。")
    return LiveDataUnavailable(f"{scope}暂时不可用，请稍后重试。")


def _to_plain(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=True, exclude_none=True)
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_plain(item) for key, item in value.items()}
    return value


def _float_value(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _round_balance(value: float) -> float:
    return round(value, 8)


def _tracked_assets(asset_filter: set[str] | None = None) -> list[str]:
    assets = {asset for asset in (asset_filter or {"BNB", "USDT"}) if asset}
    if not assets:
        assets = {"BNB", "USDT"}
    return sorted(assets)


def _cache_key(prefix: str, asset_filter: set[str] | None = None) -> str:
    tracked = ",".join(_tracked_assets(asset_filter))
    return f"{prefix}:{tracked}"


def _get_cached_value(key: str, ttl: float) -> Any | None:
    with _LIVE_CACHE_LOCK:
        cached = _LIVE_CACHE.get(key)
    if not cached:
        return None
    stored_at, value = cached
    if monotonic() - stored_at > ttl:
        return None
    return deepcopy(value)


def _set_cached_value(key: str, value: Any) -> Any:
    with _LIVE_CACHE_LOCK:
        _LIVE_CACHE[key] = (monotonic(), deepcopy(value))
    return deepcopy(value)


def _load_sdk_clients():
    try:
        from binance_sdk_simple_earn.simple_earn import (
            SIMPLE_EARN_REST_API_PROD_URL,
            ConfigurationRestAPI as SimpleEarnConfigurationRestAPI,
            SimpleEarn,
        )
        from binance_sdk_wallet.wallet import (
            WALLET_REST_API_PROD_URL,
            ConfigurationRestAPI as WalletConfigurationRestAPI,
            Wallet,
        )
    except ImportError as exc:
        raise LiveDataUnavailable(
            "实时模式需要安装币安官方 Python SDK 包 "
            "`binance-sdk-simple-earn` 和 `binance-sdk-wallet`。"
        ) from exc

    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_SECRET_KEY")
    if not api_key or not api_secret:
        raise LiveDataUnavailable("实时模式需要提供 BINANCE_API_KEY 和 BINANCE_SECRET_KEY。")

    simple_config = SimpleEarnConfigurationRestAPI(
        api_key=api_key,
        api_secret=api_secret,
        base_path=os.getenv("BINANCE_SIMPLE_EARN_BASE_PATH", SIMPLE_EARN_REST_API_PROD_URL),
    )
    wallet_config = WalletConfigurationRestAPI(
        api_key=api_key,
        api_secret=api_secret,
        base_path=os.getenv("BINANCE_WALLET_BASE_PATH", WALLET_REST_API_PROD_URL),
    )
    return SimpleEarn(config_rest_api=simple_config), Wallet(config_rest_api=wallet_config)


def _load_spot_balances(wallet, asset_filter: set[str] | None = None, include_zero: bool = False) -> dict[str, float]:
    tracked = _tracked_assets(asset_filter)
    try:
        response = wallet.rest_api.user_asset()
    except Exception as exc:  # pragma: no cover - depends on live network state
        raise _wrap_live_error("现货资产概览", exc) from exc
    data = _to_plain(response.data()) or []
    balances: dict[str, float] = {asset: 0.0 for asset in tracked}
    for row in data:
        asset = row.get("asset")
        if not asset:
            continue
        if asset not in balances:
            continue
        total = _float_value(row.get("free")) + _float_value(row.get("locked"))
        if total > 0 or include_zero:
            balances[asset] = _round_balance(total)
    if include_zero:
        return balances
    return {asset: amount for asset, amount in balances.items() if amount > 0}


def load_live_balances(asset_filter: set[str] | None = None) -> dict[str, float]:
    _, wallet = _load_sdk_clients()
    return _load_spot_balances(wallet, asset_filter=asset_filter, include_zero=False)


def _sum_flexible_position(rows: list[dict[str, Any]]) -> tuple[float, float]:
    total_amount = 0.0
    collateral_amount = 0.0
    for row in rows:
        total_amount += _float_value(row.get("totalAmount"))
        collateral_amount += _float_value(row.get("collateralAmount"))
    return total_amount, collateral_amount


def _sum_locked_position(rows: list[dict[str, Any]]) -> float:
    total_amount = 0.0
    for row in rows:
        total_amount += _float_value(row.get("amount"))
    return total_amount


def load_live_asset_overview(asset_filter: set[str] | None = None) -> dict[str, Any]:
    cache_key = _cache_key("asset_overview", asset_filter)
    cached = _get_cached_value(cache_key, _LIVE_CACHE_TTLS["asset_overview"])
    if cached is not None:
        return cached

    tracked = _tracked_assets(asset_filter)
    simple_earn, wallet = _load_sdk_clients()
    spot_balances = _load_spot_balances(wallet, asset_filter=set(tracked), include_zero=True)

    assets: dict[str, dict[str, float | str | bool]] = {}
    deployable_balances: dict[str, float] = {}

    for asset in tracked:
        try:
            flexible_response = simple_earn.rest_api.get_flexible_product_position(asset=asset)
            locked_response = simple_earn.rest_api.get_locked_product_position(asset=asset)
        except Exception as exc:  # pragma: no cover - depends on live network state
            raise _wrap_live_error(f"{asset} Earn 持仓概览", exc) from exc

        flexible_rows = (_to_plain(flexible_response.data()) or {}).get("rows", [])
        locked_rows = (_to_plain(locked_response.data()) or {}).get("rows", [])

        flexible_total, flexible_collateral = _sum_flexible_position(flexible_rows)
        locked_total = _sum_locked_position(locked_rows)
        spot_total = spot_balances.get(asset, 0.0)
        redeemable_flexible = max(flexible_total - flexible_collateral, 0.0)
        deployable_total = spot_total + redeemable_flexible
        total = spot_total + flexible_total + locked_total

        assets[asset] = {
            "asset": asset,
            "spot": _round_balance(spot_total),
            "simple_earn_flexible": _round_balance(flexible_total),
            "simple_earn_flexible_redeemable": _round_balance(redeemable_flexible),
            "simple_earn_locked": _round_balance(locked_total),
            "locked": _round_balance(locked_total),
            "total": _round_balance(total),
            "deployable": _round_balance(deployable_total),
            "has_flexible": flexible_total > 0,
            "has_locked": locked_total > 0,
        }

        if deployable_total > 0:
            deployable_balances[asset] = _round_balance(deployable_total)

    overview = {
        "scope": "deployable",
        "scope_note": "默认带入口径 = 现货 + 可赎回 Simple Earn 活期；已锁仓资产仅展示，不自动带入本次可调度仓位。",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "balances": deployable_balances,
        "assets": assets,
    }
    return _set_cached_value(cache_key, overview)


def _flexible_to_opportunity(row: dict[str, Any]) -> Opportunity:
    apr = _float_value(row.get("latestAnnualPercentageRate"))
    if apr == 0:
        apr = _float_value(row.get("airDropPercentageRate"))
    asset = row.get("asset", "")
    product_id = row.get("productId") or f"{asset.lower()}-flexible-live"
    return Opportunity.from_dict(
        {
            "id": f"live-flex-{product_id}",
            "product_name": f"Simple Earn 活期 {asset}",
            "category": "simple_earn_flexible",
            "source_type": "official_api",
            "source_url": "https://developers.binance.com/docs/simple_earn/Introduction",
            "asset": asset,
            "apr_type": "real_time",
            "apr_value": apr,
            "lock_days": 0,
            "liquidity_level": "high" if row.get("canRedeem", True) else "medium",
            "event_eligibility": ["launchpool", "hodler_airdrop"] if asset == "BNB" else [],
            "risk_tier": "core",
            "confidence": 0.98,
            "deadline": None,
            "notes": f"实时活期产品状态：{row.get('status', 'UNKNOWN')}。",
        }
    )


def _locked_to_opportunity(row: dict[str, Any]) -> Opportunity | None:
    detail = row.get("detail") or {}
    asset = detail.get("asset")
    if not asset:
        return None
    apr = _float_value(detail.get("apr")) + _float_value(detail.get("extraRewardAPR")) + _float_value(detail.get("boostApr"))
    project_id = row.get("projectId") or f"{asset.lower()}-locked-live"
    return Opportunity.from_dict(
        {
            "id": f"live-locked-{project_id}",
            "product_name": f"Simple Earn 定期 {asset} {detail.get('duration', 0)} 天",
            "category": "simple_earn_locked",
            "source_type": "official_api",
            "source_url": "https://developers.binance.com/docs/simple_earn/Introduction",
            "asset": asset,
            "apr_type": "locked",
            "apr_value": apr,
            "lock_days": int(detail.get("duration") or 0),
            "liquidity_level": "low",
            "event_eligibility": ["launchpool", "megadrop"] if asset == "BNB" else [],
            "risk_tier": "core",
            "confidence": 0.97,
            "deadline": None,
            "notes": f"实时定期产品状态：{detail.get('status', 'UNKNOWN')}。",
        }
    )


def load_live_simple_earn_opportunities(asset_filter: set[str] | None = None) -> list[Opportunity]:
    cache_key = _cache_key("simple_earn", asset_filter)
    cached = _get_cached_value(cache_key, _LIVE_CACHE_TTLS["simple_earn"])
    if cached is not None:
        return cached

    simple_earn, _ = _load_sdk_clients()
    try:
        flexible_response = simple_earn.rest_api.get_simple_earn_flexible_product_list()
        locked_response = simple_earn.rest_api.get_simple_earn_locked_product_list()
    except Exception as exc:  # pragma: no cover - depends on live network state
        raise _wrap_live_error("实时收益产品列表", exc) from exc

    flexible_rows = (_to_plain(flexible_response.data()) or {}).get("rows", [])
    locked_rows = (_to_plain(locked_response.data()) or {}).get("rows", [])

    opportunities: list[Opportunity] = []
    for row in flexible_rows:
        asset = row.get("asset")
        if asset_filter and asset not in asset_filter:
            continue
        opportunities.append(_flexible_to_opportunity(row))

    for row in locked_rows:
        detail = row.get("detail") or {}
        asset = detail.get("asset")
        if asset_filter and asset not in asset_filter:
            continue
        opportunity = _locked_to_opportunity(row)
        if opportunity is not None:
            opportunities.append(opportunity)

    if not opportunities:
        raise LiveDataUnavailable("实时模式没有为当前资产解析到可用的 Simple Earn 机会。")
    return _set_cached_value(cache_key, opportunities)


def merge_live_market_data(base: list[Opportunity], live: list[Opportunity]) -> list[Opportunity]:
    replace_categories = {"simple_earn_flexible", "simple_earn_locked"}
    retained = [item for item in base if item.category not in replace_categories]
    return retained + live
