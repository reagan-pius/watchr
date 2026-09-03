"""Message folder locations inside an Instagram JSON export."""

from __future__ import annotations

MESSAGE_ROOT_CANDIDATES: tuple[str, ...] = (
    "your_instagram_activity/messages",
    "messages",
)

INBOX_NAMES: tuple[str, ...] = ("inbox",)
REQUEST_NAMES: tuple[str, ...] = ("message_requests", "filtered", "filtered_threads")
