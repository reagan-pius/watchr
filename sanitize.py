#!/usr/bin/env python3
"""
Sanitize an analyzer output (or any text file) so it's safe to commit or share.

Masks by default:
  • email addresses          → r***@gmail.com
  • phone numbers            → +*********434
  • IP addresses             → 105.16.***.***
  • "Date of birth" lines    → ****-**-**
  • export folder names      → instagram-***-2026-04-02-AbCdEf
  • account handles          → user_001, user_002, … ("me" for your own account)
                                (only when the export folder is available;
                                 disable with --keep-handles)

Usage:
  python3 sanitize.py output.txt -o output.example.txt
  python3 sanitize.py report.txt            # prints to stdout
  cat report.txt | python3 sanitize.py -    # read from stdin
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

from connections.graph import auto_detect_export_dir, iter_connection_handles

# ─── PII PATTERNS ─────────────────────────────────────────────────────────────
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# 9–15 consecutive digits (optionally with a leading +): phone numbers.
# Won't match timestamps ("10:22"), dates ("2026-04-02") or counts ("(13)").
PHONE_RE = re.compile(r"(?<![\w./-])\+?\d{9,15}(?![\w.-])")

IP_RE = re.compile(r"\b(\d{1,3}\.\d{1,3})\.(\d{1,3})\.(\d{1,3})\b")

DOB_LINE_RE = re.compile(r"(?m)^(\s*Date of birth\s+).+$")

NAME_LINE_RE = re.compile(r"(?m)^(\s*Name\s+).+$")

EXPORT_FOLDER_RE = re.compile(r"(instagram-)[^/\s]+?(-\d{4}-\d{2}-\d{2}-\w+)")


def _find_export_dir(explicit: str | None) -> Path | None:
    if explicit:
        p = Path(explicit).expanduser().resolve()
        return p if p.is_dir() else None
    env = os.environ.get("INSTAGRAM_EXPORT_DIR")
    if env:
        p = Path(env).expanduser().resolve()
        if p.is_dir():
            return p
    return auto_detect_export_dir()


def collect_handles(export_dir: Path) -> tuple[str, set[str]]:
    """(own username, set of every other handle mentioned by the export)."""
    own = ""
    others: set[str] = set()

    pi = export_dir / "personal_information/personal_information/personal_information.json"
    if pi.is_file():
        data = _load(pi)
        for item in data.get("profile_user", []):
            u = item.get("string_map_data", {}).get("Username", {}).get("value")
            if u:
                own = str(u).strip()

    for h in iter_connection_handles(export_dir):
        others.add(h)

    inbox = export_dir / "your_instagram_activity/messages/inbox"
    if inbox.is_dir():
        for d in inbox.iterdir():
            m = re.match(r"(.+)_\d+$", d.name)
            if m:
                others.add(m.group(1))

    others.discard(own)
    return own, others


def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


# ─── SANITIZING ───────────────────────────────────────────────────────────────
def replace_handles(text: str, own: str, others: set[str]) -> str:
    """Replace handles deterministically: own → 'me', others → user_001…"""
    mapping: dict[str, str] = {}
    if own:
        mapping[own] = "me"
    for i, h in enumerate(sorted(others, key=str.casefold), 1):
        mapping[h] = f"user_{i:03d}"

    # Longest first so overlapping/partial handles replace correctly.
    for handle, alias in sorted(mapping.items(), key=lambda kv: -len(kv[0])):
        pattern = re.compile(
            r"(?<![A-Za-z0-9._@])" + re.escape(handle) + r"(?![A-Za-z0-9_])",
            re.IGNORECASE,
        )
        text = pattern.sub(alias, text)
    return text


def sanitize(text: str, export_dir: Path | None, keep_handles: bool) -> str:
    # Shorten the home directory before anything else (it contains the OS username).
    text = text.replace(str(Path.home()), "~")
    text = EMAIL_RE.sub(lambda m: m.group(0)[0] + "***@" + m.group(0).split("@")[1], text)
    text = PHONE_RE.sub(lambda m: "+" + "*" * (len(m.group(0)) - 1), text)
    text = IP_RE.sub(r"\1.***.***", text)
    text = DOB_LINE_RE.sub(r"\1****-**-**", text)
    text = NAME_LINE_RE.sub(r"\1***", text)
    text = EXPORT_FOLDER_RE.sub(r"\1***\2", text)

    if not keep_handles and export_dir:
        own, others = collect_handles(export_dir)
        text = replace_handles(text, own, others)
    return text


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Strip personal details from a text file (e.g. analyzer output).",
    )
    parser.add_argument("input", help="text file to sanitize, or '-' for stdin")
    parser.add_argument("-o", "--output", default="-", help="output file (default: stdout)")
    parser.add_argument(
        "--export-dir",
        help="export folder used to collect account handles "
        "(default: auto-detect next to this script or $INSTAGRAM_EXPORT_DIR)",
    )
    parser.add_argument(
        "--keep-handles",
        action="store_true",
        help="mask PII only; leave account handles untouched",
    )
    args = parser.parse_args()

    if args.input == "-":
        text = sys.stdin.read()
    else:
        text = Path(args.input).read_text(encoding="utf-8")

    result = sanitize(text, _find_export_dir(args.export_dir), args.keep_handles)

    if args.output == "-":
        sys.stdout.write(result)
    else:
        Path(args.output).write_text(result, encoding="utf-8")
        print(f"Sanitized output written to {args.output}")


if __name__ == "__main__":
    main()