"""Parse apps/websites export files."""

from __future__ import annotations

from typing import Any

from apps.paths import LINKED_APPS, OFF_META
from export_inventory import read_json_first


def _named_rows(data: Any) -> list[tuple[str, int]]:
    rows: list[Any]
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = []
        for key in (
            "installed_apps",
            "apps_and_websites",
            "off_instagram_activity_v2",
            "your_off_meta_activity_v2",
            "off_facebook_activity_v2",
        ):
            if isinstance(data.get(key), list):
                rows = data[key]
                break
        if not rows:
            for val in data.values():
                if isinstance(val, list):
                    rows = val
                    break
    else:
        return []
    out: list[tuple[str, int]] = []
    for row in rows:
        if isinstance(row, str):
            out.append((row, 0))
            continue
        if not isinstance(row, dict):
            continue
        name = (
            row.get("name")
            or row.get("title")
            or (row.get("string_map_data") or {}).get("Name", {}).get("value")
            or "?"
        )
        events = row.get("events") or row.get("event_list") or []
        count = len(events) if isinstance(events, list) else 0
        out.append((str(name), count))
    return out


def load_apps_parts(export_dir) -> dict[str, Any]:
    linked, _ = read_json_first(export_dir, LINKED_APPS.relative_paths)
    off, _ = read_json_first(export_dir, OFF_META.relative_paths)
    return {"linked": linked, "off": off}
