"""Parse shopping-related Instagram export JSON."""

from __future__ import annotations

from typing import Any

from export_inventory import read_json_first
from shopping.paths import ORDERS, RECENTLY_VIEWED, WISHLIST


def _item_label(row: Any) -> str:
    if isinstance(row, str):
        return row
    if not isinstance(row, dict):
        return "?"
    smd = row.get("string_map_data") or {}
    for key in ("Product Name", "Name", "Title", "Merchant", "Shop", "Product"):
        node = smd.get(key) or {}
        if isinstance(node, dict) and node.get("value"):
            return str(node["value"])
    for key in ("title", "name", "product_name", "merchant_name"):
        if row.get(key):
            return str(row[key])
    for lv in row.get("label_values") or []:
        if isinstance(lv, dict) and lv.get("value"):
            return str(lv["value"])
    href = None
    if row.get("string_list_data"):
        href = row["string_list_data"][0].get("href") or row["string_list_data"][0].get("value")
    return str(href or "?")


def _extract_items(data: Any, *keys: str) -> list[str]:
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
    return [_item_label(r) for r in rows]


def load_shopping_parts(export_dir) -> dict[str, list[str]]:
    viewed, _ = read_json_first(export_dir, RECENTLY_VIEWED.relative_paths)
    wish, _ = read_json_first(export_dir, WISHLIST.relative_paths)
    orders, _ = read_json_first(export_dir, ORDERS.relative_paths)
    return {
        "viewed": _extract_items(
            viewed,
            "shopping_recently_viewed_items",
            "recently_viewed_items",
            "label_values",
        ),
        "wishlist": _extract_items(
            wish,
            "shopping_wishlist_items",
            "wishlist_items",
            "label_values",
        ),
        "orders": _extract_items(
            orders,
            "shopping_checkout_information",
            "orders",
            "checkout_information",
            "label_values",
        ),
    }
