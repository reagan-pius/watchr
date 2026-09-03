"""Activity domain models (pure data)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MonthCount:
    month: str
    count: int


@dataclass(frozen=True)
class LabeledEvent:
    label: str
    timestamp: int | None = None
