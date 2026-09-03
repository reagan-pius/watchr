"""
Watchr — Instagram Data Export Analyser
========================================
Your unofficial watcher for Instagram exports.

Parse an unzipped Instagram data export (JSON) and print readable reports
about followers, activity, security and ad/tracking — fully offline.

The export folder is resolved in this order:
  1. --export-dir CLI flag (or --zip)
  2. $INSTAGRAM_EXPORT_DIR environment variable
  3. Auto-detect: the instagram-* folder next to this script

Personal details (email, phone number, date of birth, login IPs) are
redacted by default — pass --no-redact to print raw values.

Each report function is standalone — call whichever ones you want.
"""

import argparse
import json
import os
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path
from datetime import datetime, timezone

from activity.insights import ActivityInsights
from activity.report import print_activity_report
from ads.insights import AdsInsights
from ads.report import print_ads_report
from apps.insights import AppsInsights
from apps.report import print_apps_report
from connections.graph import ConnectionGraph, username_from_connection_entry
from connections.cleaning import CURATED_FILE_NAME
from connections.curation_store import migrate_legacy_curation
from connections.insights import ConnectionsInsights
from contacts.insights import ContactsInsights
from contacts.report import print_contacts_report
from context import AnalyzerContext
from curate_session import run_curation_session
from export_paths import resolve_export_dir
from messages.insights import MessagesInsights
from messages.report import print_messages_report
from preferences.insights import PreferencesInsights
from preferences.report import print_preferences_report
from security.insights import SecurityInsights
from security.report import print_security_report
from setup_check import run_setup_check
from shopping.insights import ShoppingInsights
from shopping.report import print_shopping_report

# ─── REDACTION ────────────────────────────────────────────────────────────────
# Personal details are masked by default so output can be pasted or shared
# safely. Disable with --no-redact (or AnalyzerContext(redact=False)).


def _mask_email(v: str) -> str:
    if "@" not in v:
        return "***"
    local, _, domain = v.partition("@")
    return f"{local[:1]}***@{domain}"


def _mask_phone(v: str) -> str:
    digits = re.sub(r"\D", "", v)
    return f"+{'*' * max(len(digits) - 3, 3)}{digits[-3:]}" if digits else "***"


def _mask_dob(v: str) -> str:
    return f"{v[:4]}-**-**" if len(v) >= 4 else "****"


def _mask_ip(v: str) -> str:
    parts = v.split(".")
    return ".".join([*parts[:2], "***", "***"]) if len(parts) == 4 else "***"


_PROFILE_MASKS = {
    "Email address": _mask_email,
    "Phone number": _mask_phone,
    "Date of birth": _mask_dob,
}


def redact_path(path: str, redact: bool = True) -> str:
    """Mask the username inside export folder names like instagram-<user>-2026-04-02-AbCdEf,
    and shorten the home directory to ~."""
    if redact:
        path = path.replace(str(Path.home()), "~", 1)
        path = re.sub(r"(instagram-)[^/\s]+?(-\d{4}-\d{2}-\d{2}-\w+)", r"\1***\2", path)
    return path
# ──────────────────────────────────────────────────────────────────────────────

def load(base_dir: Path, relative_path: str, quiet: bool = False):
    """Load a JSON file relative to base_dir.

    With ``quiet=True`` the missing-file message is suppressed (so callers
    never invoke load purely for its print side effect — ADR-0005).
    """
    full = base_dir / relative_path
    if not full.exists():
        if not quiet:
            print(f"  [!] File not found: {full}")
        return None
    with open(full, encoding="utf-8") as f:
        return json.load(f)


def load_first(base_dir: Path, relative_paths: list[str], quiet: bool = False) -> dict | list | None:
    """Try several export paths (Meta renames/moves files between export versions)."""
    for rel in relative_paths:
        full = base_dir / rel
        if full.is_file():
            with open(full, encoding="utf-8") as f:
                return json.load(f)
    if not quiet:
        print("  [!] None of these files exist under your export folder:")
        for rel in relative_paths:
            print(f"      • {base_dir / rel}")
    return None


def load_first_optional(base_dir: Path, relative_paths: list[str]) -> dict | list | None:
    """Like load_first, but no message if nothing exists (Meta often omits these)."""
    for rel in relative_paths:
        full = base_dir / rel
        if full.is_file():
            with open(full, encoding="utf-8") as f:
                return json.load(f)
    return None


def _read_json_file(full: Path):
    if not full.is_file():
        return None
    with open(full, encoding="utf-8") as f:
        return json.load(f)


def ts(unix: int) -> str:
    return datetime.fromtimestamp(unix, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


_connections_cache: dict[AnalyzerContext, ConnectionsInsights | None] = {}
_ads_cache: dict[AnalyzerContext, AdsInsights] = {}
_activity_cache: dict[AnalyzerContext, ActivityInsights] = {}
_security_cache: dict[AnalyzerContext, SecurityInsights] = {}
_messages_cache: dict[AnalyzerContext, MessagesInsights] = {}
_apps_cache: dict[AnalyzerContext, AppsInsights] = {}
_contacts_cache: dict[AnalyzerContext, ContactsInsights] = {}
_shopping_cache: dict[AnalyzerContext, ShoppingInsights] = {}
_preferences_cache: dict[AnalyzerContext, PreferencesInsights] = {}
FOLLOWER_SNAPSHOT_FILE_NAME = "followers_snapshot.json"


def _connections(ctx: AnalyzerContext) -> ConnectionsInsights | None:
    """Compute-once ConnectionsInsights for a run (ADR-0003)."""
    if ctx in _connections_cache:
        return _connections_cache[ctx]
    graph = ConnectionGraph.from_export_dir(ctx.base_dir)
    if not graph:
        print(f"  [!] Could not build a connection graph from {ctx.base_dir}")
        _connections_cache[ctx] = None
        return None
    snapshot = ctx.curation_store().load()
    insights = ConnectionsInsights.build(
        graph, snapshot, assume_mutual=ctx.assume_mutual
    )
    _connections_cache[ctx] = insights
    return insights


def _ads(ctx: AnalyzerContext) -> AdsInsights:
    """Compute-once AdsInsights for a run (ADR-0007)."""
    if ctx in _ads_cache:
        return _ads_cache[ctx]
    insights = AdsInsights.build(ctx.base_dir)
    _ads_cache[ctx] = insights
    return insights


def _activity(ctx: AnalyzerContext) -> ActivityInsights:
    if ctx in _activity_cache:
        return _activity_cache[ctx]
    insights = ActivityInsights.build(ctx.base_dir)
    _activity_cache[ctx] = insights
    return insights


def _security(ctx: AnalyzerContext) -> SecurityInsights:
    if ctx in _security_cache:
        return _security_cache[ctx]
    insights = SecurityInsights.build(ctx.base_dir)
    _security_cache[ctx] = insights
    return insights


def _messages(ctx: AnalyzerContext) -> MessagesInsights:
    if ctx in _messages_cache:
        return _messages_cache[ctx]
    insights = MessagesInsights.build(ctx.base_dir)
    _messages_cache[ctx] = insights
    return insights


def _apps(ctx: AnalyzerContext) -> AppsInsights:
    if ctx in _apps_cache:
        return _apps_cache[ctx]
    insights = AppsInsights.build(ctx.base_dir)
    _apps_cache[ctx] = insights
    return insights


def _contacts(ctx: AnalyzerContext) -> ContactsInsights:
    if ctx in _contacts_cache:
        return _contacts_cache[ctx]
    insights = ContactsInsights.build(ctx.base_dir)
    _contacts_cache[ctx] = insights
    return insights


def _shopping(ctx: AnalyzerContext) -> ShoppingInsights:
    if ctx in _shopping_cache:
        return _shopping_cache[ctx]
    insights = ShoppingInsights.build(ctx.base_dir)
    _shopping_cache[ctx] = insights
    return insights


def _preferences(ctx: AnalyzerContext) -> PreferencesInsights:
    if ctx in _preferences_cache:
        return _preferences_cache[ctx]
    insights = PreferencesInsights.build(ctx.base_dir)
    _preferences_cache[ctx] = insights
    return insights


def _count_label(count: int, graph: ConnectionGraph) -> str:
    if graph.followers_incomplete:
        return f"{count}, {graph.export_only_label}"
    return str(count)


def _follower_snapshot_path(ctx: AnalyzerContext) -> Path:
    return ctx.curation_store().root / FOLLOWER_SNAPSHOT_FILE_NAME


def _load_follower_snapshot(path: Path) -> set[str] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    raw = payload.get("followers") if isinstance(payload, dict) else None
    if not isinstance(raw, list):
        return None
    return {str(handle).strip().casefold() for handle in raw if str(handle).strip()}


def _save_follower_snapshot(path: Path, followers: set[str]) -> None:
    payload = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "followers": sorted(followers),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _print_follower_delta(ctx: AnalyzerContext, graph: ConnectionGraph) -> None:
    """Show who followed/unfollowed since the previous run for this export root."""
    if "tests" in ctx.base_dir.parts:
        return
    snapshot_path = _follower_snapshot_path(ctx)
    previous = _load_follower_snapshot(snapshot_path)
    current = set(graph.followers)

    print("\n🔁  Since last run (followers):")
    if previous is None:
        print("   No previous snapshot yet — saved this run as baseline.")
    else:
        followed = current - previous
        unfollowed = previous - current
        print(f"   Followed you since last run  {len(followed)}")
        for handle in sorted(followed):
            print(f"   + {graph.show(handle)}")
        print(f"   Unfollowed since last run    {len(unfollowed)}")
        for handle in sorted(unfollowed):
            print(f"   - {handle}")
    try:
        _save_follower_snapshot(snapshot_path, current)
    except OSError as exc:
        print(f"  [!] Could not persist follower snapshot: {exc}", file=sys.stderr)


# ══════════════════════════════════════════════════════════════════════════════
# 1. CONNECTIONS  ──  followers / following / blocked / restricted
# ══════════════════════════════════════════════════════════════════════════════

def connection_summary(ctx: AnalyzerContext) -> None:
    """Export totals vs app-reported followers (when insights are in the ZIP)."""
    ins = _connections(ctx)
    if not ins:
        return
    graph = ins.graph

    print("\n📊  Connection summary:")
    print(f"   Followers in export       {len(graph.followers)}")
    if graph.app_follower_count is not None:
        suffix = "  ⚠ export incomplete" if graph.followers_incomplete else ""
        print(f"   Followers (app insights)  {graph.app_follower_count}{suffix}")
        if graph.follower_completeness is not None:
            pct = graph.follower_completeness * 100
            print(f"   Export coverage           {pct:.0f}% of app-reported followers")
    print(f"   Following in export       {len(graph.following)}")
    mutual_note = graph.export_only_label or "from export"
    print(f"   Mutuals ({mutual_note})     {len(graph.mutuals)}")
    _print_follower_delta(ctx, graph)

    if ins.promoted:
        kind = "confirmed + assumed (--assume-mutual)" if ctx.assume_mutual else "confirmed via curation"
        print(
            f"   Mutuals incl. curation    {len(ins.effective.mutuals)}"
            f"  (+{len(ins.promoted)} {kind})"
        )
    _print_app_derived_reconciliation(ins)
    if graph.followers_incomplete:
        print(
            "\n   ⚠  Follower-side lists below are partial — Instagram often omits most\n"
            "      followers from the download. Compare totals above before trusting\n"
            "      mutual / follower counts against the app."
        )


def _print_app_derived_reconciliation(ins: ConnectionsInsights) -> None:
    """Derive one-way follow counts from in-app totals vs curated mutuals.

    With trustworthy mutuals M, in-app followers F and following G:
      people you follow who don't follow back  = G − M
      people who follow you but you don't follow back = F − M
    The export cannot name these accounts — it only yields the counts.
    """
    derived = ins.derived
    if derived is None or not derived.available:
        return
    print(
        f"\n   📐  App-derived counts ({derived.source}: {derived.app_followers} followers / "
        f"{derived.app_following} following vs {derived.curated_mutuals} mutuals):"
    )
    if derived.you_follow_dont_follow_back is not None:
        print(
            f"      You follow → don't follow back:        "
            f"{derived.app_following} − {derived.curated_mutuals} = "
            f"{derived.you_follow_dont_follow_back}"
        )
    if derived.they_follow_you_not_back is not None:
        print(
            f"      They follow you → you don't follow back: "
            f"{derived.app_followers} − {derived.curated_mutuals} = "
            f"{derived.they_follow_you_not_back}"
        )
    if ins.promoted or derived.source == "curation session":
        print(
            "      (Counts only — the export cannot say WHICH accounts; verify in-app\n"
            "       or with --curate to name them.)"
        )


def who_doesnt_follow_back(ctx: AnalyzerContext) -> set[str]:
    """People you follow who don't follow you back — cleaned & categorized.

    The raw export claim (following − followers) is unreliable because the
    follower files are often incomplete, and because pending follow requests
    appear in the following list without being able to follow back. The list
    is therefore reclassified with every signal in the export; see
    docs/data-cleaning.md. Handles you have visually confirmed in the app can
    be listed in curated_followers.txt to remove them from the report.
    """
    ins = _connections(ctx)
    if not ins:
        return set()
    result = ins.cleaning
    graph = ins.graph

    print("\n🧹  Data cleaning (don't-follow-back list):")
    print(f"   Raw export claim          {len(result.raw_not_following_back)}")
    if result.pending_requests:
        print(f"   Pending follow requests   −{len(result.pending_requests)}")
    if result.restricted:
        print(f"   Restricted profiles       −{len(result.restricted)}")
    if result.recently_unfollowed:
        print(f"   Recently unfollowed       −{len(result.recently_unfollowed)}")
    if result.curated_confirmed:
        print(f"   Manually confirmed        −{len(result.curated_confirmed)}")
    if result.curated_denied:
        print(
            f"   Marked doesn't-follow-back {len(result.curated_denied)}"
            " (kept in the 👻 list)"
        )
    print(f"   Unverified remainder      {len(result.unverified)}")
    if ctx.assume_mutual and result.unverified:
        print(
            f"   Policy --assume-mutual: {len(result.unverified)} unverified accounts were\n"
            "      moved into the Mutuals section — you asserted they all follow back."
        )
    if graph.followers_incomplete:
        print(
            "   ⚠  Follower export is incomplete, so the remainder likely contains\n"
            "      mutuals missing from the follower files. Verify each account in\n"
            f"      the app and add confirmed followers to {CURATED_FILE_NAME}\n"
            "      (see docs/data-cleaning.md)."
        )

    # Under --assume-mutual the unverified remainder is promoted into Mutuals;
    # denied handles always stay in the 👻 list (ADR-0003 nuance).
    shown = result.curated_denied if ctx.assume_mutual else ins.ghost_list
    label = _count_label(len(shown), graph)
    print(f"\n👻  People you follow who DON'T follow you back ({label}):")
    for k in sorted(shown):
        print(f"   • {result.show(k)}")

    if result.pending_requests:
        print(
            f"\n⏳  Pending follow requests — not yet accepted, excluded above "
            f"({len(result.pending_requests)}):"
        )
        for k in sorted(result.pending_requests):
            print(f"   • {result.show(k)}")

    return {result.show(k) for k in shown}


def who_you_dont_follow_back(ctx: AnalyzerContext) -> set[str]:
    """Followers you don't follow back (handles are matched case-insensitively)."""
    ins = _connections(ctx)
    if not ins:
        return set()
    graph = ins.graph
    not_followed_back = graph.not_followed_back
    label = _count_label(len(not_followed_back), graph)
    print(f"\n🙈  Followers you DON'T follow back ({label}):")
    for k in sorted(not_followed_back):
        print(f"   • {graph.show(k)}")
    return {graph.show(k) for k in not_followed_back}


def mutual_followers(ctx: AnalyzerContext) -> set[str]:
    """Accounts you both follow and are followed by, incl. curation promotions."""
    ins = _connections(ctx)
    if not ins:
        return set()
    mutual = ins.effective.mutuals
    label = _count_label(len(mutual), ins.effective)
    print(f"\n🤝  Mutuals ({label}):")
    if ins.promoted:
        kind = "confirmed + assumed (--assume-mutual)" if ctx.assume_mutual else "confirmed via curation"
        print(f"   (+{len(ins.promoted)} promoted — {kind}; raw export mutuals: {len(ins.graph.mutuals)})")
    for k in sorted(mutual):
        print(f"   • {ins.effective.show(k)}")
    return {ins.effective.show(k) for k in mutual}


def blocked_accounts(ctx: AnalyzerContext):
    data = _read_json_file(ctx.base_dir / "connections/followers_and_following/blocked_accounts.json")
    if not data:
        return
    blocked = data.get("relationships_blocked_users", [])
    print(f"\n🚫  Blocked accounts ({len(blocked)}):")
    for entry in blocked:
        u = username_from_connection_entry(entry)
        if u:
            print(f"   • {u}")


def close_friends(ctx: AnalyzerContext):
    data = _read_json_file(ctx.base_dir / "connections/followers_and_following/close_friends.json")
    if not data:
        return
    friends = data.get("relationships_close_friends", [])
    print(f"\n⭐  Close friends ({len(friends)}):")
    for entry in friends:
        u = username_from_connection_entry(entry)
        if u:
            print(f"   • {u}")


# ══════════════════════════════════════════════════════════════════════════════
# 2–5. ACTIVITY / SECURITY / ADS / MESSAGES / APPS / CONTACTS
#     (insight packages — inventory-first reports)
# ══════════════════════════════════════════════════════════════════════════════

def activity_report(ctx: AnalyzerContext) -> None:
    print_activity_report(_activity(ctx), limit=ctx.ads_limit)


def security_report(ctx: AnalyzerContext) -> None:
    print_security_report(_security(ctx), limit=ctx.ads_limit, redact=ctx.redact)


def ads_and_tracking(ctx: AnalyzerContext) -> None:
    """Inventory-first ads & tracking report (ADR-0007)."""
    print_ads_report(_ads(ctx), limit=ctx.ads_limit)


def messages_report(ctx: AnalyzerContext) -> None:
    print_messages_report(_messages(ctx), limit=ctx.ads_limit)


def apps_report(ctx: AnalyzerContext) -> None:
    print_apps_report(_apps(ctx), limit=ctx.ads_limit)


def contacts_report(ctx: AnalyzerContext) -> None:
    print_contacts_report(_contacts(ctx), limit=ctx.ads_limit, redact=ctx.redact)


def shopping_report(ctx: AnalyzerContext) -> None:
    print_shopping_report(_shopping(ctx), limit=ctx.ads_limit)


def preferences_report(ctx: AnalyzerContext) -> None:
    print_preferences_report(_preferences(ctx), limit=ctx.ads_limit)


# ══════════════════════════════════════════════════════════════════════════════
# 6. PERSONAL INFORMATION  ──  profile info
# ══════════════════════════════════════════════════════════════════════════════

def profile_info(ctx: AnalyzerContext):
    data = load(ctx.base_dir,"personal_information/personal_information/personal_information.json")
    if not data:
        return
    info = data.get("profile_user", [{}])[0].get("string_map_data", {})
    print("\n👤  Your profile info:")
    for key, val in info.items():
        v = val.get("value") or val.get("timestamp")
        if v:
            if ctx.redact and key in _PROFILE_MASKS and isinstance(v, str):
                v = _PROFILE_MASKS[key](v)
            print(f"   {key:<25} {v}")


# ══════════════════════════════════════════════════════════════════════════════
# RUN ALL (or call individual functions above)
# ══════════════════════════════════════════════════════════════════════════════

_REPORT_SECTIONS = frozenset(
    {
        "profile",
        "connections",
        "activity",
        "security",
        "ads",
        "messages",
        "apps",
        "contacts",
        "shopping",
        "preferences",
    }
)


def _parse_sections(raw: list[str]) -> set[str]:
    chosen: set[str] = set()
    for item in raw:
        for part in item.split(","):
            part = part.strip().lower()
            if part:
                chosen.add(part)
    if not chosen or "all" in chosen:
        return set(_REPORT_SECTIONS)
    unknown = chosen - _REPORT_SECTIONS
    if unknown:
        raise SystemExit(
            f"Unknown section(s): {', '.join(sorted(unknown))}. "
            f"Choose from: {', '.join(sorted(_REPORT_SECTIONS))}, all."
        )
    return chosen


def _print_header(ctx: AnalyzerContext) -> None:
    print("=" * 60)
    print("  INSTAGRAM EXPORT ANALYSER")
    print("=" * 60)
    print(f"\n  Export folder:\n  {redact_path(str(ctx.base_dir.resolve()), ctx.redact)}")
    print(
        "\n  Note: results only reflect this ZIP snapshot. Instagram can omit or delay data;\n"
        "  if the app disagrees, request a new download (Settings → Download your information)."
    )
    if ctx.redact:
        print(
            "  Personal details (email, phone, date of birth, IPs) are redacted —\n"
            "  use --no-redact to see raw values."
        )


def run_reports(ctx: AnalyzerContext, sections: set[str]) -> None:
    """Run selected report sections against the context's export."""
    if "profile" in sections:
        profile_info(ctx)

    if "connections" in sections:
        print("\n── CONNECTIONS ──────────────────────────────────────────")
        connection_summary(ctx)
        who_doesnt_follow_back(ctx)
        who_you_dont_follow_back(ctx)
        mutual_followers(ctx)
        blocked_accounts(ctx)
        close_friends(ctx)

    if "activity" in sections:
        print("\n── ACTIVITY ─────────────────────────────────────────────")
        activity_report(ctx)

    if "security" in sections:
        print("\n── SECURITY ─────────────────────────────────────────────")
        security_report(ctx)

    if "ads" in sections:
        print("\n── ADS & TRACKING ───────────────────────────────────────")
        ads_and_tracking(ctx)

    if "messages" in sections:
        print("\n── MESSAGES ─────────────────────────────────────────────")
        messages_report(ctx)

    if "apps" in sections:
        print("\n── APPS & WEBSITES ──────────────────────────────────────")
        apps_report(ctx)

    if "contacts" in sections:
        print("\n── CONTACTS ─────────────────────────────────────────────")
        contacts_report(ctx)

    if "shopping" in sections:
        print("\n── SHOPPING ─────────────────────────────────────────────")
        shopping_report(ctx)

    if "preferences" in sections:
        print("\n── PREFERENCES ──────────────────────────────────────────")
        preferences_report(ctx)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="watchr",
        description=(
            "Watchr — your unofficial watcher for Instagram exports.\n"
            "Parse an Instagram data export (JSON) and print readable, offline reports."
        ),
        epilog="Personal details are redacted by default; use --no-redact for raw values.",
    )
    parser.add_argument(
        "--export-dir",
        metavar="DIR",
        help="unzipped export folder (default: $INSTAGRAM_EXPORT_DIR, or the "
        "instagram-* folder next to this script)",
    )
    parser.add_argument(
        "--zip",
        metavar="FILE",
        help="Instagram export ZIP (extracted automatically for this run)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify export setup and list available data (exit 0 if ready)",
    )
    parser.add_argument(
        "--section",
        action="append",
        default=None,
        metavar="NAME",
        help="report section: profile, connections, activity, security, ads, "
        "messages, apps, contacts, shopping, preferences, or all "
        "(repeatable, comma-separated; default: all)",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="write report to FILE instead of stdout",
    )
    parser.add_argument(
        "--curated",
        metavar="FILE",
        help=f"override path to {CURATED_FILE_NAME} — handles you visually confirmed "
        "follow you back (default: the file next to the export folder)",
    )
    parser.add_argument(
        "--assume-mutual",
        action="store_true",
        help="treat the unverified don't-follow-back remainder as mutuals — use only "
        "when you know you follow everyone back; accounts are moved to Mutuals "
        "and labeled as assumed (see docs/data-cleaning.md)",
    )
    parser.add_argument(
        "--bootstrap-curated",
        action="store_true",
        help=f"write a commented checklist of unverified handles to "
        f"{CURATED_FILE_NAME} for in-app verification, then exit",
    )
    parser.add_argument(
        "--curate",
        action="store_true",
        help="interactive curation: asks for your in-app follower/following totals, "
        "then walks you through unverified accounts (y/n/s/a/q) until curated "
        "numbers resemble the app; answers persist in curated_followers.txt / "
        "curated_nonfollowers.txt",
    )
    parser.add_argument(
        "--ads-limit",
        type=int,
        default=30,
        metavar="N",
        help="max sample rows for ads/activity/messages/apps/contacts lists "
        "(default: 30; 0 = all)",
    )
    parser.add_argument(
        "--no-redact",
        action="store_true",
        help="show email, phone number, date of birth and login IPs unmasked",
    )
    args = parser.parse_args(argv)

    try:
        base_dir = resolve_export_dir(export_dir=args.export_dir, zip_path=args.zip)
    except (FileNotFoundError, ValueError) as exc:
        print(f"  [!] {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    ctx = AnalyzerContext(
        base_dir=base_dir,
        redact=not args.no_redact,
        curated_path=Path(args.curated).expanduser() if args.curated else None,
        assume_mutual=args.assume_mutual,
        project_root=Path(__file__).resolve().parent,
        ads_limit=max(0, args.ads_limit),
    )
    # Avoid stale data when main() is called multiple times in-process (tests/library).
    _connections_cache.clear()
    _ads_cache.clear()
    _activity_cache.clear()
    _security_cache.clear()
    _messages_cache.clear()
    _apps_cache.clear()
    _contacts_cache.clear()
    _shopping_cache.clear()
    _preferences_cache.clear()

    # One-time legacy transition: copy curated state that used to live next to
    # the repository into this export's own store (ADR-0002 addendum). Skipped
    # for --check and for exports under the test tree, so a fresh clone never
    # inherits someone else's curation and fixtures stay independent.
    if not args.check and ctx.curated_path is None:
        store = ctx.curation_store()
        if store.root == ctx.base_dir and "tests" not in ctx.base_dir.parts:
            moved = migrate_legacy_curation(store, ctx.project_root)
            if moved:
                print(
                    f"  [i] Moved {moved} legacy curated file(s) into the export folder "
                    f"({store.root}) — curation is now per-export.",
                    file=sys.stderr,
                )

    if args.check:
        raise SystemExit(run_setup_check(base_dir))

    if args.bootstrap_curated:
        ins = _connections(ctx)
        if not ins:
            print(
                "  [!] Connection files not found — cannot build checklist",
                file=sys.stderr,
            )
            raise SystemExit(1)
        store = ctx.curation_store()
        try:
            written = store.write_checklist(ins.cleaning.unverified)
        except FileExistsError:
            print(
                f"  [!] {store.confirmed_path} already exists — pass --curated FILE to\n"
                "       write the checklist elsewhere",
                file=sys.stderr,
            )
            raise SystemExit(1) from None
        print(
            f"Checklist written to {written}\n"
            f"  {len(ins.cleaning.unverified)} unverified handles listed (commented out).\n"
            "  Verify each in the app, delete the leading '# ' to confirm, then re-run."
        )
        return

    if args.curate:
        ins = _connections(ctx)
        if not ins:
            print(
                "  [!] Connection files not found — cannot start curation",
                file=sys.stderr,
            )
            raise SystemExit(1)
        run_curation_session(ins.graph, ctx.curation_store())
        # The session just rewrote curated state; drop the cached insights so
        # the post-session report reflects the fresh answers.
        _connections_cache.clear()
        # Immediately show the numbers with the fresh answers applied.
        _print_header(ctx)
        connection_summary(ctx)
        who_doesnt_follow_back(ctx)
        mutual_followers(ctx)
        return

    sections = _parse_sections(args.section or ["all"])

    def _run() -> None:
        _print_header(ctx)
        run_reports(ctx, sections)

    if args.output:
        out_path = Path(args.output).expanduser()
        with out_path.open("w", encoding="utf-8") as handle, redirect_stdout(handle):
            _run()
        print(f"Report written to {out_path}", file=sys.stderr)
    else:
        _run()


if __name__ == "__main__":
    main()