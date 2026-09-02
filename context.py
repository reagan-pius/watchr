"""AnalyzerContext — one immutable value holding a run's configuration.

Replaces the former module globals (BASE_DIR, REDACT, _graph_cache,
_curated_path, _assume_mutual). Built once in main() and passed explicitly
to every report function; see docs/adr/0001-analyzer-context.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from connections.curation_store import CurationStore


@dataclass(frozen=True)
class AnalyzerContext:
    """Everything one analyzer run depends on, as a value."""

    base_dir: Path                 # resolved export root (dir or extracted ZIP)
    redact: bool = True            # --no-redact flips this off for the run
    curated_path: Path | None = None   # explicit --curated FILE override
    assume_mutual: bool = False    # --assume-mutual policy flag
    project_root: Path | None = None   # legacy-migration source for curated state

    def curation_store(self) -> CurationStore:
        """The curated-state store for this run (ADR-0002)."""
        return CurationStore.resolve(
            explicit_curated=self.curated_path,
            export_dir=self.base_dir,
            project_root=self.project_root,
        )
