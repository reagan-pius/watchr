"""Parse ads-related Instagram export JSON into domain models."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from ads.models import (
    AdEvent,
    AdPreferencesSummary,
    Advertiser,
    AudienceFlagCounts,
    EngagementSummary,
    OffIgApp,
)
from ads.paths import (
    AD_PREFERENCES,
    ADS_CLICKED,
    ADS_INTERESTS,
    ADS_VIEWED,
    ADVERTISERS,
    CATEGORIES_USED,
    OFF_INSTAGRAM,
)
from export_inventory import read_json_first


def _truthy_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def parse_advertisers(data: Any) -> list[Advertiser]:
    if not isinstance(data, dict):
        return []
    rows = data.get("ig_custom_audiences_all_types") or []
    out: list[Advertiser] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = (row.get("advertiser_name") or row.get("name") or "?").strip() or "?"
        out.append(
            Advertiser(
                name=name,
                data_file=_truthy_flag(row.get("has_data_file_custom_audience")),
                remarketing=_truthy_flag(row.get("has_remarketing_custom_audience")),
                in_person_store=_truthy_flag(row.get("has_in_person_store_visit")),
            )
        )
    return out


def flag_counts_for(advertisers: list[Advertiser]) -> AudienceFlagCounts:
    return AudienceFlagCounts(
        total=len(advertisers),
        data_file=sum(1 for a in advertisers if a.data_file),
        remarketing=sum(1 for a in advertisers if a.remarketing),
        in_person_store=sum(1 for a in advertisers if a.in_person_store),
    )


def parse_interests(data: Any) -> list[str]:
    if not isinstance(data, dict):
        return []
    interests: list[str] = []
    for row in data.get("inferred_data_ig_interest") or []:
        if not isinstance(row, dict):
            continue
        smd = row.get("string_map_data") or {}
        interest = (smd.get("Interest") or {}).get("value")
        if interest:
            interests.append(str(interest))
    return interests


def parse_categories(data: Any) -> list[str]:
    if not isinstance(data, dict):
        return []
    categories: list[str] = []
    for lv in data.get("label_values") or []:
        if not isinstance(lv, dict) or lv.get("label") != "Name":
            continue
        for item in lv.get("vec") or []:
            if isinstance(item, dict) and item.get("value"):
                categories.append(str(item["value"]))
    return categories


def _event_from_entry(entry: Any) -> AdEvent | None:
    if not isinstance(entry, dict):
        return None
    smd = entry.get("string_map_data") or {}
    author = (
        (smd.get("Author") or {}).get("value")
        or (smd.get("Advertiser") or {}).get("value")
        or (smd.get("Title") or {}).get("value")
        or entry.get("title")
        or "?"
    )
    time_node = smd.get("Time") or smd.get("Timestamp") or {}
    ts = time_node.get("timestamp")
    if ts is None and isinstance(entry.get("timestamp"), (int, float)):
        ts = int(entry["timestamp"])
    if isinstance(ts, float):
        ts = int(ts)
    return AdEvent(author=str(author).strip() or "?", timestamp=ts if isinstance(ts, int) else None)


def _extract_ad_events(data: Any) -> list[AdEvent]:
    if data is None:
        return []
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = (
            data.get("impressions_history_ads_seen")
            or data.get("impressions_history_ads_clicked")
            or data.get("ads_viewed")
            or data.get("ads_clicked")
            or data.get("label_values")  # unlikely but avoid crash
            or []
        )
        if not rows and len(data) == 1:
            only = next(iter(data.values()))
            if isinstance(only, list):
                rows = only
    else:
        return []
    events: list[AdEvent] = []
    for entry in rows:
        ev = _event_from_entry(entry)
        if ev:
            events.append(ev)
    return events


def _month_span(events: list[AdEvent]) -> tuple[str, str] | None:
    stamps = [e.timestamp for e in events if e.timestamp]
    if not stamps:
        return None
    lo = datetime.fromtimestamp(min(stamps), tz=timezone.utc).strftime("%Y-%m")
    hi = datetime.fromtimestamp(max(stamps), tz=timezone.utc).strftime("%Y-%m")
    return lo, hi


def _top_authors(events: list[AdEvent], limit: int = 15) -> tuple[tuple[str, int], ...]:
    counts = Counter(e.author for e in events if e.author and e.author != "?")
    return tuple(counts.most_common(limit))


def build_engagement(viewed_data: Any, clicked_data: Any) -> EngagementSummary:
    viewed = _extract_ad_events(viewed_data)
    clicked = _extract_ad_events(clicked_data)
    return EngagementSummary(
        viewed_count=len(viewed),
        clicked_count=len(clicked),
        viewed_span=_month_span(viewed),
        clicked_span=_month_span(clicked),
        top_viewed=_top_authors(viewed),
        top_clicked=_top_authors(clicked),
    )


def parse_off_instagram(data: Any) -> list[OffIgApp]:
    if data is None:
        return []
    rows: list[Any]
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = (
            data.get("off_instagram_activity_v2")
            or data.get("off_facebook_activity_v2")
            or data.get("your_off_meta_activity_v2")
            or []
        )
        if not rows:
            for key, val in data.items():
                if isinstance(val, list) and key.lower().endswith("activity_v2"):
                    rows = val
                    break
    else:
        return []
    apps: list[OffIgApp] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = (row.get("name") or row.get("title") or "?").strip() or "?"
        events = row.get("events") or row.get("event_list") or []
        count = len(events) if isinstance(events, list) else 0
        apps.append(OffIgApp(name=name, event_count=count))
    return apps


def _collect_string_list(node: Any) -> list[str]:
    out: list[str] = []
    if isinstance(node, list):
        for item in node:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
            elif isinstance(item, dict):
                val = (
                    item.get("value")
                    or (item.get("string_map_data") or {}).get("Name", {}).get("value")
                    or (item.get("string_map_data") or {}).get("Interest", {}).get("value")
                )
                if val:
                    out.append(str(val).strip())
    return out


def parse_ad_preferences(data: Any) -> AdPreferencesSummary | None:
    """Best-effort preferences summary; returns None if nothing recognizable."""
    if not isinstance(data, dict):
        return AdPreferencesSummary(note="present but unrecognized structure")

    added: list[str] = []
    removed: list[str] = []

    # Common shapes: topics_your_are_interested_in / topics_you_don't_want_to_see
    for key, target in (
        ("topics_your_are_interested_in", added),
        ("topics_you_are_interested_in", added),
        ("topics_you_added", added),
        ("ads_interests", added),
        ("topics_you_don't_want_to_see", removed),
        ("topics_you_dont_want_to_see", removed),
        ("topics_you_removed", removed),
    ):
        if key in data:
            target.extend(_collect_string_list(data[key]))

    # label_values style
    for lv in data.get("label_values") or []:
        if not isinstance(lv, dict):
            continue
        label = (lv.get("label") or "").lower()
        values = _collect_string_list(lv.get("vec") or lv.get("value") or [])
        if "not" in label or "don't" in label or "removed" in label:
            removed.extend(values)
        elif values:
            added.extend(values)

    if not added and not removed:
        # Still present — note so inventory consumers know we saw the file
        return AdPreferencesSummary(note="present but no topic lists found")
    return AdPreferencesSummary(
        topics_added=tuple(dict.fromkeys(added)),
        topics_removed=tuple(dict.fromkeys(removed)),
    )


def load_advertisers(export_dir) -> list[Advertiser]:
    data, _ = read_json_first(export_dir, ADVERTISERS.relative_paths)
    return parse_advertisers(data)


def load_interests(export_dir) -> list[str]:
    data, _ = read_json_first(export_dir, ADS_INTERESTS.relative_paths)
    return parse_interests(data)


def load_categories(export_dir) -> list[str]:
    data, _ = read_json_first(export_dir, CATEGORIES_USED.relative_paths)
    return parse_categories(data)


def load_engagement(export_dir) -> EngagementSummary:
    viewed, _ = read_json_first(export_dir, ADS_VIEWED.relative_paths)
    clicked, _ = read_json_first(export_dir, ADS_CLICKED.relative_paths)
    if viewed is None and clicked is None:
        return EngagementSummary()
    return build_engagement(viewed, clicked)


def load_off_instagram(export_dir) -> list[OffIgApp]:
    data, _ = read_json_first(export_dir, OFF_INSTAGRAM.relative_paths)
    return parse_off_instagram(data)


def load_preferences(export_dir) -> AdPreferencesSummary | None:
    data, rel = read_json_first(export_dir, AD_PREFERENCES.relative_paths)
    if rel is None:
        return None
    return parse_ad_preferences(data)
