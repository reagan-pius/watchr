"""Canonical preferences paths inside an Instagram JSON export."""

from __future__ import annotations

from export_inventory import FileGroup

YOUR_TOPICS = FileGroup(
    key="your_topics",
    label="your topics",
    relative_paths=(
        "preferences/your_topics/your_topics.json",
        "preferences/your_topics/recommended_topics.json",
        "your_topics/your_topics.json",
    ),
)

REELS_TOPICS = FileGroup(
    key="reels_topics",
    label="reels topics",
    relative_paths=(
        "preferences/your_topics/your_reels_topics.json",
        "your_topics/your_reels_topics.json",
    ),
)

NOTIFICATIONS = FileGroup(
    key="notifications",
    label="notification preferences",
    relative_paths=(
        "preferences/settings/notification_preferences.json",
        "preferences/notification_preferences.json",
        "settings/notification_preferences.json",
    ),
)

COMMENTS_SETTINGS = FileGroup(
    key="comments_settings",
    label="comments settings",
    relative_paths=(
        "preferences/settings/comments_allowed_from.json",
        "comments_settings/comments_allowed_from.json",
        "preferences/comments_settings/comments_allowed_from.json",
    ),
)

MEDIA_SETTINGS = FileGroup(
    key="media_settings",
    label="media settings",
    relative_paths=(
        "preferences/settings/use_cross-app_messaging.json",
        "preferences/media_settings.json",
        "media_settings/use_cross-app_messaging.json",
    ),
)

PREFERENCES_FILE_GROUPS: tuple[FileGroup, ...] = (
    YOUR_TOPICS,
    REELS_TOPICS,
    NOTIFICATIONS,
    COMMENTS_SETTINGS,
    MEDIA_SETTINGS,
)
