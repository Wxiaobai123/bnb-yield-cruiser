from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.models import PlanResult


class TelegramNotificationError(RuntimeError):
    """Raised when Telegram config is missing or message delivery fails."""


@dataclass
class TelegramConfig:
    bot_token: str
    chat_id: str
    enabled: bool = True
    source: str = "file"

    @property
    def masked_token(self) -> str:
        if len(self.bot_token) <= 10:
            return "*" * len(self.bot_token)
        return f"{self.bot_token[:6]}...{self.bot_token[-4:]}"


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _config_from_env() -> TelegramConfig | None:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        return None
    return TelegramConfig(bot_token=bot_token, chat_id=chat_id, enabled=True, source="env")


def load_telegram_config(config_path: str) -> TelegramConfig | None:
    path = Path(config_path)
    raw = _read_json(path)
    if raw:
        bot_token = str(raw.get("bot_token", "")).strip()
        chat_id = str(raw.get("chat_id", "")).strip()
        enabled = bool(raw.get("enabled", True))
        if bot_token and chat_id:
            return TelegramConfig(bot_token=bot_token, chat_id=chat_id, enabled=enabled, source="file")
    return _config_from_env()


def require_telegram_config(config_path: str) -> TelegramConfig:
    config = load_telegram_config(config_path)
    if not config:
        raise TelegramNotificationError("请先连接 Telegram Bot，并填写 Bot Token 与 Chat ID。")
    if not config.enabled:
        raise TelegramNotificationError("Telegram 提醒当前已关闭，请重新启用后再发送。")
    return config


def save_telegram_config(config_path: str, bot_token: str, chat_id: str, enabled: bool = True) -> TelegramConfig:
    bot_token = bot_token.strip()
    chat_id = chat_id.strip()
    if not bot_token:
        raise TelegramNotificationError("Bot Token 不能为空。")
    if not chat_id:
        raise TelegramNotificationError("Chat ID 不能为空。")

    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "bot_token": bot_token,
        "chat_id": chat_id,
        "enabled": bool(enabled),
        "updated_at": datetime.now().isoformat(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    os.chmod(path, 0o600)
    return TelegramConfig(bot_token=bot_token, chat_id=chat_id, enabled=bool(enabled), source="file")


def remove_telegram_config(config_path: str) -> None:
    path = Path(config_path)
    if path.exists():
        path.unlink()


def telegram_status(config_path: str) -> dict:
    config = load_telegram_config(config_path)
    if not config:
        return {
            "connected": False,
            "enabled": False,
            "chat_id": "",
            "masked_token": "",
            "source": "none",
        }
    return {
        "connected": True,
        "enabled": config.enabled,
        "chat_id": config.chat_id,
        "masked_token": config.masked_token,
        "source": config.source,
    }


def send_telegram_message(config: TelegramConfig, text: str, timeout: int = 10) -> dict:
    data = urlencode(
        {
            "chat_id": config.chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    request = Request(
        f"https://api.telegram.org/bot{config.bot_token}/sendMessage",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise TelegramNotificationError(f"Telegram 接口返回错误：{detail}") from exc
    except URLError as exc:
        raise TelegramNotificationError(f"无法连接 Telegram 接口：{exc}") from exc

    if not payload.get("ok"):
        raise TelegramNotificationError(f"Telegram 发送失败：{payload.get('description', '未知错误')}")
    return payload["result"]


def build_test_message() -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "BNB 收益巡航官\n"
        "Telegram 连接测试成功。\n"
        f"发送时间：{timestamp}\n"
        "接下来你可以把当前收益方案一键推送到这个对话。"
    )


def _format_balance(amount: float, asset: str) -> str:
    digits = 2 if asset in {"USDT", "USDC", "FDUSD"} else 4
    return f"{amount:.{digits}f} {asset}"


def _format_data_mode(data_mode: str) -> str:
    mapping = {
        "sample": "演示样例",
        "auto": "自动模式",
        "live": "实时模式",
        "mixed-public": "样例 + 公告",
        "mixed-live": "实时收益 + 样例事件",
        "live+public": "实时收益 + 官方公告",
    }
    return mapping.get(data_mode, data_mode)


def _format_risk_label(risk_tolerance: str) -> str:
    mapping = {
        "low": "低风险",
        "medium": "中风险",
        "high": "高风险",
    }
    return mapping.get(risk_tolerance, risk_tolerance)


def build_plan_notification(plan: PlanResult) -> str:
    lines = [
        "BNB 收益巡航官",
        "",
        "当前画像",
        f"- BNB：{_format_balance(plan.profile.balances.get('BNB', 0.0), 'BNB')}",
        f"- USDT：{_format_balance(plan.profile.balances.get('USDT', 0.0), 'USDT')}",
        f"- 流动性窗口：{plan.profile.liquidity_window_days} 天",
        f"- 风险偏好：{_format_risk_label(plan.profile.risk_tolerance)}",
        f"- 数据模式：{_format_data_mode(plan.data_mode)}",
        "",
        "推荐配置",
    ]

    visible_allocations = [item for item in plan.allocations if item.bucket != "Reserve"]
    if not visible_allocations:
        lines.append("- 当前没有可推送的配置结果。")
    else:
        for index, item in enumerate(visible_allocations[:4], start=1):
            lines.append(
                f"{index}. {item.scored.opportunity.product_name} | "
                f"{_format_balance(item.amount, item.asset)} | {item.scored.include_reason}"
            )

    if plan.reminders:
        lines.extend(["", "提醒项"])
        for reminder in plan.reminders[:3]:
            lines.append(
                f"- {reminder.title} | {reminder.when.strftime('%Y-%m-%d %H:%M')} | {reminder.description}"
            )

    if plan.warnings:
        lines.extend(["", "数据提示"])
        for warning in plan.warnings[:2]:
            lines.append(f"- {warning}")

    return "\n".join(lines)
