"""Parse activity-related Instagram export JSON."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from activity.models import LabeledEvent, MonthCount
from activity.paths import (
    COMMENTS,
    LIKED_COMMENTS,
    LIKED_POSTS,
    POSTS,
    REELS,
    SAVED,
    SEARCHES,
    STORIES,
    STORY_LIKES,
    STORY_POLLS,
)
from connections.graph import username_from_connection_entry
from export_inventory import read_json_first


def _month_counts(timestamps: list[int]) -> tuple[MonthCount, ...]:
    by_month = Counter(
        datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m") for t in timestamps
    )
    return tuple(MonthCount(month=m, count=c) for m, c in sorted(by_month.items()))


def parse_posts(data: Any) -> tuple[int, tuple[MonthCount, ...]]:
    if not isinstance(data, list):
        return 0, ()
    stamps: list[int] = []
    for post in data:
        if not isinstance(post, dict):
            continue
        for media in post.get("media") or []:
            if isinstance(media, dict) and "creation_timestamp" in media:
                stamps.append(int(media["creation_timestamp"]))
    return len(stamps), _month_counts(stamps)


def parse_stories(data: Any) -> tuple[int, tuple[MonthCount, ...]]:
    if not isinstance(data, dict):
        return 0, ()
    stories = data.get("ig_stories") or []
    stamps = [
        int(s["creation_timestamp"])
        for s in stories
        if isinstance(s, dict) and "creation_timestamp" in s
    ]
    return len(stories) if isinstance(stories, list) else 0, _month_counts(stamps)


def parse_reels(data: Any) -> tuple[int, tuple[MonthCount, ...]]:
    if data is None:
        return 0, ()
    rows: list[Any]
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = data.get("ig_reels_media") or data.get("ig_reels") or data.get("reels") or []
        if not rows:
            for val in data.values():
                if isinstance(val, list):
                    rows = val
                    break
    else:
        return 0, ()
    stamps: list[int] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if "creation_timestamp" in row:
            stamps.append(int(row["creation_timestamp"]))
            continue
        for media in row.get("media") or []:
            if isinstance(media, dict) and "creation_timestamp" in media:
                stamps.append(int(media["creation_timestamp"]))
    return len(rows), _month_counts(stamps)


def _like_label(entry: dict) -> tuple[str, int | None]:
    label, t_raw = "?", None
    if entry.get("string_list_data"):
        d = entry["string_list_data"][0]
        label = d.get("value") or d.get("href") or "?"
        t_raw = d.get("timestamp")
    else:
        for lv in entry.get("label_values") or []:
            if isinstance(lv, dict) and lv.get("label") == "URL":
                label = lv.get("value") or lv.get("href") or "?"
                break
        t_raw = entry.get("timestamp")
        title = entry.get("title")
        if title:
            label = str(title)
    if isinstance(t_raw, float):
        t_raw = int(t_raw)
    return str(label), t_raw if isinstance(t_raw, int) else None


def parse_liked_posts(data: Any) -> tuple[int, tuple[LabeledEvent, ...]]:
    if isinstance(data, list):
        likes = data
    elif isinstance(data, dict):
        likes = data.get("likes_media_likes") or []
    else:
        return 0, ()
    events: list[LabeledEvent] = []
    for entry in likes:
        if not isinstance(entry, dict):
            continue
        label, ts = _like_label(entry)
        events.append(LabeledEvent(label=label, timestamp=ts))
    return len(events), tuple(events)


def parse_liked_comments(data: Any) -> int:
    if not isinstance(data, dict):
        return 0
    likes = data.get("likes_comment_likes") or []
    return len(likes) if isinstance(likes, list) else 0


def parse_comment_targets(data: Any) -> tuple[tuple[str, int], ...]:
    if not isinstance(data, list):
        return ()
    targets: list[str] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        if entry.get("string_list_data"):
            targets.append(entry["string_list_data"][0].get("value") or "")
            continue
        u = username_from_connection_entry(entry)
        if u:
            targets.append(u)
    return tuple(Counter(t for t in targets if t).most_common(15))


def parse_searches(data: Any) -> tuple[int, tuple[tuple[str, int], ...]]:
    if not isinstance(data, dict):
        return 0, ()
    searches = data.get("searches_user") or []
    terms: list[str] = []
    for s in searches:
        if not isinstance(s, dict):
            continue
        t = (s.get("title") or "").strip()
        if t:
            terms.append(t)
            continue
        for d in (s.get("string_map_data") or {}).values():
            if isinstance(d, dict) and d.get("value"):
                terms.append(str(d["value"]))
        u = username_from_connection_entry(s)
        if u:
            terms.append(u)
    return len(searches) if isinstance(searches, list) else 0, tuple(
        Counter(terms).most_common(20)
    )


def parse_saved(data: Any) -> tuple[int, tuple[LabeledEvent, ...]]:
    rows: list[Any] = []
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = (
            data.get("saved_saved_media")
            or data.get("saved_saved_collections")
            or data.get("label_values")
            or []
        )
        if not rows:
            for val in data.values():
                if isinstance(val, list):
                    rows = val
                    break
    events: list[LabeledEvent] = []
    for entry in rows:
        if not isinstance(entry, dict):
            continue
        title = entry.get("title")
        label, ts = _like_label(entry)
        if title:
            label = str(title)
        events.append(LabeledEvent(label=label, timestamp=ts))
    return len(events), tuple(events)


def _count_list_payload(data: Any, *keys: str) -> int:
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in keys:
            val = data.get(key)
            if isinstance(val, list):
                return len(val)
        for val in data.values():
            if isinstance(val, list):
                return len(val)
    return 0


def load_activity_parts(export_dir) -> dict[str, Any]:
    posts, _ = read_json_first(export_dir, POSTS.relative_paths)
    stories, _ = read_json_first(export_dir, STORIES.relative_paths)
    reels, _ = read_json_first(export_dir, REELS.relative_paths)
    liked, _ = read_json_first(export_dir, LIKED_POSTS.relative_paths)
    liked_c, _ = read_json_first(export_dir, LIKED_COMMENTS.relative_paths)
    comments, _ = read_json_first(export_dir, COMMENTS.relative_paths)
    searches, _ = read_json_first(export_dir, SEARCHES.relative_paths)
    saved, _ = read_json_first(export_dir, SAVED.relative_paths)
    story_likes, _ = read_json_first(export_dir, STORY_LIKES.relative_paths)
    story_polls, _ = read_json_first(export_dir, STORY_POLLS.relative_paths)
    return {
        "posts": posts,
        "stories": stories,
        "reels": reels,
        "liked": liked,
        "liked_c": liked_c,
        "comments": comments,
        "searches": searches,
        "saved": saved,
        "story_likes": story_likes,
        "story_polls": story_polls,
    }
