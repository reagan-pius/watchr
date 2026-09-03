"""Ads domain models (pure data)."""

from __future__ import annotations

from dataclasses import dataclass, field

from export_inventory import InventoryItem


@dataclass(frozen=True)
class Advertiser:
    name: str
    data_file: bool = False
    remarketing: bool = False
    in_person_store: bool = False

    def flag_labels(self) -> list[str]:
        labels: list[str] = []
        if self.data_file:
            labels.append("data-file")
        if self.remarketing:
            labels.append("remarketing")
        if self.in_person_store:
            labels.append("store-visit")
        return labels or ["(no flags)"]


@dataclass(frozen=True)
class AudienceFlagCounts:
    total: int = 0
    data_file: int = 0
    remarketing: int = 0
    in_person_store: int = 0


@dataclass(frozen=True)
class AdEvent:
    author: str
    timestamp: int | None = None


@dataclass(frozen=True)
class EngagementSummary:
    viewed_count: int = 0
    clicked_count: int = 0
    viewed_span: tuple[str, str] | None = None
    clicked_span: tuple[str, str] | None = None
    top_viewed: tuple[tuple[str, int], ...] = ()
    top_clicked: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True)
class OffIgApp:
    name: str
    event_count: int = 0


@dataclass(frozen=True)
class AdPreferencesSummary:
    topics_added: tuple[str, ...] = ()
    topics_removed: tuple[str, ...] = ()
    note: str | None = None
