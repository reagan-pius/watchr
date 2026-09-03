"""ShoppingInsights — compute-once shopping value for one export run."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from export_inventory import InventoryItem, build_inventory
from shopping import parse as shopping_parse
from shopping.paths import SHOPPING_FILE_GROUPS


@dataclass
class ShoppingInsights:
    inventory: list[InventoryItem] = field(default_factory=list)
    recently_viewed: list[str] = field(default_factory=list)
    wishlist: list[str] = field(default_factory=list)
    orders: list[str] = field(default_factory=list)

    @classmethod
    def build(cls, export_dir: Path) -> ShoppingInsights:
        export_dir = export_dir.resolve()
        parts = shopping_parse.load_shopping_parts(export_dir)
        return cls(
            inventory=build_inventory(export_dir, SHOPPING_FILE_GROUPS),
            recently_viewed=parts["viewed"],
            wishlist=parts["wishlist"],
            orders=parts["orders"],
        )
