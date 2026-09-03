"""Render ActivityInsights as terminal report lines."""

from __future__ import annotations

from datetime import datetime, timezone

from activity.insights import ActivityInsights
from export_inventory import FileStatus, format_inventory_lines


def _cap(limit: int, total: int) -> int:
    if limit <= 0:
        return total
    return min(limit, total)


def _ts(unix: int | None) -> str:
    if not unix:
        return "?"
    return datetime.fromtimestamp(unix, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def format_activity_report(ins: ActivityInsights, *, limit: int = 30) -> str:
    lines: list[str] = ["", "📋  Export inventory (activity):"]
    lines.extend(format_inventory_lines(ins.inventory))
    if any(i.status == FileStatus.MISSING for i in ins.inventory):
        lines.append(
            "   Note: missing files were omitted from this ZIP — re-request those "
            "categories if you need them."
        )

    if ins.post_total:
        lines.append("")
        lines.append(f"📸  Posts by month ({ins.post_total} total):")
        for mc in ins.posts_by_month:
            lines.append(f"   {mc.month}  {'█' * min(mc.count, 40)} {mc.count}")

    if ins.story_total:
        lines.append("")
        lines.append(f"📖  Stories in archive ({ins.story_total}):")
        for mc in ins.stories_by_month:
            lines.append(f"   {mc.month}  {'█' * min(mc.count, 40)} {mc.count}")

    if ins.reel_total:
        lines.append("")
        lines.append(f"🎬  Reels ({ins.reel_total}):")
        for mc in ins.reels_by_month:
            lines.append(f"   {mc.month}  {'█' * min(mc.count, 40)} {mc.count}")

    if ins.liked_posts_total:
        show_n = _cap(min(limit, 20) if limit > 0 else 20, len(ins.recent_liked_posts))
        lines.append("")
        lines.append(f"❤️   You've liked {ins.liked_posts_total} posts. Most recent {show_n}:")
        for ev in ins.recent_liked_posts[:show_n]:
            lines.append(f"   • {ev.label}  @ {_ts(ev.timestamp)}")

    if ins.liked_comments_total:
        lines.append("")
        lines.append(f"💬  You've liked {ins.liked_comments_total} comments.")

    if ins.comment_targets:
        lines.append("")
        lines.append("🗨️   Top accounts you commented on:")
        for account, count in ins.comment_targets:
            lines.append(f"   {count:>4}x  {account}")

    if ins.search_total:
        show_n = _cap(min(limit, 20) if limit > 0 else 20, len(ins.top_searches))
        lines.append("")
        lines.append(f"🔍  Top searched accounts ({ins.search_total} total):")
        for term, count in ins.top_searches[:show_n]:
            lines.append(f"   {count:>3}x  {term}")

    if ins.saved_total:
        show_n = _cap(min(limit, 20) if limit > 0 else 20, len(ins.recent_saved))
        lines.append("")
        lines.append(f"🔖  Saved items ({ins.saved_total}). Sample {show_n}:")
        for ev in ins.recent_saved[:show_n]:
            lines.append(f"   • {ev.label}  @ {_ts(ev.timestamp)}")

    if ins.story_likes_total or ins.story_polls_total:
        lines.append("")
        lines.append("✨  Story interactions:")
        if ins.story_likes_total:
            lines.append(f"   Story likes: {ins.story_likes_total}")
        if ins.story_polls_total:
            lines.append(f"   Poll responses: {ins.story_polls_total}")

    if not any(
        [
            ins.post_total,
            ins.story_total,
            ins.reel_total,
            ins.liked_posts_total,
            ins.liked_comments_total,
            ins.comment_targets,
            ins.search_total,
            ins.saved_total,
            ins.story_likes_total,
            ins.story_polls_total,
        ]
    ):
        lines.append("")
        lines.append(
            "   No activity detail files found in this export. "
            "Enable Your Instagram activity when requesting a download."
        )

    return "\n".join(lines).rstrip() + "\n"


def print_activity_report(ins: ActivityInsights, *, limit: int = 30) -> None:
    print(format_activity_report(ins, limit=limit), end="")
