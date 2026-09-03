"""MessagesInsights — metadata-only DM summary (ADR follow-on to full export analyser)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from messages.parse import ThreadMeta, scan_threads


@dataclass
class MessagesInsights:
    root_rel: str | None = None
    threads: list[ThreadMeta] = field(default_factory=list)

    @property
    def inbox_count(self) -> int:
        return sum(1 for t in self.threads if t.bucket == "inbox")

    @property
    def request_count(self) -> int:
        return sum(1 for t in self.threads if t.bucket == "requests")

    @property
    def message_total(self) -> int:
        return sum(t.message_count for t in self.threads)

    @property
    def media_total(self) -> int:
        return sum(t.media_file_count for t in self.threads)

    @classmethod
    def build(cls, export_dir: Path) -> MessagesInsights:
        export_dir = export_dir.resolve()
        root, threads = scan_threads(export_dir)
        root_rel = None
        if root is not None:
            try:
                root_rel = str(root.relative_to(export_dir))
            except ValueError:
                root_rel = str(root)
        # Largest threads first for sampling
        threads_sorted = sorted(threads, key=lambda t: t.message_count, reverse=True)
        return cls(root_rel=root_rel, threads=threads_sorted)
