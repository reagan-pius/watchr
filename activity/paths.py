"""Canonical activity-related paths inside an Instagram JSON export."""

from __future__ import annotations

from export_inventory import FileGroup

POSTS = FileGroup(
    key="posts",
    label="posts",
    relative_paths=(
        "your_instagram_activity/media/posts_1.json",
        "your_instagram_activity/content/posts_1.json",
    ),
)

STORIES = FileGroup(
    key="stories",
    label="stories archive",
    relative_paths=(
        "your_instagram_activity/media/stories.json",
        "your_instagram_activity/content/stories.json",
    ),
)

REELS = FileGroup(
    key="reels",
    label="reels",
    relative_paths=(
        "your_instagram_activity/media/reels.json",
        "your_instagram_activity/content/reels.json",
        "your_instagram_activity/media/reels_1.json",
    ),
)

LIKED_POSTS = FileGroup(
    key="liked_posts",
    label="liked posts",
    relative_paths=("your_instagram_activity/likes/liked_posts.json",),
)

LIKED_COMMENTS = FileGroup(
    key="liked_comments",
    label="liked comments",
    relative_paths=("your_instagram_activity/likes/liked_comments.json",),
)

COMMENTS = FileGroup(
    key="comments",
    label="your comments",
    relative_paths=(
        "your_instagram_activity/comments/post_comments_1.json",
        "your_instagram_activity/comments/post_comments.json",
    ),
)

SEARCHES = FileGroup(
    key="searches",
    label="profile / account searches",
    relative_paths=(
        "logged_information/recent_searches/profile_searches.json",
        "your_instagram_activity/recent_searches/account_searches.json",
    ),
)

SAVED = FileGroup(
    key="saved",
    label="saved posts",
    relative_paths=(
        "your_instagram_activity/saved/saved_posts.json",
        "your_instagram_activity/saved/saved_collections.json",
    ),
)

STORY_LIKES = FileGroup(
    key="story_likes",
    label="story likes",
    relative_paths=(
        "your_instagram_activity/story_interactions/story_likes.json",
        "your_instagram_activity/story_interactions/stories_liked.json",
    ),
)

STORY_POLLS = FileGroup(
    key="story_polls",
    label="story polls",
    relative_paths=("your_instagram_activity/story_interactions/polls.json",),
)

ACTIVITY_FILE_GROUPS: tuple[FileGroup, ...] = (
    POSTS,
    STORIES,
    REELS,
    LIKED_POSTS,
    LIKED_COMMENTS,
    COMMENTS,
    SEARCHES,
    SAVED,
    STORY_LIKES,
    STORY_POLLS,
)
