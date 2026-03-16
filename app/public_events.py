from __future__ import annotations

from copy import deepcopy
import html
import json
import re
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Iterable
from urllib.parse import urlencode
from urllib.error import URLError
from urllib.request import Request, urlopen
from time import monotonic

from app.models import Opportunity

ARTICLE_LIST_API_URL = "https://www.binance.com/bapi/apex/v1/public/apex/cms/article/list/query"
ARTICLE_DETAIL_API_URL = "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query"
ANNOUNCEMENT_DETAIL_URL = "https://www.binance.com/en/support/announcement/detail/{code}"
CATEGORY_SEARCH_CONFIG = {
    "launchpool": {"catalog_ids": [48], "scan_pages": 3, "limit": 2},
    "hodler_airdrop": {"catalog_ids": [128, 48], "scan_pages": 2, "limit": 2},
    "megadrop": {"catalog_ids": [48, None, 128], "scan_pages": 3, "limit": 1},
}

KEYWORD_RULES = {
    "launchpool": ("launchpool",),
    "hodler_airdrop": ("hodler airdrops", "hodler airdrop"),
    "megadrop": ("megadrop",),
}


class PublicEventsUnavailable(RuntimeError):
    """Raised when official public event pages cannot be fetched or parsed."""


_PUBLIC_JSON_CACHE_LOCK = Lock()
_PUBLIC_JSON_CACHE: dict[str, tuple[float, dict]] = {}
_PUBLIC_JSON_TTL_SECONDS = 300.0


def _fetch(url: str, timeout: int = 10) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "bnb-yield-cruiser/0.1 (+https://www.binance.com/)",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "application/json, text/plain, */*",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            waf_action = response.headers.get("x-amzn-waf-action", "")
            if response.status == 202 and waf_action:
                raise PublicEventsUnavailable(
                    "币安公告页触发了官方反爬挑战，当前环境无法直接抓取公告列表，已回退到本地备用事件数据。"
                )
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read().decode(charset, errors="replace")
            if not body and waf_action:
                raise PublicEventsUnavailable(
                    "币安公告页触发了官方反爬挑战，当前环境无法直接抓取公告列表，已回退到本地备用事件数据。"
                )
            return body
    except URLError as exc:
        raise PublicEventsUnavailable(f"无法抓取 {url}：{exc}") from exc


def _fetch_json(url: str, timeout: int = 10) -> dict:
    with _PUBLIC_JSON_CACHE_LOCK:
        cached = _PUBLIC_JSON_CACHE.get(url)
    if cached and monotonic() - cached[0] <= _PUBLIC_JSON_TTL_SECONDS:
        return deepcopy(cached[1])

    raw = _fetch(url, timeout=timeout)
    if not raw:
        raise PublicEventsUnavailable(f"官方公告接口返回空结果：{url}")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PublicEventsUnavailable(f"官方公告接口返回了无法解析的 JSON：{url}") from exc

    if payload.get("success") is False or payload.get("code") not in {None, "000000"}:
        raise PublicEventsUnavailable(
            f"官方公告接口返回异常：{payload.get('message') or payload.get('code') or 'unknown error'}"
        )
    data = payload.get("data") or {}
    with _PUBLIC_JSON_CACHE_LOCK:
        _PUBLIC_JSON_CACHE[url] = (monotonic(), deepcopy(data))
    return deepcopy(data)


def _strip_tags(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _html_to_text(page_html: str) -> str:
    cleaned = re.sub(r"<script.*?</script>", " ", page_html, flags=re.S | re.I)
    cleaned = re.sub(r"<style.*?</style>", " ", cleaned, flags=re.S | re.I)
    cleaned = re.sub(r"<[^>]+>", "\n", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = cleaned.replace("\xa0", " ")
    cleaned = re.sub(r"\r", "\n", cleaned)
    cleaned = re.sub(r"\n{2,}", "\n", cleaned)
    return cleaned


def _ms_to_datetime(raw: int | float | str | None) -> datetime | None:
    if raw in (None, ""):
        return None
    try:
        milliseconds = int(raw)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(milliseconds / 1000, tz=timezone.utc)


def _cms_body_to_text(body: str) -> str:
    if not body:
        return ""
    try:
        root = json.loads(body)
    except json.JSONDecodeError:
        return _strip_tags(body)

    blocks = {"p", "div", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "br", "table", "tr"}
    parts: list[str] = []

    def walk(node) -> None:
        if isinstance(node, dict):
            if node.get("node") == "text":
                text = node.get("text", "")
                if text:
                    parts.append(text)
                return

            tag = str(node.get("tag", "")).lower()
            if tag in blocks:
                parts.append("\n")
            for child in node.get("child") or []:
                walk(child)
            if tag in blocks:
                parts.append("\n")
            return

        if isinstance(node, list):
            for item in node:
                walk(item)
            return

        if isinstance(node, str):
            parts.append(node)

    walk(root)
    text = html.unescape("".join(parts)).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def _build_article_list_url(page_no: int, page_size: int, catalog_id: int | None = None) -> str:
    params = {"type": 1, "pageNo": page_no, "pageSize": page_size}
    if catalog_id is not None:
        params["catalogId"] = catalog_id
    return f"{ARTICLE_LIST_API_URL}?{urlencode(params)}"


def _fetch_article_list(page_no: int = 1, page_size: int = 50, catalog_id: int | None = None) -> list[dict]:
    data = _fetch_json(_build_article_list_url(page_no=page_no, page_size=page_size, catalog_id=catalog_id))
    catalogs = data.get("catalogs") or []
    articles: list[dict] = []
    for catalog in catalogs:
        articles.extend(catalog.get("articles") or [])
    return articles


def _fetch_article_detail(article_code: str) -> dict:
    url = f"{ARTICLE_DETAIL_API_URL}?{urlencode({'articleCode': article_code})}"
    return _fetch_json(url)


def _utc_datetime(raw: str) -> datetime:
    return datetime.strptime(raw.strip(), "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)


def _extract_first_future(*dates: datetime | None, now: datetime | None = None) -> datetime | None:
    ordered = [date for date in dates if date is not None]
    if now is None:
        return ordered[0] if ordered else None
    future_dates = [date for date in ordered if date > now]
    return min(future_dates) if future_dates else None


def _find(pattern: str, text: str) -> re.Match[str] | None:
    return re.search(pattern, text, flags=re.I | re.S)


def parse_launchpool_detail(
    title: str,
    url: str,
    text: str,
    now: datetime | None = None,
    published_at: datetime | None = None,
) -> Opportunity:
    publish_match = _find(r"Published on\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2})", text)
    farming_match = _find(
        r"Farming Period:\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \(UTC\)\s*to\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \(UTC\)",
        text,
    )
    listing_match = _find(r"list .*? at (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \(UTC\)", text)
    symbol_match = re.search(r"\(([A-Z0-9]+)\)", title)

    published_at = _utc_datetime(publish_match.group(1)) if publish_match else published_at
    farming_start = _utc_datetime(farming_match.group(1)) if farming_match else None
    farming_end = _utc_datetime(farming_match.group(2)) if farming_match else None
    listing_at = _utc_datetime(listing_match.group(1)) if listing_match else None
    reminder_at = _extract_first_future(farming_start, farming_end, listing_at, now=now)
    symbol = symbol_match.group(1) if symbol_match else "待定"

    apr_value = 3.0
    apy_match = _find(r"annual percentage yield \(APY\).*?updated in real time", text)
    if apy_match:
        apr_value = 3.8

    note_parts = [f"{symbol} 的官方 Launchpool 活动。"]
    if farming_match:
        note_parts.append(
            f"挖矿时间为 {farming_start.isoformat()} 到 {farming_end.isoformat()}。"
        )
    if listing_at:
        note_parts.append(f"现货上线时间预计为 {listing_at.isoformat()}。")

    return Opportunity.from_dict(
        {
            "id": f"public-launchpool-{symbol.lower()}",
            "product_name": f"{symbol} Launchpool 机会",
            "category": "launchpool",
            "source_type": "official_announcement",
            "source_url": url,
            "asset": "BNB",
            "apr_type": "event",
            "apr_value": apr_value,
            "lock_days": 0,
            "liquidity_level": "medium",
            "event_eligibility": ["launchpool"],
            "risk_tier": "core",
            "confidence": 0.94 if published_at else 0.88,
            "deadline": reminder_at.isoformat() if reminder_at else None,
            "notes": " ".join(note_parts),
        }
    )


def parse_hodler_detail(
    title: str,
    url: str,
    text: str,
    now: datetime | None = None,
    published_at: datetime | None = None,
) -> Opportunity:
    publish_match = _find(r"Published on\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2})", text)
    eligibility_match = _find(
        r"from\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \(UTC\)\s+to\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \(UTC\)",
        text,
    )
    distribution_match = _find(r"distributed .*? by (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \(UTC\)", text)
    relative_distribution_match = _find(r"within\s+(\d+)\s+hours?\s+of this announcement", text)
    symbol_match = re.search(r"\(([A-Z0-9]+)\)", title)

    published_at = _utc_datetime(publish_match.group(1)) if publish_match else published_at
    eligibility_start = _utc_datetime(eligibility_match.group(1)) if eligibility_match else None
    eligibility_end = _utc_datetime(eligibility_match.group(2)) if eligibility_match else None
    distribution_at = _utc_datetime(distribution_match.group(1)) if distribution_match else None
    if distribution_at is None and relative_distribution_match and published_at is not None:
        distribution_at = published_at + timedelta(hours=int(relative_distribution_match.group(1)))
    reminder_at = _extract_first_future(distribution_at, eligibility_end, now=now)
    symbol = symbol_match.group(1) if symbol_match else "待定"

    note_parts = [f"{symbol} 的官方 HODLer 空投活动。"]
    if eligibility_match:
        note_parts.append(
            f"资格快照区间为 {eligibility_start.isoformat()} 到 {eligibility_end.isoformat()}。"
        )
    if distribution_at:
        note_parts.append(f"预计发放时间不晚于 {distribution_at.isoformat()}。")

    return Opportunity.from_dict(
        {
            "id": f"public-hodler-{symbol.lower()}",
            "product_name": f"{symbol} HODLer 空投",
            "category": "hodler_airdrop",
            "source_type": "official_announcement",
            "source_url": url,
            "asset": "BNB",
            "apr_type": "event",
            "apr_value": 2.6,
            "lock_days": 0,
            "liquidity_level": "high",
            "event_eligibility": ["hodler_airdrop"],
            "risk_tier": "core",
            "confidence": 0.94 if published_at else 0.88,
            "deadline": reminder_at.isoformat() if reminder_at else None,
            "notes": " ".join(note_parts),
        }
    )


def parse_megadrop_detail(
    title: str,
    url: str,
    text: str,
    now: datetime | None = None,
    published_at: datetime | None = None,
) -> Opportunity:
    period_match = _find(
        r"(?:Participation|Event|Subscription) Period:\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \(UTC\)\s*to\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \(UTC\)",
        text,
    )
    listing_match = _find(r"list .*? at (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \(UTC\)", text)
    symbol_match = re.search(r"\(([A-Z0-9]+)\)", title)
    period_start = _utc_datetime(period_match.group(1)) if period_match else None
    period_end = _utc_datetime(period_match.group(2)) if period_match else None
    listing_at = _utc_datetime(listing_match.group(1)) if listing_match else None
    reminder_at = _extract_first_future(period_end, listing_at, now=now)
    symbol = symbol_match.group(1) if symbol_match else "待定"

    confidence = 0.9 if published_at else 0.86

    return Opportunity.from_dict(
        {
            "id": f"public-megadrop-{symbol.lower()}",
            "product_name": f"{symbol} Megadrop 机会",
            "category": "megadrop",
            "source_type": "official_announcement",
            "source_url": url,
            "asset": "BNB",
            "apr_type": "event",
            "apr_value": 5.2,
            "lock_days": 30,
            "liquidity_level": "low",
            "event_eligibility": ["megadrop"],
            "risk_tier": "advanced",
            "confidence": confidence,
            "deadline": reminder_at.isoformat() if reminder_at else None,
            "notes": f"{symbol} 的官方 Megadrop 活动，适合锁仓 BNB 场景。",
        }
    )


def _relevant_entries(entries: Iterable[dict[str, str]], category: str, limit: int) -> list[dict[str, str]]:
    keywords = KEYWORD_RULES[category]
    matched = [
        entry
        for entry in entries
        if any(keyword in entry["title"].lower() for keyword in keywords)
    ]
    return matched[:limit]


def _load_relevant_entries(category: str) -> list[dict[str, str | datetime | None]]:
    config = CATEGORY_SEARCH_CONFIG[category]
    limit = int(config["limit"])
    scan_pages = int(config["scan_pages"])
    seen_codes: set[str] = set()
    candidates: list[dict[str, str | datetime | None]] = []

    for catalog_id in config["catalog_ids"]:
        for page_no in range(1, scan_pages + 1):
            rows = _fetch_article_list(page_no=page_no, page_size=50, catalog_id=catalog_id)
            if not rows:
                break

            normalized_rows: list[dict[str, str]] = []
            for row in rows:
                code = row.get("code")
                title = row.get("title")
                if not code or not title or code in seen_codes:
                    continue
                seen_codes.add(code)
                normalized_rows.append(
                    {
                        "code": code,
                        "title": title,
                        "url": ANNOUNCEMENT_DETAIL_URL.format(code=code),
                        "published_at": _ms_to_datetime(row.get("releaseDate")),
                    }
                )

            candidates.extend(_relevant_entries(normalized_rows, category, limit=len(normalized_rows)))
            if len(rows) < 50:
                break

    candidates.sort(
        key=lambda item: item.get("published_at") or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return candidates[:limit]


def load_public_event_opportunities(limit_per_category: int = 2, now: datetime | None = None) -> list[Opportunity]:
    opportunities: list[Opportunity] = []
    category_limits = {
        "launchpool": limit_per_category,
        "hodler_airdrop": limit_per_category,
        "megadrop": 1,
    }

    for category, limit in category_limits.items():
        original_limit = CATEGORY_SEARCH_CONFIG[category]["limit"]
        CATEGORY_SEARCH_CONFIG[category]["limit"] = limit
        try:
            entries = _load_relevant_entries(category)
        finally:
            CATEGORY_SEARCH_CONFIG[category]["limit"] = original_limit

        for entry in entries:
            detail = _fetch_article_detail(str(entry["code"]))
            detail_text = _cms_body_to_text(str(detail.get("body") or detail.get("contentJson") or ""))
            published_at = _ms_to_datetime(detail.get("publishDate")) or entry.get("published_at")

            if category == "launchpool":
                opportunities.append(
                    parse_launchpool_detail(
                        str(entry["title"]),
                        str(entry["url"]),
                        detail_text,
                        now=now,
                        published_at=published_at,
                    )
                )
            elif category == "hodler_airdrop":
                opportunities.append(
                    parse_hodler_detail(
                        str(entry["title"]),
                        str(entry["url"]),
                        detail_text,
                        now=now,
                        published_at=published_at,
                    )
                )
            elif category == "megadrop":
                opportunities.append(
                    parse_megadrop_detail(
                        str(entry["title"]),
                        str(entry["url"]),
                        detail_text,
                        now=now,
                        published_at=published_at,
                    )
                )

    if not opportunities:
        raise PublicEventsUnavailable("没有从币安官方公告接口里解析到可用的活动机会。")
    return opportunities


def merge_public_event_data(base: list[Opportunity], live_events: list[Opportunity]) -> list[Opportunity]:
    replacement_categories = {item.category for item in live_events}
    retained = [item for item in base if item.category not in replacement_categories]
    return retained + live_events
