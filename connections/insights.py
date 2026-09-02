"""ConnectionsInsights — the compute-once value the report layer consumes.

ADR-0003: build one value per run (graph + cleaning result + promotion set +
effective graph + app-derived counts + source label), then let report
functions be pure ``insights -> str`` renderers.

Nuance locked in by the ADR: the effective (promoted) graph drives the
summary and the Mutuals list; the 👻 list stays driven by the
``CleaningResult`` (unverified ∪ denied) so pending and restricted accounts
never reappear in it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from connections.cleaning import CleaningResult, clean_connection_sets, promotion_set
from connections.curation_store import CurationSnapshot
from connections.graph import ConnectionGraph


@dataclass
class AppDerivedCounts:
    """One-way follow totals computed from in-app figures vs curated mutuals."""

    app_followers: int | None
    app_following: int | None
    curated_mutuals: int
    source: str  # "curation session" | "export insights"

    @property
    def available(self) -> bool:
        return self.app_followers is not None or self.app_following is not None

    @property
    def you_follow_dont_follow_back(self) -> int | None:
        if self.app_following is None:
            return None
        return self.app_following - self.curated_mutuals

    @property
    def they_follow_you_not_back(self) -> int | None:
        if self.app_followers is None:
            return None
        return self.app_followers - self.curated_mutuals


@dataclass
class ConnectionsInsights:
    """All connection facts for one run, computed exactly once."""

    graph: ConnectionGraph
    cleaning: CleaningResult
    promoted: set[str] = field(default_factory=set)
    effective: ConnectionGraph | None = None
    derived: AppDerivedCounts | None = None

    @property
    def ghost_list(self) -> set[str]:
        """Handles that should appear under 👻 (unverified + denied).

        Deliberately NOT effective-driven: promotion must not pull pending or
        restricted accounts back into this list (ADR-0003 nuance).
        """
        return self.cleaning.cleaned_not_following_back

    @property
    def pending_list(self) -> set[str]:
        return self.cleaning.pending_requests

    @property
    def show(self):
        return self.cleaning.show

    def ghost_handles_remaining_for_assume(self) -> set[str]:
        """Unverified remainder shown in 👻 (empty under --assume-mutual)."""
        return self.cleaning.unverified

    @classmethod
    def build(
        cls,
        graph: ConnectionGraph,
        snapshot: CurationSnapshot,
        *,
        assume_mutual: bool = False,
        meta_override: dict | None = None,
    ) -> "ConnectionsInsights":
        """Compute the whole picture once (ADR-0003)."""
        cleaning = clean_connection_sets(
            graph, snapshot=snapshot
        )
        promoted = promotion_set(cleaning, assume_remainder=assume_mutual)
        effective = graph.with_promoted(promoted)
        derived = _app_derived_counts(graph, effective, snapshot, meta_override)
        return cls(
            graph=graph,
            cleaning=cleaning,
            promoted=promoted,
            effective=effective,
            derived=derived,
        )


def _app_derived_counts(
    graph: ConnectionGraph,
    effective: ConnectionGraph,
    snapshot: CurationSnapshot,
    meta_override: dict | None = None,
) -> AppDerivedCounts | None:
    meta = dict(snapshot.meta or {})
    if meta_override:
        meta.update(meta_override)
    app_followers = meta.get("app_followers", graph.app_follower_count)
    app_following = meta.get("app_following", len(graph.following))
    if app_followers is None and app_following is None:
        return None
    source = "curation session" if snapshot.meta else "export insights"
    return AppDerivedCounts(
        app_followers=app_followers,
        app_following=app_following,
        curated_mutuals=len(effective.mutuals),
        source=source,
    )