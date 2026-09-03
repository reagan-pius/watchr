"""Parse preferences-related Instagram export JSON."""

from __future__ import annotations

from typing import Any

from export_inventory import read_json_first
from preferences.paths import (
    COMMENTS_SETTINGS,
    MEDIA_SETTINGS,
    NOTIFICATIONS,
    REELS_TOPICS,
    YOUR_TOPICS,
)


def _topic_names(data: Any, *keys: str) -> list[str]:
    rows: list[Any]
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = []
        for key in keys:
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
    names: list[str] = []
    for row in rows:
        if isinstance(row, str):
            names.append(row)
            continue
        if not isinstance(row, dict):
            continue
        smd = row.get("string_map_data") or {}
        name = (
            (smd.get("Name") or {}).get("value")
            or (smd.get("Topic") or {}).get("value")
            or row.get("name")
            or row.get("title")
            or row.get("value")
        )
        if name:
            names.append(str(name))
    return names


def _notification_rows(data: Any) -> list[tuple[str, str]]:
    """Return (label, value) pairs for notification prefs."""
    rows: list[Any]
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = data.get("settings_notification_preferences") or []
        if not rows:
            for val in data.values():
                if isinstance(val, list):
                    rows = val
                    break
    else:
        return []
    out: list[tuple[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        smd = row.get("string_map_data") or {}
        label = (
            (smd.get("Preference") or {}).get("value")
            or (smd.get("Name") or {}).get("value")
            or (smd.get("Channel") or {}).get("value")
            or row.get("preference")
            or row.get("name")
            or "?"
        )
        value = (
            (smd.get("Value") or {}).get("value")
            or (smd.get("Setting") or {}).get("value")
            or row.get("value")
            or row.get("enabled")
            or "?"
        )
        # Sometimes channel + type live as separate fields
        channel = (smd.get("Channel") or {}).get("value")
        typ = (smd.get("Type") or {}).get("value")
        if channel and typ and label == "?":
            label = f"{channel} / {typ}"
        elif channel and label == channel and typ:
            label = f"{channel} / {typ}"
        out.append((str(label), str(value)))
    return out


def _setting_summary(data: Any) -> list[str]:
    if data is None:
        return []
    if isinstance(data, list):
        return [str(x) for x in data[:50]]
    if isinstance(data, dict):
        smd = data.get("string_map_data")
        if isinstance(smd, dict):
            lines = []
            for key, val in smd.items():
                if isinstance(val, dict) and val.get("value") is not None:
                    lines.append(f"{key}: {val['value']}")
                elif isinstance(val, (str, int, bool)):
                    lines.append(f"{key}: {val}")
            if lines:
                return lines
        names = _topic_names(data)
        if names:
            return names
        lines = []
        for key, val in data.items():
            if key == "string_map_data":
                continue
            if isinstance(val, (str, int, bool)):
                lines.append(f"{key}: {val}")
            elif isinstance(val, dict):
                inner = val.get("value") if "value" in val else None
                if inner is not None:
                    lines.append(f"{key}: {inner}")
        return lines
    return [str(data)]


def load_preferences_parts(export_dir) -> dict[str, Any]:
    topics, _ = read_json_first(export_dir, YOUR_TOPICS.relative_paths)
    reels, _ = read_json_first(export_dir, REELS_TOPICS.relative_paths)
    notif, _ = read_json_first(export_dir, NOTIFICATIONS.relative_paths)
    comments, _ = read_json_first(export_dir, COMMENTS_SETTINGS.relative_paths)
    media, _ = read_json_first(export_dir, MEDIA_SETTINGS.relative_paths)
    return {
        "topics": _topic_names(topics, "topics_your_topics", "your_topics", "topics"),
        "reels_topics": _topic_names(
            reels, "topics_your_reels_topics", "your_reels_topics", "topics"
        ),
        "notifications": _notification_rows(notif),
        "comments": _setting_summary(comments),
        "media": _setting_summary(media),
    }
