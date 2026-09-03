"""Canonical contacts paths."""

from __future__ import annotations

from export_inventory import FileGroup

SYNCED = FileGroup(
    key="synced_contacts",
    label="synced contacts",
    relative_paths=(
        "connections/contacts/synced_contacts.json",
        "contacts/synced_contacts.json",
        "personal_information/information_about_you/contacts.json",
        "personal_information/information_about_you/synced_contacts.json",
    ),
)

CONTACTS_FILE_GROUPS: tuple[FileGroup, ...] = (SYNCED,)
