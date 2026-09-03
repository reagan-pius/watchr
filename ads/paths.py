"""Canonical ads-related paths inside an Instagram JSON export."""

from __future__ import annotations

from export_inventory import FileGroup

# Meta relocates files between export generations; keep aliases ordered
# newest / most common first.

ADVERTISERS = FileGroup(
    key="advertisers",
    label="advertisers using your activity or information",
    relative_paths=(
        "ads_information/instagram_ads_and_businesses/advertisers_using_your_activity_or_information.json",
        "ads_information/advertisers_using_your_activity_or_information.json",
    ),
)

ADS_INTERESTS = FileGroup(
    key="ads_interests",
    label="ads interests",
    relative_paths=(
        "ads_information/instagram_ads_and_businesses/ads_interests.json",
        "ads_information/ads_interests.json",
    ),
)

CATEGORIES_USED = FileGroup(
    key="categories_used",
    label="other categories used to reach you",
    relative_paths=(
        "ads_information/instagram_ads_and_businesses/other_categories_used_to_reach_you.json",
        "ads_information/other_categories_used_to_reach_you.json",
    ),
)

ADS_VIEWED = FileGroup(
    key="ads_viewed",
    label="ads viewed",
    relative_paths=(
        "ads_information/ads_and_topics/ads_viewed.json",
        "ads_information/instagram_ads_and_businesses/ads_viewed.json",
        "logged_information/ads_and_topics/ads_viewed.json",
    ),
)

ADS_CLICKED = FileGroup(
    key="ads_clicked",
    label="ads clicked",
    relative_paths=(
        "ads_information/ads_and_topics/ads_clicked.json",
        "ads_information/instagram_ads_and_businesses/ads_clicked.json",
        "logged_information/ads_and_topics/ads_clicked.json",
    ),
)

AD_PREFERENCES = FileGroup(
    key="ad_preferences",
    label="ad preferences",
    relative_paths=(
        "ads_information/ad_preferences.json",
        "ads_information/instagram_ads_and_businesses/ad_preferences.json",
        "preferences/ad_preferences.json",
    ),
)

OFF_INSTAGRAM = FileGroup(
    key="off_instagram",
    label="off-Instagram activity",
    relative_paths=(
        "logged_information/ads_and_topics/off_instagram_activity.json",
        "apps_and_websites_off_of_instagram/apps_and_websites/your_activity_off_meta_technologies.json",
        "ads_information/instagram_ads_and_businesses/off_instagram_activity.json",
    ),
)

ADS_FILE_GROUPS: tuple[FileGroup, ...] = (
    ADVERTISERS,
    ADS_INTERESTS,
    CATEGORIES_USED,
    ADS_VIEWED,
    ADS_CLICKED,
    AD_PREFERENCES,
    OFF_INSTAGRAM,
)
