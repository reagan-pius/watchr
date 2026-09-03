"""Export inventory — present / missing / empty status for logical file groups.

Shared by report sections and ``--check`` so optional Meta files get one
coherent inventory instead of absolute-path ``[!] File not found`` spam.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class FileStatus(str, Enum):
    PRESENT = "present"
    MISSING = "missing"
    EMPTY = "empty"


@dataclass(frozen=True)
class FileGroup:
    """One logical export artifact that may live at several Meta path aliases."""

    key: str
    label: str
    relative_paths: tuple[str, ...]


@dataclass(frozen=True)
class InventoryItem:
    key: str
    label: str
    status: FileStatus
    resolved_path: str | None  # relative path that matched, if any


def _is_empty_payload(data: object) -> bool:
    if data is None:
        return True
    if isinstance(data, (list, dict, str)) and len(data) == 0:
        return True
    return False


def resolve_group(export_dir: Path, group: FileGroup) -> InventoryItem:
    """Classify a file group under ``export_dir``."""
    export_dir = export_dir.resolve()
    for rel in group.relative_paths:
        full = export_dir / rel
        if not full.is_file():
            continue
        try:
            with full.open(encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            # Unreadable counts as present for inventory; parsers decide later.
            return InventoryItem(group.key, group.label, FileStatus.PRESENT, rel)
        if _is_empty_payload(data):
            return InventoryItem(group.key, group.label, FileStatus.EMPTY, rel)
        return InventoryItem(group.key, group.label, FileStatus.PRESENT, rel)
    return InventoryItem(group.key, group.label, FileStatus.MISSING, None)


def build_inventory(export_dir: Path, groups: list[FileGroup] | tuple[FileGroup, ...]) -> list[InventoryItem]:
    return [resolve_group(export_dir, g) for g in groups]


def format_inventory_lines(items: list[InventoryItem], *, indent: str = "   ") -> list[str]:
    """Human-readable inventory lines (no absolute paths)."""
    marks = {
        FileStatus.PRESENT: "✓",
        FileStatus.EMPTY: "·",
        FileStatus.MISSING: "✗",
    }
    lines: list[str] = []
    for item in items:
        mark = marks[item.status]
        suffix = ""
        if item.status == FileStatus.EMPTY:
            suffix = " (empty)"
        elif item.status == FileStatus.MISSING:
            suffix = " (not in this ZIP)"
        lines.append(f"{indent}{mark}  {item.label}{suffix}")
    return lines


def first_existing_path(export_dir: Path, relative_paths: list[str] | tuple[str, ...]) -> Path | None:
    """Return the first existing file path, or None."""
    export_dir = export_dir.resolve()
    for rel in relative_paths:
        full = export_dir / rel
        if full.is_file():
            return full
    return None


def read_json_first(
    export_dir: Path, relative_paths: list[str] | tuple[str, ...]
) -> tuple[object | None, str | None]:
    """Load the first existing JSON among aliases. Returns (data, relative_path)."""
    export_dir = export_dir.resolve()
    path = first_existing_path(export_dir, relative_paths)
    if path is None:
        return None, None
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, None
    rel = str(path.relative_to(export_dir))
    return data, rel
