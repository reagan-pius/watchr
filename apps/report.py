"""Render AppsInsights."""

from __future__ import annotations

from apps.insights import AppsInsights
from export_inventory import FileStatus, format_inventory_lines


def _cap(limit: int, total: int) -> int:
    if limit <= 0:
        return total
    return min(limit, total)


def format_apps_report(ins: AppsInsights, *, limit: int = 30) -> str:
    lines: list[str] = ["", "📋  Export inventory (apps & websites):"]
    lines.extend(format_inventory_lines(ins.inventory))
    if any(i.status == FileStatus.MISSING for i in ins.inventory):
        lines.append(
            "   Note: missing files were omitted from this ZIP — re-request those "
            "categories if you need them."
        )

    if ins.linked:
        show_n = _cap(limit, len(ins.linked))
        lines.append("")
        lines.append(f"🔗  Linked apps / websites ({len(ins.linked)}):")
        for name, count in ins.linked[:show_n]:
            suffix = f"  ({count} events)" if count else ""
            lines.append(f"   • {name}{suffix}")
        if show_n < len(ins.linked):
            lines.append(f"   ... and {len(ins.linked) - show_n} more")

    if ins.off_meta:
        show_n = _cap(limit, len(ins.off_meta))
        lines.append("")
        lines.append(f"🌐  Activity off Meta technologies ({len(ins.off_meta)}):")
        for name, count in ins.off_meta[:show_n]:
            lines.append(f"   • {name}  ({count} events)")
        if show_n < len(ins.off_meta):
            lines.append(f"   ... and {len(ins.off_meta) - show_n} more")

    if not ins.linked and not ins.off_meta:
        lines.append("")
        lines.append(
            "   No apps/websites detail found. Enable Apps and websites off of Instagram "
            "when requesting a download."
        )

    return "\n".join(lines).rstrip() + "\n"


def print_apps_report(ins: AppsInsights, *, limit: int = 30) -> None:
    print(format_apps_report(ins, limit=limit), end="")
