"""Render SecurityInsights as terminal report lines."""

from __future__ import annotations

from datetime import datetime, timezone

from export_inventory import FileStatus, format_inventory_lines
from security.insights import SecurityInsights


def _cap(limit: int, total: int) -> int:
    if limit <= 0:
        return total
    return min(limit, total)


def _ts(unix: int | None) -> str:
    if not unix:
        return "?"
    return datetime.fromtimestamp(unix, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def _mask_ip(ip: str) -> str:
    parts = ip.split(".")
    return ".".join([*parts[:2], "***", "***"]) if len(parts) == 4 else "***"


def format_security_report(
    ins: SecurityInsights, *, limit: int = 30, redact: bool = True
) -> str:
    lines: list[str] = ["", "📋  Export inventory (security):"]
    lines.extend(format_inventory_lines(ins.inventory))
    if any(i.status == FileStatus.MISSING for i in ins.inventory):
        lines.append(
            "   Note: missing files were omitted from this ZIP — re-request those "
            "categories if you need them."
        )

    if ins.logins:
        show_n = _cap(min(limit, 15) if limit > 0 else 15, len(ins.logins))
        lines.append("")
        lines.append(f"🔐  Login history ({len(ins.logins)} entries). Most recent {show_n}:")
        for entry in ins.logins[:show_n]:
            ip = entry.get("ip") or "?"
            if redact:
                ip = _mask_ip(ip)
            device = (entry.get("device") or "unknown device")[:60]
            lines.append(f"   {_ts(entry.get('timestamp'))}  |  {ip}  |  {device}")

    if ins.top_devices:
        lines.append("")
        lines.append("💻  Devices seen in login history:")
        for device, count in ins.top_devices:
            lines.append(f"   {count:>3}x  {device}")

    if ins.sessions:
        lines.append("")
        lines.append(f"📱  Active sessions ({len(ins.sessions)}):")
        for s in ins.sessions:
            lines.append(f"   • {s.get('device', '?')}  —  {s.get('last_seen', '?')}")

    if ins.password_change_count or ins.email_change_count or ins.protection_note:
        lines.append("")
        lines.append("🛡  Account security events:")
        if ins.password_change_count:
            lines.append(f"   Password changes recorded: {ins.password_change_count}")
        if ins.email_change_count:
            lines.append(f"   Email changes recorded: {ins.email_change_count}")
        if ins.protection_note:
            lines.append(f"   Login protection / 2FA: {ins.protection_note}")

    if not any([ins.logins, ins.sessions, ins.password_change_count, ins.email_change_count, ins.protection_note]):
        lines.append("")
        lines.append(
            "   No security detail files found in this export. "
            "Enable Security and login information when requesting a download."
        )

    return "\n".join(lines).rstrip() + "\n"


def print_security_report(
    ins: SecurityInsights, *, limit: int = 30, redact: bool = True
) -> None:
    print(format_security_report(ins, limit=limit, redact=redact), end="")
