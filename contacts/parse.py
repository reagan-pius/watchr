"""Parse contacts export files."""

from __future__ import annotations

from typing import Any

from contacts.paths import SYNCED
from export_inventory import read_json_first


def parse_contact_names(data: Any) -> list[str]:
    rows: list[Any]
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = (
            data.get("contacts_contact_info")
            or data.get("contacts")
            or data.get("label_values")
            or []
        )
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
        name = (
            row.get("name")
            or row.get("first_name")
            or (row.get("string_map_data") or {}).get("Name", {}).get("value")
            or (row.get("string_map_data") or {}).get("First Name", {}).get("value")
            or row.get("title")
        )
        if name:
            names.append(str(name))
        else:
            # Still count as a contact even without a display name
            names.append("(unnamed)")
    return names


def load_contacts(export_dir) -> list[str]:
    data, _ = read_json_first(export_dir, SYNCED.relative_paths)
    return parse_contact_names(data)
