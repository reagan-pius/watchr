"""Render ShoppingInsights."""

from __future__ import annotations

from export_inventory import FileStatus, format_inventory_lines
from shopping.insights import ShoppingInsights


def _cap(limit: int, total: int) -> int:
    if limit <= 0:
        return total
    return min(limit, total)


def _sample_block(title: str, items: list[str], limit: int) -> list[str]:
    if not items:
        return []
    show_n = _cap(limit, len(items))
    lines = ["", f"{title} ({len(items)}):"]
    for item in items[:show_n]:
        lines.append(f"   • {item}")
    if show_n < len(items):
        lines.append(f"   ... and {len(items) - show_n} more")
    return lines


def format_shopping_report(ins: ShoppingInsights, *, limit: int = 30) -> str:
    lines: list[str] = ["", "📋  Export inventory (shopping):"]
    lines.extend(format_inventory_lines(ins.inventory))
    if any(i.status == FileStatus.MISSING for i in ins.inventory):
        lines.append(
            "   Note: missing files were omitted from this ZIP — enable Shopping "
            "when requesting a download if you need them."
        )

    lines.extend(_sample_block("🛍  Recently viewed items", ins.recently_viewed, limit))
    lines.extend(_sample_block("⭐  Wishlist", ins.wishlist, limit))
    lines.extend(_sample_block("🧾  Orders / checkout records", ins.orders, limit))

    if not ins.recently_viewed and not ins.wishlist and not ins.orders:
        lines.append("")
        lines.append(
            "   No shopping detail found in this export. "
            "Enable Shopping when requesting a download."
        )

    return "\n".join(lines).rstrip() + "\n"


def print_shopping_report(ins: ShoppingInsights, *, limit: int = 30) -> None:
    print(format_shopping_report(ins, limit=limit), end="")
