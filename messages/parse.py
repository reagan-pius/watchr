"""Parse DM thread folders for metadata only (no message content)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from messages.paths import INBOX_NAMES, MESSAGE_ROOT_CANDIDATES, REQUEST_NAMES

_THREAD_DIR_RE = re.compile(r"^(.+)_(\d+)$")


@dataclass(frozen=True)
class ThreadMeta:
    folder_name: str
    title: str
    participants: tuple[str, ...]
    message_count: int
    first_ts_ms: int | None
    last_ts_ms: int | None
    media_file_count: int
    bucket: str  # inbox | requests


def find_messages_root(export_dir: Path) -> Path | None:
    for rel in MESSAGE_ROOT_CANDIDATES:
        root = export_dir / rel
        if root.is_dir():
            return root
    return None


def _participant_names(data: dict) -> tuple[str, ...]:
    names: list[str] = []
    for p in data.get("participants") or []:
        if isinstance(p, dict):
            n = p.get("name") or p.get("username")
            if n:
                names.append(str(n))
        elif isinstance(p, str):
            names.append(p)
    return tuple(names)


def _message_timestamps(messages: list[Any]) -> tuple[int | None, int | None, int]:
    stamps: list[int] = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        ts = m.get("timestamp_ms")
        if ts is None:
            ts = m.get("timestamp")
        if isinstance(ts, (int, float)):
            # normalize seconds → ms if clearly seconds
            iv = int(ts)
            if iv < 10_000_000_000:
                iv *= 1000
            stamps.append(iv)
    if not stamps:
        return None, None, len(messages)
    return min(stamps), max(stamps), len(messages)


def _media_count(thread_dir: Path) -> int:
    n = 0
    for sub in ("photos", "videos", "audio", "files", "gifs"):
        d = thread_dir / sub
        if d.is_dir():
            n += sum(1 for p in d.rglob("*") if p.is_file())
    return n


def _load_thread(thread_dir: Path, bucket: str) -> ThreadMeta | None:
    message_files = sorted(thread_dir.glob("message_*.json"))
    if not message_files:
        # some exports use a single messages.json
        alt = thread_dir / "messages.json"
        if alt.is_file():
            message_files = [alt]
        else:
            return None

    participants: list[str] = []
    title = thread_dir.name
    m = _THREAD_DIR_RE.match(thread_dir.name)
    if m:
        title = m.group(1)
    total_msgs = 0
    first_ts: int | None = None
    last_ts: int | None = None

    for mf in message_files:
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        if data.get("title"):
            title = str(data["title"])
        participants.extend(_participant_names(data))
        messages = data.get("messages") or []
        if isinstance(messages, list):
            f, l, count = _message_timestamps(messages)
            total_msgs += count
            if f is not None:
                first_ts = f if first_ts is None else min(first_ts, f)
            if l is not None:
                last_ts = l if last_ts is None else max(last_ts, l)

    # Deduplicate participants preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for p in participants:
        key = p.casefold()
        if key not in seen:
            seen.add(key)
            uniq.append(p)

    return ThreadMeta(
        folder_name=thread_dir.name,
        title=title,
        participants=tuple(uniq),
        message_count=total_msgs,
        first_ts_ms=first_ts,
        last_ts_ms=last_ts,
        media_file_count=_media_count(thread_dir),
        bucket=bucket,
    )


def scan_threads(export_dir: Path) -> tuple[Path | None, list[ThreadMeta]]:
    root = find_messages_root(export_dir)
    if root is None:
        return None, []
    threads: list[ThreadMeta] = []
    for bucket, names in (("inbox", INBOX_NAMES), ("requests", REQUEST_NAMES)):
        for name in names:
            folder = root / name
            if not folder.is_dir():
                continue
            for child in sorted(folder.iterdir()):
                if child.is_dir():
                    meta = _load_thread(child, bucket)
                    if meta:
                        threads.append(meta)
    return root, threads
