"""Parse security-related Instagram export JSON."""

from __future__ import annotations

from collections import Counter
from typing import Any

from security.paths import (
    ACTIVE_SESSIONS,
    EMAIL_CHANGES,
    LOGIN_ACTIVITY,
    LOGIN_PROTECTION,
    PASSWORD_CHANGES,
)
from export_inventory import read_json_first


def parse_logins(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    rows = data.get("account_history_login_history") or []
    out: list[dict[str, Any]] = []
    for entry in rows:
        if not isinstance(entry, dict):
            continue
        d = entry.get("string_map_data") or {}
        time_ = (d.get("Time") or {}).get("timestamp")
        device = (
            (d.get("User agent") or d.get("User Agent") or {}).get("value")
            or "unknown device"
        )
        ip = (d.get("IP address") or d.get("IP Address") or {}).get("value") or "?"
        out.append(
            {
                "timestamp": int(time_) if isinstance(time_, (int, float)) else None,
                "device": str(device),
                "ip": str(ip),
            }
        )
    return out


def parse_sessions(data: Any) -> list[dict[str, str]]:
    if not isinstance(data, dict):
        return []
    rows = data.get("account_history_active_sessions") or []
    out: list[dict[str, str]] = []
    for s in rows:
        if not isinstance(s, dict):
            continue
        d = s.get("string_map_data") or {}
        out.append(
            {
                "device": (d.get("Device") or {}).get("value") or "?",
                "last_seen": (d.get("Last Seen") or {}).get("value") or "?",
            }
        )
    return out


def device_summary_from_logins(logins: list[dict[str, Any]]) -> tuple[tuple[str, int], ...]:
    return tuple(Counter(l["device"][:80] for l in logins if l.get("device")).most_common(15))


def _count_activity_rows(data: Any, *keys: str) -> int:
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in keys:
            val = data.get(key)
            if isinstance(val, list):
                return len(val)
        for val in data.values():
            if isinstance(val, list):
                return len(val)
    return 0


def parse_protection_note(data: Any) -> str | None:
    if data is None:
        return None
    if isinstance(data, dict):
        # Best-effort: count keys / list lengths
        lists = [v for v in data.values() if isinstance(v, list)]
        if lists:
            return f"protection-related entries: {sum(len(x) for x in lists)}"
        return f"file present ({len(data)} top-level keys)"
    if isinstance(data, list):
        return f"protection-related entries: {len(data)}"
    return "file present"


def load_security_parts(export_dir) -> dict[str, Any]:
    login, _ = read_json_first(export_dir, LOGIN_ACTIVITY.relative_paths)
    sessions, _ = read_json_first(export_dir, ACTIVE_SESSIONS.relative_paths)
    pw, _ = read_json_first(export_dir, PASSWORD_CHANGES.relative_paths)
    email, _ = read_json_first(export_dir, EMAIL_CHANGES.relative_paths)
    prot, prot_rel = read_json_first(export_dir, LOGIN_PROTECTION.relative_paths)
    return {
        "login": login,
        "sessions": sessions,
        "password": pw,
        "email": email,
        "protection": prot,
        "protection_present": prot_rel is not None,
    }
