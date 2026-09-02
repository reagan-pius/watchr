"""Locate and validate Instagram export folders (and ZIP archives)."""

from __future__ import annotations

import os
import tempfile
import zipfile
from pathlib import Path

from connections.graph import auto_detect_export_dir


def is_export_root(path: Path) -> bool:
    return path.is_dir() and (
        (path / "connections").is_dir() or (path / "personal_information").is_dir()
    )


def find_export_root(base: Path) -> Path | None:
    """Return the export root inside base (handles nested instagram-* folders)."""
    base = base.expanduser().resolve()
    if is_export_root(base):
        return base
    nested = sorted(p for p in base.glob("instagram-*") if p.is_dir() and is_export_root(p))
    if nested:
        return nested[0]
    subs = [p for p in base.iterdir() if p.is_dir()] if base.is_dir() else []
    if len(subs) == 1 and is_export_root(subs[0]):
        return subs[0]
    return None


def resolve_export_dir(
    *,
    export_dir: str | Path | None = None,
    zip_path: str | Path | None = None,
    search_base: Path | None = None,
) -> Path:
    """
    Resolve an export folder from CLI flags, env, ZIP, or auto-detect.

    Returns the export root path. Raises FileNotFoundError or ValueError on failure.
    """
    if export_dir and zip_path:
        raise ValueError("Pass only one of --export-dir or --zip, not both.")

    if zip_path:
        return extract_export_zip(Path(zip_path))

    if export_dir:
        root = find_export_root(Path(export_dir))
        if root is None:
            raise FileNotFoundError(
                f"Not a valid Instagram export folder: {Path(export_dir).expanduser()}"
            )
        return root

    env = os.environ.get("INSTAGRAM_EXPORT_DIR")
    if env:
        root = find_export_root(Path(env))
        if root is None:
            raise FileNotFoundError(
                f"INSTAGRAM_EXPORT_DIR is set but not a valid export: {env}"
            )
        return root

    base = search_base or Path(__file__).resolve().parent
    detected = auto_detect_export_dir(base)
    if detected and is_export_root(detected):
        return detected

    raise FileNotFoundError(
        "No export found. Pass --export-dir or --zip, set INSTAGRAM_EXPORT_DIR, "
        "or unzip an instagram-* folder next to this project."
    )


def extract_export_zip(zip_path: Path) -> Path:
    """Extract a ZIP to a temp directory and return the export root inside it."""
    zip_path = zip_path.expanduser().resolve()
    if not zip_path.is_file():
        raise FileNotFoundError(f"ZIP not found: {zip_path}")

    tmp = Path(tempfile.mkdtemp(prefix="ig-export-"))
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp)
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Not a valid ZIP file: {zip_path}") from exc

    root = find_export_root(tmp)
    if root is None:
        raise ValueError(
            f"ZIP extracted but no Instagram export layout found inside: {zip_path}"
        )
    return root
