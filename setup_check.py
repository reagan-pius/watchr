"""Pre-flight checks for clone-and-run setup (`--check` / doctor)."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from activity.paths import ACTIVITY_FILE_GROUPS
from ads.paths import ADS_FILE_GROUPS
from apps.paths import APPS_FILE_GROUPS
from connections.graph import (
    ConnectionGraph,
    _load_follower_entries,
    _load_following_entries,
    _load_app_follower_count,
)
from contacts.paths import CONTACTS_FILE_GROUPS
from export_inventory import FileStatus, build_inventory
from messages.paths import MESSAGE_ROOT_CANDIDATES
from preferences.paths import PREFERENCES_FILE_GROUPS
from security.paths import SECURITY_FILE_GROUPS
from shopping.paths import SHOPPING_FILE_GROUPS

MIN_PYTHON = (3, 10)


@dataclass
class CheckResult:
    ok: bool
    message: str


def _status(ok: bool) -> str:
    return "✓" if ok else "✗"


def _warn(ok: bool) -> str:
    return "⚠" if not ok else "✓"


def run_setup_check(export_dir: Path) -> int:
    """Print setup diagnostics. Returns exit code (0 = ready to analyze)."""
    export_dir = export_dir.resolve()
    lines: list[str] = []
    fatal = False

    py_ok = sys.version_info >= MIN_PYTHON
    lines.append(
        f"{_status(py_ok)}  Python {sys.version_info.major}.{sys.version_info.minor} "
        f"(need >={MIN_PYTHON[0]}.{MIN_PYTHON[1]})"
    )
    fatal |= not py_ok

    export_ok = export_dir.is_dir() and (
        (export_dir / "connections").is_dir()
        or (export_dir / "personal_information").is_dir()
    )
    lines.append(f"{_status(export_ok)}  Export folder: {export_dir}")
    fatal |= not export_ok

    conn = export_dir / "connections/followers_and_following"
    follower_files = sorted(conn.glob("followers_*.json")) if conn.is_dir() else []
    following_files = sorted(conn.glob("following*.json")) if conn.is_dir() else []

    if follower_files:
        raw_followers = len(_load_follower_entries(export_dir))
        names = ", ".join(p.name for p in follower_files)
        lines.append(f"✓  Follower files ({names}): {raw_followers} raw JSON entries")
    else:
        lines.append("✗  No followers_*.json — connection reports will fail")
        fatal = True

    if following_files:
        raw_following = len(_load_following_entries(export_dir))
        names = ", ".join(p.name for p in following_files)
        lines.append(f"✓  Following files ({names}): {raw_following} raw JSON entries")
    else:
        lines.append("✗  No following*.json — connection reports will fail")
        fatal = True

    graph = ConnectionGraph.from_export_dir(export_dir)
    if graph:
        lines.append(
            f"✓  Unique handles: {len(graph.followers)} followers, "
            f"{len(graph.following)} following, {len(graph.mutuals)} mutuals (computed)"
        )
        app_count = _load_app_follower_count(export_dir)
        if app_count is not None:
            pct = (len(graph.followers) / app_count * 100) if app_count else 0
            incomplete = graph.followers_incomplete
            mark = _warn(not incomplete)
            lines.append(
                f"{mark}  App insights report {app_count} followers; "
                f"export lists {len(graph.followers)} ({pct:.0f}% coverage)"
            )
            if incomplete:
                lines.append(
                    "⚠  Follower list looks incomplete — mutual / one-way counts "
                    "may not match the app"
                )
        else:
            lines.append("·  No audience_insights.json — app follower total unavailable")
    elif export_ok:
        lines.append("✗  Could not build connection graph from export files")
        fatal = True

    def add_group(title: str, groups) -> None:
        lines.append("")
        lines.append(f"{title}:")
        for item in build_inventory(export_dir, groups):
            mark = (
                "✓"
                if item.status == FileStatus.PRESENT
                else ("·" if item.status == FileStatus.EMPTY else "✗")
            )
            lines.append(f"{mark}  {item.label}")

    add_group("Activity files", ACTIVITY_FILE_GROUPS)
    add_group("Security files", SECURITY_FILE_GROUPS)
    add_group("Ads & tracking files", ADS_FILE_GROUPS)
    add_group("Apps & websites files", APPS_FILE_GROUPS)
    add_group("Contacts files", CONTACTS_FILE_GROUPS)
    add_group("Shopping files", SHOPPING_FILE_GROUPS)
    add_group("Preferences files", PREFERENCES_FILE_GROUPS)

    lines.append("")
    lines.append("Messages:")
    msg_ok = any((export_dir / rel).is_dir() for rel in MESSAGE_ROOT_CANDIDATES)
    lines.append(f"{_status(msg_ok)}  messages root (inbox / requests)")

    lines.append("")
    if fatal:
        lines.append("Not ready — fix the ✗ items above, then run the analyzer.")
    else:
        lines.append("Ready — run: python3 instagram_analysis.py --export-dir <path>")

    print("\n".join(lines))
    return 1 if fatal else 0
