"""PreferencesInsights — compute-once preferences value for one export run."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from export_inventory import InventoryItem, build_inventory
from preferences import parse as preferences_parse
from preferences.paths import PREFERENCES_FILE_GROUPS


@dataclass
class PreferencesInsights:
    inventory: list[InventoryItem] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    reels_topics: list[str] = field(default_factory=list)
    notifications: list[tuple[str, str]] = field(default_factory=list)
    comments_settings: list[str] = field(default_factory=list)
    media_settings: list[str] = field(default_factory=list)

    @classmethod
    def build(cls, export_dir: Path) -> PreferencesInsights:
        export_dir = export_dir.resolve()
        parts = preferences_parse.load_preferences_parts(export_dir)
        return cls(
            inventory=build_inventory(export_dir, PREFERENCES_FILE_GROUPS),
            topics=parts["topics"],
            reels_topics=parts["reels_topics"],
            notifications=parts["notifications"],
            comments_settings=parts["comments"],
            media_settings=parts["media"],
        )
