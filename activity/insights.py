"""ActivityInsights — compute-once activity value for one export run."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from activity import parse as activity_parse
from activity.models import LabeledEvent, MonthCount
from activity.paths import ACTIVITY_FILE_GROUPS
from export_inventory import InventoryItem, build_inventory


@dataclass
class ActivityInsights:
    inventory: list[InventoryItem] = field(default_factory=list)
    post_total: int = 0
    posts_by_month: tuple[MonthCount, ...] = ()
    story_total: int = 0
    stories_by_month: tuple[MonthCount, ...] = ()
    reel_total: int = 0
    reels_by_month: tuple[MonthCount, ...] = ()
    liked_posts_total: int = 0
    recent_liked_posts: tuple[LabeledEvent, ...] = ()
    liked_comments_total: int = 0
    comment_targets: tuple[tuple[str, int], ...] = ()
    search_total: int = 0
    top_searches: tuple[tuple[str, int], ...] = ()
    saved_total: int = 0
    recent_saved: tuple[LabeledEvent, ...] = ()
    story_likes_total: int = 0
    story_polls_total: int = 0

    @classmethod
    def build(cls, export_dir: Path) -> ActivityInsights:
        export_dir = export_dir.resolve()
        parts = activity_parse.load_activity_parts(export_dir)
        post_total, posts_by_month = activity_parse.parse_posts(parts["posts"])
        story_total, stories_by_month = activity_parse.parse_stories(parts["stories"])
        reel_total, reels_by_month = activity_parse.parse_reels(parts["reels"])
        liked_total, recent_liked = activity_parse.parse_liked_posts(parts["liked"])
        saved_total, recent_saved = activity_parse.parse_saved(parts["saved"])
        search_total, top_searches = activity_parse.parse_searches(parts["searches"])
        return cls(
            inventory=build_inventory(export_dir, ACTIVITY_FILE_GROUPS),
            post_total=post_total,
            posts_by_month=posts_by_month,
            story_total=story_total,
            stories_by_month=stories_by_month,
            reel_total=reel_total,
            reels_by_month=reels_by_month,
            liked_posts_total=liked_total,
            recent_liked_posts=recent_liked,
            liked_comments_total=activity_parse.parse_liked_comments(parts["liked_c"]),
            comment_targets=activity_parse.parse_comment_targets(parts["comments"]),
            search_total=search_total,
            top_searches=top_searches,
            saved_total=saved_total,
            recent_saved=recent_saved,
            story_likes_total=activity_parse._count_list_payload(
                parts["story_likes"],
                "story_activities_story_likes",
                "stories_user_liked",
            ),
            story_polls_total=activity_parse._count_list_payload(
                parts["story_polls"],
                "story_activities_polls",
                "polls",
            ),
        )
