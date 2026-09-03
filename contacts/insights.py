"""ContactsInsights compute-once value."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from contacts import parse as contacts_parse
from contacts.paths import CONTACTS_FILE_GROUPS
from export_inventory import InventoryItem, build_inventory


@dataclass
class ContactsInsights:
    inventory: list[InventoryItem] = field(default_factory=list)
    names: list[str] = field(default_factory=list)

    @classmethod
    def build(cls, export_dir: Path) -> ContactsInsights:
        export_dir = export_dir.resolve()
        return cls(
            inventory=build_inventory(export_dir, CONTACTS_FILE_GROUPS),
            names=contacts_parse.load_contacts(export_dir),
        )
