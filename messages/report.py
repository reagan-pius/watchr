"""Render MessagesInsights — never includes message bodies."""

from __future__ import annotations

from datetime import datetime, timezone

from messages.insights import MessagesInsights


def _cap(limit: int, total: int) -> int:
    if limit <= 0:
        return total
    return min(limit, total)


def _ms(ts: int | None) -> str:
    if not ts:
        return "?"
    return datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m")


def format_messages_report(ins: MessagesInsights, *, limit: int = 30) -> str:
    lines: list[str] = []
    if ins.root_rel is None:
        return (
            "\n📋  Messages:\n"
            "   ✗  No messages folder in this ZIP "
            "(your_instagram_activity/messages or messages/)\n"
            "   Enable Messages when requesting a download if you need this section.\n"
        )

    lines.append("")
    lines.append("📋  Messages (metadata only — message text is never printed):")
    lines.append(f"   ✓  Root: {ins.root_rel}")
    lines.append(f"   Threads: {len(ins.threads)}  "
                 f"(inbox {ins.inbox_count}, requests {ins.request_count})")
    lines.append(f"   Messages (count only): {ins.message_total}")
    lines.append(f"   Attached media files on disk: {ins.media_total}")

    if not ins.threads:
        lines.append("   (No conversation folders with message_*.json found)")
        return "\n".join(lines).rstrip() + "\n"

    show_n = _cap(limit, len(ins.threads))
    lines.append("")
    lines.append(f"💬  Largest threads (sample {show_n} of {len(ins.threads)}):")
    for t in ins.threads[:show_n]:
        people = ", ".join(t.participants[:4]) if t.participants else t.title
        if len(t.participants) > 4:
            people += f" +{len(t.participants) - 4}"
        span = f"{_ms(t.first_ts_ms)} → {_ms(t.last_ts_ms)}"
        lines.append(
            f"   • [{t.bucket}] {t.title}  —  {t.message_count} msgs, "
            f"{t.media_file_count} media, {span}"
        )
        lines.append(f"       participants: {people}")

    if show_n < len(ins.threads):
        lines.append(
            f"   ... and {len(ins.threads) - show_n} more "
            "(raise --ads-limit or use 0 for all)"
        )
    lines.append(
        "   Privacy: Watchr does not print DM bodies. Open message_*.json locally if needed."
    )
    return "\n".join(lines).rstrip() + "\n"


def print_messages_report(ins: MessagesInsights, *, limit: int = 30) -> None:
    print(format_messages_report(ins, limit=limit), end="")
