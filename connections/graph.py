"""
Connection graph — followers, following, and derived sets from an export folder.

Single adapter seam for export JSON variants (list vs relationships_* keys,
split followers_*.json files) and optional app-reported totals from insights.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

COMPLETENESS_THRESHOLD = 0.8

_IG_HREF = re.compile(r"instagram\.com/(?:_u/)?([^/?#]+)", re.I)
_HREF_SKIP = frozenset(
    {"p", "reel", "reels", "stories", "tv", "explore", "accounts", "share", ""}
)

_RELATIONSHIP_LIST_KEYS = (
    "relationships_followers",
    "relationships_following",
    "relationships_close_friends",
    "relationships_blocked_users",
    "relationships_restricted_users",
    "relationships_permanent_follow_requests",
)


def auto_detect_export_dir(base: Path | None = None) -> Path | None:
    here = base or Path(__file__).resolve().parent.parent
    candidates = sorted(p for p in here.glob("instagram-*") if p.is_dir())
    return candidates[0] if candidates else None


def _read_json_file(full: Path):
    if not full.is_file():
        return None
    with open(full, encoding="utf-8") as f:
        return json.load(f)


def _username_from_instagram_href(href: str) -> str | None:
    m = _IG_HREF.search(href or "")
    if not m:
        return None
    u = m.group(1).strip()
    if not u or u.casefold() in _HREF_SKIP:
        return None
    return u


def _norm_handle(u: str) -> str:
    return u.strip().casefold()


def username_from_connection_entry(entry: dict) -> str | None:
    """Username from a followers/following-style entry (export format varies)."""
    sld = entry.get("string_list_data") or []
    if sld and isinstance(sld[0], dict):
        first = sld[0]
        v = first.get("value")
        if v:
            return str(v).strip()
        hu = _username_from_instagram_href(first.get("href") or "")
        if hu:
            return hu
    title = (entry.get("title") or "").strip()
    return title or None


def _entries_from_relationship_file(data) -> list:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in _RELATIONSHIP_LIST_KEYS:
            entries = data.get(key)
            if isinstance(entries, list):
                return entries
    return []


def _load_follower_entries(export_dir: Path) -> list:
    """Merge followers_1.json, followers_2.json, … (Instagram splits large lists)."""
    d = export_dir / "connections/followers_and_following"
    if not d.is_dir():
        return []
    out: list = []
    for p in sorted(d.glob("followers_*.json")):
        data = _read_json_file(p)
        if data is not None:
            out.extend(_entries_from_relationship_file(data))
    return out


def _load_following_entries(export_dir: Path) -> list:
    d = export_dir / "connections/followers_and_following"
    if not d.is_dir():
        return []
    acc: list = []
    for p in sorted(d.glob("following*.json")):
        data = _read_json_file(p)
        if data is not None:
            acc.extend(_entries_from_relationship_file(data))
    return acc


def _handle_sets_from_entries(entries: list) -> tuple[set[str], dict[str, str]]:
    """(casefolded usernames, casefold -> one spelling for display)."""
    keys: set[str] = set()
    display: dict[str, str] = {}
    for e in entries:
        u = username_from_connection_entry(e)
        if not u:
            continue
        k = _norm_handle(u)
        keys.add(k)
        display.setdefault(k, u)
    return keys, display


def _load_app_follower_count(export_dir: Path) -> int | None:
    """App-reported follower total from audience insights, if present in the export."""
    path = (
        export_dir
        / "logged_information/past_instagram_insights/audience_insights.json"
    )
    data = _read_json_file(path)
    if not isinstance(data, dict):
        return None
    for block in data.get("organic_insights_audience", []):
        smd = block.get("string_map_data") or {}
        raw = smd.get("Followers", {}).get("value")
        if raw is not None:
            try:
                return int(str(raw).strip().replace(",", ""))
            except ValueError:
                continue
    return None


def iter_connection_handles(export_dir: Path) -> list[str]:
    """All handles from follower/following/close-friends/blocked connection files."""
    conn = export_dir / "connections/followers_and_following"
    if not conn.is_dir():
        return []
    paths = list(conn.glob("followers_*.json"))
    paths += list(conn.glob("following*.json"))
    paths += [
        conn / "close_friends.json",
        conn / "blocked_accounts.json",
    ]
    handles: list[str] = []
    seen: set[str] = set()
    for p in paths:
        if not p.is_file():
            continue
        data = _read_json_file(p)
        if data is None:
            continue
        for entry in _entries_from_relationship_file(data):
            if not isinstance(entry, dict):
                continue
            h = username_from_connection_entry(entry)
            if h and h not in seen:
                seen.add(h)
                handles.append(h)
    return handles


@dataclass
class ConnectionGraph:
    """Follower/following sets and derived metrics for one export snapshot."""

    followers: set[str] = field(default_factory=set)
    following: set[str] = field(default_factory=set)
    display: dict[str, str] = field(default_factory=dict)
    app_follower_count: int | None = None
    export_dir: Path | None = None

    @property
    def mutuals(self) -> set[str]:
        return self.followers & self.following

    @property
    def not_following_back(self) -> set[str]:
        return self.following - self.followers

    @property
    def not_followed_back(self) -> set[str]:
        return self.followers - self.following

    @property
    def follower_completeness(self) -> float | None:
        if self.app_follower_count is None or self.app_follower_count <= 0:
            return None
        return len(self.followers) / self.app_follower_count

    @property
    def followers_incomplete(self) -> bool:
        ratio = self.follower_completeness
        if ratio is None:
            return False
        return ratio < COMPLETENESS_THRESHOLD

    @property
    def export_only_label(self) -> str:
        return "export-only — follower list incomplete" if self.followers_incomplete else ""

    def show(self, key: str) -> str:
        return self.display.get(key, key)

    def with_promoted(self, promoted: set[str]) -> "ConnectionGraph":
        """Return a copy with ``promoted`` handles added to the followers set.

        Promoted handles are curated-confirmed followers (never denied ones),
        so they surface in ``mutuals`` (and other follower-side properties)
        without mutating the original graph. ADR-0004.
        """
        return ConnectionGraph(
            followers=self.followers | set(promoted),
            following=set(self.following),
            display=dict(self.display),
            app_follower_count=self.app_follower_count,
            export_dir=self.export_dir,
        )

    @classmethod
    def from_export_dir(cls, export_dir: Path) -> ConnectionGraph | None:
        f_entries = _load_follower_entries(export_dir)
        fol_entries = _load_following_entries(export_dir)
        if not f_entries or not fol_entries:
            return None

        fk, fd = _handle_sets_from_entries(f_entries)
        ok, od = _handle_sets_from_entries(fol_entries)
        display = dict(od)
        display.update(fd)

        return cls(
            followers=fk,
            following=ok,
            display=display,
            app_follower_count=_load_app_follower_count(export_dir),
            export_dir=export_dir,
        )
