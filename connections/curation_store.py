"""CurationStore — the single owner of curated state on disk (ADR-0002).

Owns exactly three files, rooted at one directory:

    curated_followers.txt      handles confirmed to follow the user back
    curated_nonfollowers.txt   handles confirmed NOT to follow back
    curation_meta.json         in-app reference figures (followers/following)

All reads and writes of these files go through this module. The data-loss
guard (never overwrite a non-empty confirmed file with an empty set) lives
here, so every writer is protected — see the incident recorded in the ADR.

Default root resolution (ADR-0002 addendum) — per-export, so a fresh clone
never inherits another user's curation:

  1. explicit --curated FILE's parent, else
  2. the export folder itself when it is a stable directory, else
  3. a stable per-export cache (~/.cache/ig-analyzer/<export-name>) when the
     export folder is a temp extraction from --zip (so curation survives
     across runs of the same ZIP).

Reads are unioned with export-embedded copies of the same files when the
root differs from the export folder (root != export dir).
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

CURATED_FILE_NAME = "curated_followers.txt"
CURATED_NONFOLLOWERS_FILE_NAME = "curated_nonfollowers.txt"
CURATION_META_FILE_NAME = "curation_meta.json"

_ANSWER_HEADER_FOLLOWERS = [
    "# Handles confirmed to follow me back (written by the curation session).",
]
_ANSWER_HEADER_NONFOLLOWERS = [
    "# Handles confirmed NOT to follow me back (written by the curation session).",
]


def _norm(u: str) -> str:
    return u.strip().casefold()


def read_handle_file(paths: list[Path]) -> set[str]:
    """Casefolded handles from curated text files (# comments, one per line)."""
    handles: set[str] = set()
    for path in paths:
        if not path.is_file():
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                cleaned = re.sub(r"#.*$", "", line).strip()
                if cleaned:
                    handles.add(_norm(cleaned))
    return handles


def write_curated_file(path: Path, handles, header_lines=None) -> Path:
    """Persist a curated file (header comment + one handle per line, sorted)."""
    lines = list(header_lines or [])
    if lines:
        lines.append("")
    lines.extend(sorted(handles))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@dataclass
class CurationSnapshot:
    """View of the curated state at one moment."""

    confirmed: set[str] = field(default_factory=set)
    denied: set[str] = field(default_factory=set)
    meta: dict = field(default_factory=dict)


@dataclass
class SaveResult:
    """Outcome of a store.save() call (drives wizard messaging)."""

    confirmed_written: bool
    skipped_existing: int = 0   # handles preserved by the data-loss guard


def _is_temp_extraction(path: Path) -> bool:
    """True when ``path`` is an export folder auto-extracted from a --zip run.

    ``export_paths.extract_export_zip`` extracts to a ``tempfile.mkdtemp``
    directory whose name starts with ``ig-export-``.
    """
    try:
        tmp = Path(tempfile.gettempdir()).resolve()
    except OSError:
        return False
    resolved = path.resolve()
    if not _is_relative_to(resolved, tmp):
        return False
    return Path(resolved.name).name.startswith("ig-export-") if resolved.name else False


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


LEGACY_CURATED_FILE_NAMES = (
    CURATED_FILE_NAME,
    CURATED_NONFOLLOWERS_FILE_NAME,
    CURATION_META_FILE_NAME,
)


def migrate_legacy_curation(store: CurationStore, legacy_root: Path | None) -> int:
    """Copy legacy curated files from ``legacy_root`` (e.g. an old project root)
    into the store's root when the target lacks them. Returns files copied.

    This is the one-time transition helper for installs that kept
    ``curated_followers.txt`` next to the repository before curation became
    export-scoped. It never overwrites existing curated state.
    """
    if legacy_root is None:
        return 0
    legacy_root = legacy_root.expanduser().resolve()
    if legacy_root == store.root.resolve() or legacy_root == (
        store.export_dir and store.export_dir.resolve()
    ):
        return 0
    moved = 0
    for name in LEGACY_CURATED_FILE_NAMES:
        src = legacy_root / name
        dst = store.root / name
        if src.is_file() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            moved += 1
    return moved


class CurationStore:
    """Read/write access to the three curated-state files."""

    def __init__(self, root: Path, export_dir: Path | None = None):
        self.root = root
        self.export_dir = export_dir

    @classmethod
    def resolve(
        cls,
        explicit_curated: Path | None,
        export_dir: Path,
        project_root: Path | None = None,
    ) -> "CurationStore":
        """Resolve the default curated-state root (see module docstring).

        ``project_root`` is accepted for backward compatibility; it is only
        used as the legacy-migration source (see ``migrate_legacy_curation``),
        never as the default root.
        """
        if explicit_curated is not None:
            return cls(root=explicit_curated.parent, export_dir=export_dir)
        root = export_dir
        if _is_temp_extraction(export_dir):
            root = Path.home() / ".cache" / "ig-analyzer" / export_dir.name
        return cls(root=root, export_dir=export_dir)

    @property
    def confirmed_path(self) -> Path:
        return self.root / CURATED_FILE_NAME

    @property
    def denied_path(self) -> Path:
        return self.root / CURATED_NONFOLLOWERS_FILE_NAME

    @property
    def meta_path(self) -> Path:
        return self.root / CURATION_META_FILE_NAME

    def load(self) -> CurationSnapshot:
        """Confirmed/denied/meta, unioned with export-embedded copies."""
        confirmed = read_handle_file([self.confirmed_path])
        denied = read_handle_file([self.denied_path])
        meta: dict = {}
        if self.export_dir is not None and self.export_dir != self.root:
            confirmed |= read_handle_file([self.export_dir / CURATED_FILE_NAME])
            denied |= read_handle_file([self.export_dir / CURATED_NONFOLLOWERS_FILE_NAME])
            meta_path = self.export_dir / CURATION_META_FILE_NAME
            if meta_path.is_file():
                try:
                    loaded = json.loads(meta_path.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        meta = loaded
                except (OSError, json.JSONDecodeError):
                    pass
        if not meta and self.meta_path.is_file():
            try:
                loaded = json.loads(self.meta_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    meta = loaded
            except (OSError, json.JSONDecodeError):
                pass
        return CurationSnapshot(confirmed=confirmed, denied=denied, meta=meta)

    def save(self, confirmed: set[str], denied: set[str], meta: dict | None = None) -> SaveResult:
        """Write all three files. Guards against wiping a non-empty
        confirmed file with an empty set."""
        wrote_confirmed = True
        skipped = 0
        if not confirmed:
            existing = read_handle_file([self.confirmed_path])
            if existing:
                wrote_confirmed = False
                skipped = len(existing)
        if wrote_confirmed:
            write_curated_file(self.confirmed_path, confirmed, _ANSWER_HEADER_FOLLOWERS)
        write_curated_file(self.denied_path, denied, _ANSWER_HEADER_NONFOLLOWERS)
        payload = {
            "app_followers": meta.get("app_followers") if meta else None,
            "app_following": meta.get("app_following") if meta else None,
            "note": "Totals as shown in the Instagram app when the curation session ran.",
        }
        self.meta_path.parent.mkdir(parents=True, exist_ok=True)
        self.meta_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return SaveResult(confirmed_written=wrote_confirmed, skipped_existing=skipped)

    def write_checklist(self, unverified: set[str]) -> Path:
        """Write the commented verification checklist (--bootstrap-curated).
        Refuses to overwrite an existing file (raises FileExistsError)."""
        if self.confirmed_path.exists():
            raise FileExistsError(self.confirmed_path)
        lines = [
            "# curated_followers.txt — verification checklist (generated by --bootstrap-curated)",
            "#",
            "# The follower export is incomplete, so each handle below was reported as",
            "# 'not following back' but may actually be a mutual. For each one, open",
            "# their profile in the Instagram app → Following → search your handle:",
            "#   - they follow you  → delete the leading '# ' to confirm (they will be",
            "#                        moved into Mutuals on the next run)",
            "#   - they don't       → leave the line commented out",
            "",
        ]
        lines.extend(f"# {handle}" for handle in sorted(unverified))
        self.confirmed_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return self.confirmed_path
