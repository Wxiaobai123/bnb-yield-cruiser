from __future__ import annotations

import json
import os
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from app.data_sources import has_live_credentials, profile_from_dict
from app.ics import build_ics_text
from app.live_binance import LiveDataUnavailable, load_live_asset_overview
from app.runtime import generate_plan, plan_to_dict
from app.telegram import (
    TelegramNotificationError,
    build_plan_notification,
    build_test_message,
    remove_telegram_config,
    require_telegram_config,
    save_telegram_config,
    send_telegram_message,
    telegram_status,
)

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
DEFAULT_OPPORTUNITIES = str(ROOT / "data" / "opportunities.sample.json")
TELEGRAM_CONFIG = str(ROOT / "data" / "telegram_config.json")


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


PUBLIC_DEMO = _env_flag("PUBLIC_DEMO", default=False)
TELEGRAM_FEATURE_ENABLED = _env_flag("ENABLE_TELEGRAM", default=not PUBLIC_DEMO)
PUBLIC_DEMO_NOTICE = (
    "当前为公开演示版：默认使用示例数据与公开事件源，不接收个人 Binance 或 Telegram 凭证。"
)


def _telegram_available() -> bool:
    return TELEGRAM_FEATURE_ENABLED and not PUBLIC_DEMO


def _safe_telegram_status() -> dict:
    if not _telegram_available():
        return {
            "connected": False,
            "enabled": False,
            "chat_id": "",
            "masked_token": "",
            "source": "disabled",
        }
    return telegram_status(TELEGRAM_CONFIG)


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "BNBYieldCruiserHTTP/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self._serve_file("index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/styles.css":
            self._serve_file("styles.css", "text/css; charset=utf-8")
            return
        if parsed.path == "/app.js":
            self._serve_file("app.js", "application/javascript; charset=utf-8")
            return
        if parsed.path == "/api/health":
            self._send_json(
                {
                    "ok": True,
                    "live_credentials": has_live_credentials(),
                    "telegram": _safe_telegram_status(),
                    "telegram_available": _telegram_available(),
                    "public_demo": PUBLIC_DEMO,
                    "public_demo_notice": PUBLIC_DEMO_NOTICE if PUBLIC_DEMO else "",
                    "time": datetime.now().isoformat(),
                }
            )
            return
        if parsed.path == "/api/telegram/status":
            self._send_json(
                {
                    "ok": True,
                    "telegram": _safe_telegram_status(),
                    "telegram_available": _telegram_available(),
                    "public_demo": PUBLIC_DEMO,
                }
            )
            return
        if parsed.path in {"/api/binance/spot-balances", "/api/binance/asset-overview"}:
            try:
                overview = load_live_asset_overview(asset_filter={"BNB", "USDT"})
            except LiveDataUnavailable as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            self._send_json(
                {
                    "ok": True,
                    "balances": {
                        "BNB": overview.get("balances", {}).get("BNB", 0.0),
                        "USDT": overview.get("balances", {}).get("USDT", 0.0),
                    },
                    "asset_overview": overview,
                    "updated_at": overview.get("updated_at") or datetime.now().isoformat(),
                }
            )
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in {
            "/api/plan",
            "/api/telegram/connect",
            "/api/telegram/disconnect",
            "/api/telegram/test",
            "/api/telegram/push-plan",
        }:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length).decode("utf-8")
            payload = json.loads(raw_body or "{}")
        except (ValueError, json.JSONDecodeError):
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")
            return

        try:
            if parsed.path.startswith("/api/telegram/") and not _telegram_available():
                self._send_json(
                    {
                        "ok": False,
                        "error": "公开演示版已关闭 Telegram 连接与推送能力，请在本地自托管环境中启用。",
                    },
                    status=HTTPStatus.FORBIDDEN,
                )
                return

            if parsed.path == "/api/telegram/connect":
                config = save_telegram_config(
                    TELEGRAM_CONFIG,
                    bot_token=str(payload.get("bot_token", "")),
                    chat_id=str(payload.get("chat_id", "")),
                    enabled=bool(payload.get("enabled", True)),
                )
                self._send_json(
                    {
                        "ok": True,
                        "message": "Telegram 已连接，可以发送测试消息了。",
                        "telegram": _safe_telegram_status(),
                        "chat_id": config.chat_id,
                    }
                )
                return

            if parsed.path == "/api/telegram/disconnect":
                remove_telegram_config(TELEGRAM_CONFIG)
                self._send_json(
                    {
                        "ok": True,
                        "message": "Telegram 连接已断开。",
                        "telegram": _safe_telegram_status(),
                    }
                )
                return

            if parsed.path == "/api/telegram/test":
                config = require_telegram_config(TELEGRAM_CONFIG)
                result = send_telegram_message(config, build_test_message())
                self._send_json(
                    {
                        "ok": True,
                        "message": "测试消息已发送到 Telegram。",
                        "message_id": result.get("message_id"),
                        "telegram": _safe_telegram_status(),
                    }
                )
                return

            plan = self._plan_from_payload(payload)

            if parsed.path == "/api/telegram/push-plan":
                config = require_telegram_config(TELEGRAM_CONFIG)
                result = send_telegram_message(config, build_plan_notification(plan))
                self._send_json(
                    {
                        "ok": True,
                        "message": "当前收益方案已推送到 Telegram。",
                        "message_id": result.get("message_id"),
                        "telegram": _safe_telegram_status(),
                        "preview": build_plan_notification(plan),
                    }
                )
                return

            body = plan_to_dict(plan)
            body["ok"] = True
            body["ics_content"] = build_ics_text(plan.reminders) if plan.reminders else ""
            body["ics_filename"] = "bnb-yield-cruiser-reminders.ics"
            body["telegram"] = _safe_telegram_status()
            body["telegram_available"] = _telegram_available()
            body["public_demo"] = PUBLIC_DEMO
            body["public_demo_notice"] = PUBLIC_DEMO_NOTICE if PUBLIC_DEMO else ""
            self._send_json(body)
        except KeyError as exc:
            self.send_error(HTTPStatus.BAD_REQUEST, f"Missing field: {exc}")
        except (LiveDataUnavailable, TelegramNotificationError) as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # pragma: no cover - defensive path for demo server
            self._send_json({"ok": False, "error": f"Planner error: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, format: str, *args) -> None:
        return

    def _plan_from_payload(self, payload: dict):
        profile = profile_from_dict(payload["profile"])
        return generate_plan(
            profile=profile,
            opportunities_path=DEFAULT_OPPORTUNITIES,
            mode=payload.get("mode", "auto"),
            use_wallet_balances=bool(payload.get("use_wallet_balances", False)),
            skip_public_events=bool(payload.get("skip_public_events", False)),
            has_live_credentials=has_live_credentials(),
        )

    def _serve_file(self, name: str, content_type: str) -> None:
        path = WEB_DIR / name
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8765"))
    server = ThreadingHTTPServer((host, port), DemoHandler)
    display_host = "127.0.0.1" if host == "0.0.0.0" else host
    print(f"BNB Yield Cruiser demo server running at http://{display_host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
