"""Tests for the Instagram export analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from connections.graph import ConnectionGraph, _load_follower_entries, _load_following_entries
from export_paths import find_export_root, is_export_root, resolve_export_dir
from setup_check import run_setup_check

FIXTURE_EXPORT = (
    Path(__file__).parent
    / "fixtures/minimal_export/instagram-demo-2026-01-01-TEST01"
)


def test_fixture_is_valid_export_root():
    assert is_export_root(FIXTURE_EXPORT)


def test_find_export_root_nested():
    base = FIXTURE_EXPORT.parent
    assert find_export_root(base) == FIXTURE_EXPORT


def test_raw_json_entry_counts():
    assert len(_load_follower_entries(FIXTURE_EXPORT)) == 3
    assert len(_load_following_entries(FIXTURE_EXPORT)) == 4


def test_connection_graph_fixture():
    graph = ConnectionGraph.from_export_dir(FIXTURE_EXPORT)
    assert graph is not None
    assert len(graph.followers) == 3
    assert len(graph.following) == 4
    assert len(graph.mutuals) == 2
    assert len(graph.not_following_back) == 2
    assert len(graph.not_followed_back) == 1
    assert graph.app_follower_count == 10
    assert graph.followers_incomplete is True


def test_resolve_export_dir_explicit():
    root = resolve_export_dir(export_dir=FIXTURE_EXPORT)
    assert root == FIXTURE_EXPORT


def test_setup_check_passes_on_fixture(capsys):
    code = run_setup_check(FIXTURE_EXPORT)
    out = capsys.readouterr().out
    assert code == 0
    assert "Ready" in out
    assert "3 raw JSON entries" in out
    assert "4 raw JSON entries" in out


def test_setup_check_fails_without_export(tmp_path, capsys):
    code = run_setup_check(tmp_path)
    out = capsys.readouterr().out
    assert code == 1
    assert "Not ready" in out


def test_main_check_flag(capsys):
    import instagram_analysis as ia

    with pytest.raises(SystemExit) as exc:
        ia.main(["--check", "--export-dir", str(FIXTURE_EXPORT)])
    assert exc.value.code == 0
    assert "Ready" in capsys.readouterr().out


def test_main_section_connections_only(capsys):
    import instagram_analysis as ia

    ia.main(["--export-dir", str(FIXTURE_EXPORT), "--section", "connections"])
    out = capsys.readouterr().out
    assert "Connection summary" in out
    assert "Mutuals" in out
    assert "Posts by month" not in out


def test_main_output_file(tmp_path):
    import instagram_analysis as ia

    out_file = tmp_path / "report.txt"
    ia.main(
        [
            "--export-dir",
            str(FIXTURE_EXPORT),
            "--section",
            "profile",
            "--output",
            str(out_file),
        ]
    )
    text = out_file.read_text(encoding="utf-8")
    assert "Your profile info" in text
    assert "demo_user" in text
