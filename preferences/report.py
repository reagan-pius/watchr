"""Render PreferencesInsights."""

from __future__ import annotations

from export_inventory import FileStatus, format_inventory_lines
from preferences.insights import PreferencesInsights


def _cap(limit: int, total: int) -> int:
    if limit <= 0:
        return total
    return min(limit, total)


def format_preferences_report(ins: PreferencesInsights, *, limit: int = 30) -> str:
    lines: list[str] = ["", "📋  Export inventory (preferences):"]
    lines.extend(format_inventory_lines(ins.inventory))
    if any(i.status == FileStatus.MISSING for i in ins.inventory):
        lines.append(
            "   Note: missing files were omitted from this ZIP — enable Preferences "
            "when requesting a download if you need them."
        )

    if ins.topics:
        show_n = _cap(limit, len(ins.topics))
        lines.append("")
        lines.append(f"🗂  Your topics ({len(ins.topics)}):")
        for t in ins.topics[:show_n]:
            lines.append(f"   • {t}")
        if show_n < len(ins.topics):
            lines.append(f"   ... and {len(ins.topics) - show_n} more")

    if ins.reels_topics:
        show_n = _cap(limit, len(ins.reels_topics))
        lines.append("")
        lines.append(f"🎬  Reels topics ({len(ins.reels_topics)}):")
        for t in ins.reels_topics[:show_n]:
            lines.append(f"   • {t}")
        if show_n < len(ins.reels_topics):
            lines.append(f"   ... and {len(ins.reels_topics) - show_n} more")

    if ins.notifications:
        show_n = _cap(limit, len(ins.notifications))
        lines.append("")
        lines.append(f"🔔  Notification preferences ({len(ins.notifications)}):")
        for label, value in ins.notifications[:show_n]:
            lines.append(f"   • {label}: {value}")
        if show_n < len(ins.notifications):
            lines.append(f"   ... and {len(ins.notifications) - show_n} more")

    if ins.comments_settings:
        lines.append("")
        lines.append("💬  Comments settings:")
        for s in ins.comments_settings[: _cap(limit, len(ins.comments_settings))]:
            lines.append(f"   • {s}")

    if ins.media_settings:
        lines.append("")
        lines.append("📷  Media / messaging settings:")
        for s in ins.media_settings[: _cap(limit, len(ins.media_settings))]:
            lines.append(f"   • {s}")

    if not any(
        [
            ins.topics,
            ins.reels_topics,
            ins.notifications,
            ins.comments_settings,
            ins.media_settings,
        ]
    ):
        lines.append("")
        lines.append(
            "   No preferences detail found in this export. "
            "Enable Preferences when requesting a download."
        )

    return "\n".join(lines).rstrip() + "\n"


def print_preferences_report(ins: PreferencesInsights, *, limit: int = 30) -> None:
    print(format_preferences_report(ins, limit=limit), end="")
