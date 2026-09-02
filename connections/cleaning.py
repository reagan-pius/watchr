"""
Data cleaning / curation for connection sets.
=============================================

Instagram's data download reliably includes the full *following* list, but for
many accounts the *followers* list arrives truncated (sometimes only a small
fraction of the real total). The raw "following − followers" computation is
therefore polluted with false positives: genuine mutuals that are simply
missing from the export's follower files.

This module cleans the raw sets using every signal available inside the export:

1.  **Pending follow requests** (`recent_follow_requests.json`) — accounts the
    user has requested but who have not accepted yet. They show up in
    `following.json` but cannot follow back by definition, so they are
    reclassified instead of counted as "not following back".
2.  **Restricted profiles** (`restricted_profiles.json`) — reclassified, since
    the relationship is deliberately muted.
3.  **Recently unfollowed profiles** (`recently_unfollowed_profiles.json`) —
    dropped if they linger in the following list.
4.  **Manual curation** (`curated_followers.txt`) — handles the user has
    visually confirmed in the app to be followers. This is the only reliable
    signal when the export's follower list is incomplete: every confirmed
    handle is removed from the "don't follow back" list.

What remains is the *unverified* remainder: people the export says don't follow
back, where that claim could not be checked against any other file. When
follower coverage is low, that remainder is expected to contain mostly false
positives — see docs/data-cleaning.md for the full workflow.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from connections.curation_store import (  # noqa: F401 — re-exported per ADR-0002
    CURATED_FILE_NAME,
    CURATED_NONFOLLOWERS_FILE_NAME,
    CURATION_META_FILE_NAME,
    CurationSnapshot,
    read_handle_file,
    write_curated_file,
)
from connections.graph import ConnectionGraph, _entries_from_relationship_file, _norm_handle


def _read_json_file(full: Path):
    if not full.is_file():
        return None
    with open(full, encoding="utf-8") as f:
        return json.load(f)


def _entries_for_cleaning(data):
    """Like graph._entries_from_relationship_file, plus relationships_unfollowed_users."""
    entries = _entries_from_relationship_file(data)
    if not entries and isinstance(data, dict):
        value = data.get("relationships_unfollowed_users")
        if isinstance(value, list):
            return value
    return entries


def _handles_from_relationship_file(export_dir: Path, relative: str) -> set[str]:
    """Casefolded handles from any relationships_* style file (missing file → empty)."""
    data = _read_json_file(export_dir / relative)
    if data is None:
        return set()
    handles: set[str] = set()
    for entry in _entries_for_cleaning(data):
        if not isinstance(entry, dict):
            continue
        sld = entry.get("string_list_data") or []
        if sld and isinstance(sld[0], dict):
            v = sld[0].get("value")
            if v:
                handles.add(_norm_handle(str(v)))
                continue
            title = (entry.get("title") or "").strip()
            if title:
                handles.add(_norm_handle(title))
    return handles


def load_pending_requests(export_dir: Path) -> set[str]:
    """Outgoing follow requests that have not been accepted."""
    return _handles_from_relationship_file(
        export_dir, "connections/followers_and_following/recent_follow_requests.json"
    )


def load_restricted(export_dir: Path) -> set[str]:
    """Accounts the user has restricted."""
    return _handles_from_relationship_file(
        export_dir, "connections/followers_and_following/restricted_profiles.json"
    )


def load_recently_unfollowed(export_dir: Path) -> set[str]:
    """Accounts the user unfollowed (should no longer be in the following list)."""
    return _handles_from_relationship_file(
        export_dir, "connections/followers_and_following/recently_unfollowed_profiles.json"
    )


def load_curated_followers(export_dir: Path, extra_path: Path | None = None) -> set[str]:
    """Handles the user manually confirmed follow them back.

    Reads ``curated_followers.txt`` from the export folder and (if different)
    from ``extra_path`` (e.g. the project root). One handle per line; ``#``
    starts a comment, blank lines are ignored. Matching is case-insensitive.
    """
    paths = [export_dir / CURATED_FILE_NAME]
    if extra_path is not None and extra_path != export_dir / CURATED_FILE_NAME:
        paths.append(extra_path)
    return read_handle_file(paths)


def load_curated_nonfollowers(export_dir: Path, extra_path: Path | None = None) -> set[str]:
    """Handles the user marked as NOT following them back (curation sessions).

    Same file format as ``curated_followers.txt``; used so the wizard never
    re-asks accounts the user has already classified.
    """
    paths = [export_dir / CURATED_NONFOLLOWERS_FILE_NAME]
    if extra_path is not None and extra_path != export_dir / CURATED_NONFOLLOWERS_FILE_NAME:
        paths.append(extra_path)
    return read_handle_file(paths)


def load_curation_meta(search_dirs) -> dict:
    """In-app reference figures saved by the curation session.

    Looks for ``curation_meta.json`` (keys: ``app_followers``,
    ``app_following``) in each directory given. First readable file wins.
    Missing or malformed file → {}.
    """
    for directory in search_dirs:
        if not directory:
            continue
        path = Path(directory) / CURATION_META_FILE_NAME
        if not path.is_file():
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            return data
    return {}


def write_curation_meta(path: Path, app_followers: int | None, app_following: int | None) -> Path:
    """Persist the in-app reference figures from a curation session."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "app_followers": app_followers,
        "app_following": app_following,
        "note": "Totals as shown in the Instagram app when the curation session ran.",
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


@dataclass
class CleaningResult:
    """Raw vs cleaned "don't follow back" sets, with per-bucket provenance."""

    raw_not_following_back: set[str] = field(default_factory=set)
    pending_requests: set[str] = field(default_factory=set)
    restricted: set[str] = field(default_factory=set)
    recently_unfollowed: set[str] = field(default_factory=set)
    curated_confirmed: set[str] = field(default_factory=set)
    curated_denied: set[str] = field(default_factory=set)
    unverified: set[str] = field(default_factory=set)
    display: dict[str, str] = field(default_factory=dict)

    @property
    def cleaned_not_following_back(self) -> set[str]:
        """The curated 👻 list: unverified remainder + accounts the user
        confirmed do NOT follow back (denied handles stay listed)."""
        return self.unverified | self.curated_denied

    def show(self, key: str) -> str:
        return self.display.get(key, key)


def clean_connection_sets(
    graph: ConnectionGraph,
    extra_curated_path: Path | None = None,
    snapshot: CurationSnapshot | None = None,
) -> CleaningResult:
    """Apply every cleaning step to the raw graph's not-following-back set.

    ``snapshot`` (from a CurationStore) supplies the curated confirmed/denied
    sets; when it's None the curated files are loaded from the export dir and
    ``extra_curated_path`` (backwards-compatible fallback).
    """
    export_dir = graph.export_dir
    if export_dir is None:
        raw = set(graph.not_following_back)
        return CleaningResult(
            raw_not_following_back=raw,
            unverified=set(raw),
            display=dict(graph.display),
        )

    pending_all = load_pending_requests(export_dir)
    restricted_all = load_restricted(export_dir)
    unfollowed_all = load_recently_unfollowed(export_dir)
    if snapshot is not None:
        curated_all = set(snapshot.confirmed)
        denied_all = set(snapshot.denied)
    else:
        curated_all = load_curated_followers(export_dir, extra_curated_path)
        denied_all = load_curated_nonfollowers(export_dir)

    raw = set(graph.not_following_back)
    pending = raw & pending_all
    restricted = raw & restricted_all
    unfollowed = raw & unfollowed_all
    curated = raw & curated_all
    denied = raw & denied_all
    unverified = raw - pending - restricted - unfollowed - curated - denied

    return CleaningResult(
        raw_not_following_back=raw,
        pending_requests=pending,
        restricted=restricted,
        recently_unfollowed=unfollowed,
        curated_confirmed=curated,
        curated_denied=denied,
        unverified=unverified,
        display=dict(graph.display),
    )


def promotion_set(result: CleaningResult, assume_remainder: bool = False) -> set[str]:
    """Handles to promote into the followers set (and therefore Mutuals).

    By default only manually confirmed handles are promoted. With
    ``assume_remainder=True`` the whole unverified remainder is promoted too —
    an explicit policy for users who know they follow everyone back; see
    docs/data-cleaning.md.
    """
    promoted = set(result.curated_confirmed)
    if assume_remainder:
        promoted |= result.unverified
    return promoted


def write_curate_template(result: CleaningResult, path: Path) -> Path:
    """Write a commented checklist of unverified handles for in-app verification.

    Every handle is written commented out, so nothing is treated as confirmed
    until the user deletes the leading ``#`` after checking the account in the
    app. Refuses to overwrite an existing file (``FileExistsError``).
    """
    if path.exists():
        raise FileExistsError(path)
    lines = [
        "# curated_followers.txt — verification checklist (generated by --bootstrap-curated)",
        "#",
        "# The follower export is incomplete, so each handle below was reported as",
        "# 'not following back' but may actually be a mutual. For each one, open",
        "# their profile in the Instagram app → Following → search your handle:",
        "#   - they follow you  → delete the leading '# ' to confirm (they will be",
        "#                        moved into Mutuals on the next run)",
        "#   - they don't       → leave the line commented out",
        "",
    ]
    lines.extend(f"# {handle}" for handle in sorted(result.unverified))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
