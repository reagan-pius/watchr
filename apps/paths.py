"""Canonical apps/websites paths."""

from __future__ import annotations

from export_inventory import FileGroup

LINKED_APPS = FileGroup(
    key="linked_apps",
    label="apps and websites linked",
    relative_paths=(
        "apps_and_websites_off_of_instagram/apps_and_websites/apps_and_websites.json",
        "apps_and_websites_off_of_instagram/apps_and_websites/your_apps_and_websites.json",
        "apps_and_websites_off_of_instagram/linked_apps.json",
    ),
)

OFF_META = FileGroup(
    key="off_meta",
    label="activity off Meta technologies",
    relative_paths=(
        "apps_and_websites_off_of_instagram/apps_and_websites/your_activity_off_meta_technologies.json",
        "logged_information/ads_and_topics/off_instagram_activity.json",
    ),
)

APPS_FILE_GROUPS: tuple[FileGroup, ...] = (LINKED_APPS, OFF_META)
