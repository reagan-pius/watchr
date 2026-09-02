"""Pre-flight checks for clone-and-run setup (`--check` / doctor)."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from connections.graph import (
    ConnectionGraph,
    _load_follower_entries,
    _load_following_entries,
    _load_app_follower_count,
    _read_json_file,
)

MIN_PYTHON = (3, 10)

OPTIONAL_REPORT_FILES = [
    (
        "posts",
        [
            "your_instagram_activity/content/posts_1.json",
            "your_instagram_activity/media/posts_1.json",
        ],
    ),
    (
        "stories",
        [
            "your_instagram_activity/media/stories.json",
            "your_instagram_activity/content/stories.json",
        ],
    ),
    (
        "login history",
        [
            "security_and_login_information/login_and_profile_creation/login_activity.json",
            "security_and_login_information/login_and_account_creation/login_activity.json",
        ],
    ),
    (
        "ad interests",
        [
            "ads_information/instagram_ads_and_businesses/ads_interests.json",
            "ads_information/instagram_ads_and_businesses/other_categories_used_to_reach_you.json",
        ],
    ),
]


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

    lines.append("")
    lines.append("Optional report sections:")
    for label, rel_paths in OPTIONAL_REPORT_FILES:
        found = any((export_dir / rel).is_file() for rel in rel_paths)
        lines.append(f"{_status(found)}  {label}")

    lines.append("")
    if fatal:
        lines.append("Not ready — fix the ✗ items above, then run the analyzer.")
    else:
        lines.append("Ready — run: python3 instagram_analysis.py --export-dir <path>")

    print("\n".join(lines))
    return 1 if fatal else 0
