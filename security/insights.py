"""SecurityInsights — compute-once security value for one export run."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from export_inventory import InventoryItem, build_inventory
from security import parse as security_parse
from security.paths import SECURITY_FILE_GROUPS


@dataclass
class SecurityInsights:
    inventory: list[InventoryItem] = field(default_factory=list)
    logins: list[dict] = field(default_factory=list)
    sessions: list[dict] = field(default_factory=list)
    top_devices: tuple[tuple[str, int], ...] = ()
    password_change_count: int = 0
    email_change_count: int = 0
    protection_note: str | None = None

    @classmethod
    def build(cls, export_dir: Path) -> SecurityInsights:
        export_dir = export_dir.resolve()
        parts = security_parse.load_security_parts(export_dir)
        logins = security_parse.parse_logins(parts["login"])
        return cls(
            inventory=build_inventory(export_dir, SECURITY_FILE_GROUPS),
            logins=logins,
            sessions=security_parse.parse_sessions(parts["sessions"]),
            top_devices=security_parse.device_summary_from_logins(logins),
            password_change_count=security_parse._count_activity_rows(
                parts["password"],
                "account_history_password_change",
                "password_change_activity",
            ),
            email_change_count=security_parse._count_activity_rows(
                parts["email"],
                "account_history_email_change",
                "email_address_change",
            ),
            protection_note=security_parse.parse_protection_note(parts["protection"])
            if parts["protection_present"]
            else None,
        )
