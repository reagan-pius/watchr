"""Canonical shopping paths inside an Instagram JSON export."""

from __future__ import annotations

from export_inventory import FileGroup

RECENTLY_VIEWED = FileGroup(
    key="recently_viewed",
    label="recently viewed shopping items",
    relative_paths=(
        "your_instagram_activity/shopping/recently_viewed_items.json",
        "shopping/recently_viewed_items.json",
        "your_instagram_activity/shopping/recently_viewed.json",
    ),
)

WISHLIST = FileGroup(
    key="wishlist",
    label="wishlist items",
    relative_paths=(
        "your_instagram_activity/shopping/wishlist_items.json",
        "shopping/wishlist_items.json",
        "your_instagram_activity/shopping/wishlist.json",
    ),
)

ORDERS = FileGroup(
    key="orders",
    label="shopping orders / checkout",
    relative_paths=(
        "your_instagram_activity/shopping/checkout_information.json",
        "your_instagram_activity/shopping/orders.json",
        "shopping/checkout_information.json",
        "shopping/orders.json",
    ),
)

SHOPPING_FILE_GROUPS: tuple[FileGroup, ...] = (RECENTLY_VIEWED, WISHLIST, ORDERS)
