"""Render AdsInsights as terminal report lines."""

from __future__ import annotations

from ads.insights import AdsInsights
from export_inventory import FileStatus, format_inventory_lines


def _cap(limit: int, total: int) -> int:
    """Return how many items to show. limit 0 = unlimited."""
    if limit <= 0:
        return total
    return min(limit, total)


def format_inventory(ins: AdsInsights) -> list[str]:
    lines = ["", "📋  Export inventory (ads & tracking):"]
    lines.extend(format_inventory_lines(ins.inventory))
    missing = [i.label for i in ins.inventory if i.status == FileStatus.MISSING]
    if missing:
        lines.append(
            "   Note: missing files were omitted from this ZIP — re-request those "
            "categories in Accounts Centre if you need them."
        )
    return lines


def format_advertisers(ins: AdsInsights, *, limit: int = 30) -> list[str]:
    if not ins.advertisers:
        return []
    fc = ins.flag_counts
    lines = [
        "",
        f"📢  Advertisers who have uploaded your data ({fc.total}):",
        "   Audience types:",
        f"      data-file custom audience     {fc.data_file}",
        f"      remarketing                   {fc.remarketing}",
        f"      in-person store visit         {fc.in_person_store}",
    ]
    show_n = _cap(limit, len(ins.advertisers))
    if show_n:
        lines.append(f"   Sample ({show_n} of {fc.total}):")
        for adv in ins.advertisers[:show_n]:
            flags = ", ".join(adv.flag_labels())
            lines.append(f"      • {adv.name}  [{flags}]")
    if show_n < fc.total:
        lines.append(
            f"   ... and {fc.total - show_n} more "
            "(use --ads-limit 0 to print all, or --output FILE)"
        )
    return lines


def format_interests_and_categories(ins: AdsInsights, *, limit: int = 30) -> list[str]:
    lines: list[str] = []
    if ins.interests:
        show_n = _cap(limit, len(ins.interests))
        lines.append("")
        lines.append(f"🎯  Instagram thinks you're interested in ({len(ins.interests)} topics):")
        for topic in ins.interests[:show_n]:
            lines.append(f"   • {topic}")
        if show_n < len(ins.interests):
            lines.append(f"   ... and {len(ins.interests) - show_n} more")
    if ins.categories:
        show_n = _cap(limit, len(ins.categories))
        lines.append("")
        lines.append(f"🏷️   Categories Meta uses to reach you ({len(ins.categories)}):")
        for cat in ins.categories[:show_n]:
            lines.append(f"   • {cat}")
        if show_n < len(ins.categories):
            lines.append(f"   ... and {len(ins.categories) - show_n} more")
    return lines


def format_engagement(ins: AdsInsights, *, limit: int = 15) -> list[str]:
    eng = ins.engagement
    if eng.viewed_count == 0 and eng.clicked_count == 0:
        return []
    lines = ["", "👁  Ads engagement:"]
    viewed_span = (
        f"{eng.viewed_span[0]} → {eng.viewed_span[1]}" if eng.viewed_span else "n/a"
    )
    clicked_span = (
        f"{eng.clicked_span[0]} → {eng.clicked_span[1]}" if eng.clicked_span else "n/a"
    )
    lines.append(
        f"   Viewed: {eng.viewed_count}  |  Clicked: {eng.clicked_count}"
    )
    if eng.viewed_count:
        lines.append(f"   Viewed span:  {viewed_span}")
    if eng.clicked_count:
        lines.append(f"   Clicked span: {clicked_span}")

    top_n = limit if limit > 0 else 15
    if eng.top_viewed:
        lines.append(f"   Top advertisers by views:")
        for author, count in eng.top_viewed[:top_n]:
            lines.append(f"      {count:>4}x  {author}")
    if eng.top_clicked:
        lines.append(f"   Top advertisers by clicks:")
        for author, count in eng.top_clicked[:top_n]:
            lines.append(f"      {count:>4}x  {author}")
    return lines


def format_preferences(ins: AdsInsights, *, limit: int = 30) -> list[str]:
    prefs = ins.preferences
    if prefs is None:
        return []
    lines = ["", "⚙️   Ad preferences:"]
    if prefs.note and not prefs.topics_added and not prefs.topics_removed:
        lines.append(f"   {prefs.note}")
        return lines
    if prefs.topics_added:
        show_n = _cap(limit, len(prefs.topics_added))
        lines.append(f"   Topics you're interested in ({len(prefs.topics_added)}):")
        for t in prefs.topics_added[:show_n]:
            lines.append(f"      • {t}")
        if show_n < len(prefs.topics_added):
            lines.append(f"      ... and {len(prefs.topics_added) - show_n} more")
    if prefs.topics_removed:
        show_n = _cap(limit, len(prefs.topics_removed))
        lines.append(f"   Topics you don't want to see ({len(prefs.topics_removed)}):")
        for t in prefs.topics_removed[:show_n]:
            lines.append(f"      • {t}")
        if show_n < len(prefs.topics_removed):
            lines.append(f"      ... and {len(prefs.topics_removed) - show_n} more")
    if prefs.note:
        lines.append(f"   ({prefs.note})")
    return lines


def format_off_instagram(ins: AdsInsights, *, limit: int = 20) -> list[str]:
    if not ins.off_ig_apps:
        return []
    lines = [
        "",
        f"🌐  Apps/sites that sent your activity to Meta ({len(ins.off_ig_apps)}):",
    ]
    show_n = _cap(limit, len(ins.off_ig_apps))
    for app in ins.off_ig_apps[:show_n]:
        lines.append(f"   • {app.name}  ({app.event_count} events)")
    if show_n < len(ins.off_ig_apps):
        lines.append(f"   ... and {len(ins.off_ig_apps) - show_n} more")
    return lines


def format_ads_report(ins: AdsInsights, *, limit: int = 30) -> str:
    """Full ads section body (no section banner)."""
    chunks: list[str] = []
    chunks.extend(format_inventory(ins))
    chunks.extend(format_advertisers(ins, limit=limit))
    chunks.extend(format_interests_and_categories(ins, limit=limit))
    chunks.extend(format_engagement(ins, limit=min(limit, 15) if limit > 0 else 15))
    chunks.extend(format_preferences(ins, limit=limit))
    chunks.extend(format_off_instagram(ins, limit=min(limit, 20) if limit > 0 else 20))
    if not any(
        [
            ins.advertisers,
            ins.interests,
            ins.categories,
            ins.engagement.viewed_count,
            ins.engagement.clicked_count,
            ins.off_ig_apps,
            ins.preferences is not None,
        ]
    ):
        chunks.append("")
        chunks.append(
            "   No ads/tracking detail files found in this export. "
            "Enable Ads categories when requesting a download."
        )
    return "\n".join(chunks).rstrip() + "\n"


def print_ads_report(ins: AdsInsights, *, limit: int = 30) -> None:
    print(format_ads_report(ins, limit=limit), end="")
