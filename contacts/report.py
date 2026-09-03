"""Render ContactsInsights — redacted sample by default."""

from __future__ import annotations

from contacts.insights import ContactsInsights
from export_inventory import FileStatus, format_inventory_lines


def _cap(limit: int, total: int) -> int:
    if limit <= 0:
        return total
    return min(limit, total)


def _redact_name(name: str) -> str:
    if name == "(unnamed)":
        return name
    parts = name.strip().split()
    if not parts:
        return "***"
    return " ".join(f"{p[0]}***" if p else "***" for p in parts)


def format_contacts_report(
    ins: ContactsInsights, *, limit: int = 30, redact: bool = True
) -> str:
    lines: list[str] = ["", "📋  Export inventory (contacts):"]
    lines.extend(format_inventory_lines(ins.inventory))
    if any(i.status == FileStatus.MISSING for i in ins.inventory):
        lines.append(
            "   Note: missing files were omitted from this ZIP — re-request Contacts "
            "if you need this section."
        )

    if ins.names:
        show_n = _cap(limit, len(ins.names))
        lines.append("")
        lines.append(f"📇  Synced / uploaded contacts ({len(ins.names)}):")
        lines.append(
            "   Samples are redacted by default (use --no-redact for raw names)."
            if redact
            else "   Showing raw contact names (--no-redact)."
        )
        for name in ins.names[:show_n]:
            display = _redact_name(name) if redact else name
            lines.append(f"   • {display}")
        if show_n < len(ins.names):
            lines.append(f"   ... and {len(ins.names) - show_n} more")
    else:
        lines.append("")
        lines.append(
            "   No contacts file found. Enable Contacts when requesting a download."
        )

    return "\n".join(lines).rstrip() + "\n"


def print_contacts_report(
    ins: ContactsInsights, *, limit: int = 30, redact: bool = True
) -> None:
    print(format_contacts_report(ins, limit=limit, redact=redact), end="")
