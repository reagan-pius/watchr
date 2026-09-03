"""AppsInsights compute-once value."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from apps import parse as apps_parse
from apps.paths import APPS_FILE_GROUPS
from export_inventory import InventoryItem, build_inventory


@dataclass
class AppsInsights:
    inventory: list[InventoryItem] = field(default_factory=list)
    linked: list[tuple[str, int]] = field(default_factory=list)
    off_meta: list[tuple[str, int]] = field(default_factory=list)

    @classmethod
    def build(cls, export_dir: Path) -> AppsInsights:
        export_dir = export_dir.resolve()
        parts = apps_parse.load_apps_parts(export_dir)
        return cls(
            inventory=build_inventory(export_dir, APPS_FILE_GROUPS),
            linked=apps_parse._named_rows(parts["linked"]),
            off_meta=apps_parse._named_rows(parts["off"]),
        )
