from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.models import ReminderItem


def _format_ics_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _escape_ics_text(value: str) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def build_ics_text(reminders: list[ReminderItem]) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//BNB Yield Cruiser//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape_ics_text('BNB 收益巡航官提醒')}",
    ]

    for index, reminder in enumerate(reminders, start=1):
        stamp = _format_ics_datetime(reminder.when)
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:bnb-yield-cruiser-{index}@local",
                f"DTSTAMP:{stamp}",
                f"DTSTART:{stamp}",
                f"SUMMARY:{_escape_ics_text(reminder.title)}",
                f"DESCRIPTION:{_escape_ics_text(f'{reminder.description} 来源: {reminder.source_url}')}",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    return "\n".join(lines) + "\n"


def write_ics(reminders: list[ReminderItem], output_path: str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_ics_text(reminders))
    return path
