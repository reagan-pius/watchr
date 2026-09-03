"""AdsInsights — compute-once ads/tracking value for one export run (ADR-0007)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ads import parse as ads_parse
from ads.models import (
    AdPreferencesSummary,
    Advertiser,
    AudienceFlagCounts,
    EngagementSummary,
    OffIgApp,
)
from ads.paths import ADS_FILE_GROUPS
from export_inventory import InventoryItem, build_inventory


@dataclass
class AdsInsights:
    """All ads/tracking facts for one export, computed exactly once."""

    inventory: list[InventoryItem] = field(default_factory=list)
    advertisers: list[Advertiser] = field(default_factory=list)
    flag_counts: AudienceFlagCounts = field(default_factory=AudienceFlagCounts)
    interests: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    engagement: EngagementSummary = field(default_factory=EngagementSummary)
    off_ig_apps: list[OffIgApp] = field(default_factory=list)
    preferences: AdPreferencesSummary | None = None

    @classmethod
    def build(cls, export_dir: Path) -> AdsInsights:
        export_dir = export_dir.resolve()
        advertisers = ads_parse.load_advertisers(export_dir)
        return cls(
            inventory=build_inventory(export_dir, ADS_FILE_GROUPS),
            advertisers=advertisers,
            flag_counts=ads_parse.flag_counts_for(advertisers)
            if advertisers
            else AudienceFlagCounts(),
            interests=ads_parse.load_interests(export_dir),
            categories=ads_parse.load_categories(export_dir),
            engagement=ads_parse.load_engagement(export_dir),
            off_ig_apps=ads_parse.load_off_instagram(export_dir),
            preferences=ads_parse.load_preferences(export_dir),
        )
