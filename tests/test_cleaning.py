"""Tests for the data cleaning / curation pipeline (connections/cleaning.py)."""

from __future__ import annotations

from pathlib import Path

from connections.cleaning import (
    CleaningResult,
    clean_connection_sets,
    load_curated_followers,
    load_curated_nonfollowers,
    load_pending_requests,
    load_recently_unfollowed,
    load_restricted,
    promotion_set,
    write_curated_file,
    write_curate_template,
)
from connections.graph import ConnectionGraph

FIXTURE_EXPORT = (
    Path(__file__).parent
    / "fixtures/minimal_export/instagram-demo-2026-01-01-TEST01"
)


def _fixture_graph() -> ConnectionGraph:
    graph = ConnectionGraph.from_export_dir(FIXTURE_EXPORT)
    assert graph is not None
    return graph


def test_load_signal_files():
    assert load_pending_requests(FIXTURE_EXPORT) == {"dave_demo"}
    assert load_restricted(FIXTURE_EXPORT) == {"mallory_demo"}
    assert load_recently_unfollowed(FIXTURE_EXPORT) == {"frank_demo"}


def test_load_curated_followers_case_insensitive():
    # Fixture file lists EVE_DEMO in uppercase with comments.
    assert load_curated_followers(FIXTURE_EXPORT) == {"eve_demo"}


def test_clean_connection_sets_buckets():
    graph = _fixture_graph()
    # Raw claim: following {alice, bob, dave, eve} − followers {alice, bob, carol}
    assert graph.not_following_back == {"dave_demo", "eve_demo"}

    result = clean_connection_sets(graph)

    assert result.raw_not_following_back == {"dave_demo", "eve_demo"}
    assert result.pending_requests == {"dave_demo"}
    assert result.restricted == set()  # mallory_demo is not followed, so not in raw
    assert result.recently_unfollowed == set()  # frank_demo is not followed, so not in raw
    assert result.curated_confirmed == {"eve_demo"}  # case-insensitive match
    assert result.unverified == set()
    assert result.cleaned_not_following_back == set()


def test_clean_unverified_remainder(tmp_path):
    """An export with no signal files leaves the raw claim untouched."""
    graph = ConnectionGraph(
        followers={"alice"},
        following={"alice", "zed"},
        display={"zed": "zed"},
        export_dir=tmp_path,  # directory with no relationship/curated files
    )
    result = clean_connection_sets(graph)
    assert result.raw_not_following_back == {"zed"}
    assert result.unverified == {"zed"}


def test_clean_with_custom_curated_path(tmp_path):
    graph = _fixture_graph()
    curated = tmp_path / "my_curated.txt"
    curated.write_text("# confirmed in app\nDAVE_DEMO\n", encoding="utf-8")

    result = clean_connection_sets(graph, extra_curated_path=curated)
    assert result.curated_confirmed == {"dave_demo", "eve_demo"}
    assert result.unverified == set()


def test_main_connections_output_cleaned(capsys):
    import instagram_analysis as ia

    ia.main(["--export-dir", str(FIXTURE_EXPORT), "--section", "connections"])
    out = capsys.readouterr().out
    assert "Data cleaning" in out
    assert "Raw export claim          2" in out
    assert "Pending follow requests   −1" in out
    assert "Manually confirmed        −1" in out
    assert "Unverified remainder      0" in out
    assert "dave_demo" in out  # listed under pending follow requests


def test_promotion_set_confirmed_only_by_default():
    result = clean_connection_sets(_fixture_graph())
    assert promotion_set(result) == {"eve_demo"}
    # Fixture unverified set is empty, so assume_remainder changes nothing here.
    assert promotion_set(result, assume_remainder=True) == {"eve_demo"}


def test_promotion_set_includes_unverified_with_assume_flag(tmp_path):
    graph = ConnectionGraph(
        followers={"alice"},
        following={"alice", "zed"},
        display={},
        export_dir=tmp_path,
    )
    result = clean_connection_sets(graph)
    assert promotion_set(result) == set()
    assert promotion_set(result, assume_remainder=True) == {"zed"}


def test_write_curate_template(tmp_path):
    result = CleaningResult(unverified={"amy_demo", "zed_demo"})
    target = tmp_path / "curated_followers.txt"

    written = write_curate_template(result, target)
    text = written.read_text(encoding="utf-8")
    assert "# amy_demo" in text and "# zed_demo" in text

    # Commented handles are NOT treated as confirmed followers.
    assert load_curated_followers(tmp_path, extra_path=written) == set()

    # Refuses to overwrite an existing checklist.
    import pytest

    with pytest.raises(FileExistsError):
        write_curate_template(result, target)


def test_main_assume_mutual_promotes_to_mutuals(capsys):
    import instagram_analysis as ia

    ia.main(
        ["--export-dir", str(FIXTURE_EXPORT), "--section", "connections", "--assume-mutual"]
    )
    out = capsys.readouterr().out
    # Fixture: raw mutuals {alice, bob} + promoted {eve} = 3.
    assert "Mutuals incl. curation    3  (+1 confirmed + assumed (--assume-mutual))" in out
    assert "(+1 promoted — confirmed + assumed (--assume-mutual); raw export mutuals: 2)" in out
    assert "eve_demo" in out  # now listed under Mutuals


def test_main_bootstrap_curated(tmp_path, capsys):
    import instagram_analysis as ia

    target = tmp_path / "curated_followers.txt"
    ia.main(
        ["--export-dir", str(FIXTURE_EXPORT), "--bootstrap-curated", "--curated", str(target)]
    )
    out = capsys.readouterr().out
    assert "Checklist written" in out
    # Fixture unverified set is empty (dave pending, eve curated) — header only.
    text = target.read_text(encoding="utf-8")
    assert "verification checklist" in text

    # Refuses to overwrite.
    import pytest

    with pytest.raises(SystemExit):
        ia.main(
            ["--export-dir", str(FIXTURE_EXPORT), "--bootstrap-curated", "--curated", str(target)]
        )


# ── curation session ──────────────────────────────────────────────────────────


def test_curated_nonfollowers_loader(tmp_path):
    (tmp_path / "curated_nonfollowers.txt").write_text(
        "# marked doesn't follow back\nzed_demo\n", encoding="utf-8"
    )
    assert load_curated_nonfollowers(tmp_path) == {"zed_demo"}


def test_denied_handles_stay_in_ghost_list(tmp_path):
    graph = ConnectionGraph(
        followers={"alice_demo"},
        following={"alice_demo", "zed_demo", "yara_demo"},
        display={},
        export_dir=tmp_path,
    )
    (tmp_path / "curated_nonfollowers.txt").write_text("zed_demo\n", encoding="utf-8")

    result = clean_connection_sets(graph)
    assert result.curated_denied == {"zed_demo"}
    assert result.unverified == {"yara_demo"}
    # Denied handles remain listed as not-following-back — they are confirmed.
    assert result.cleaned_not_following_back == {"zed_demo", "yara_demo"}
    # ...but are never promoted, even with --assume-mutual.
    assert promotion_set(result, assume_remainder=True) == {"yara_demo"}


def test_write_curated_file_roundtrip(tmp_path):
    path = tmp_path / "curated_followers.txt"
    write_curated_file(path, {"amy_demo", "zed_demo"}, ["# header"])
    assert load_curated_followers(tmp_path, extra_path=path) == {"amy_demo", "zed_demo"}


def _mini_graph(tmp_path, following):
    return ConnectionGraph(
        followers={"alice_demo"},
        following={"alice_demo", *following},
        display={},
        export_dir=tmp_path,
    )


def _store(tmp_path):
    """A CurationStore rooted at tmp_path (same as the mini graph's export dir)."""
    from connections.curation_store import CurationStore

    return CurationStore.resolve(
        explicit_curated=None, export_dir=tmp_path, project_root=tmp_path
    )


def test_curation_session_answers(tmp_path):
    """Scripted input: 2 in-app figures, then y / n for the two unverified."""
    from curate_session import run_curation_session

    graph = _mini_graph(tmp_path, ["zed_demo", "yara_demo"])
    store = _store(tmp_path)
    answers = iter(["100", "3", "y", "n"])

    out = run_curation_session(
        graph,
        store,
        input_fn=lambda _prompt: next(answers),
        output_fn=lambda _msg: None,
    )

    # queue is alphabetical: yara_demo first, then zed_demo
    assert out["confirmed"] == {"yara_demo"}
    assert out["denied"] == {"zed_demo"}
    assert (tmp_path / "curated_followers.txt").read_text().strip().endswith("yara_demo")
    assert "zed_demo" in (tmp_path / "curated_nonfollowers.txt").read_text()

    # Files persist: a fresh cleaning pass sees the answers.
    result = clean_connection_sets(graph)
    assert result.curated_confirmed == {"yara_demo"}
    assert result.curated_denied == {"zed_demo"}
    assert result.cleaned_not_following_back == {"zed_demo"}


def test_curation_session_quit_saves_progress(tmp_path):
    from curate_session import run_curation_session

    graph = _mini_graph(tmp_path, ["zed_demo", "yara_demo", "ursa_demo"])
    answers = iter(["50", "4", "y", "s", "q"])  # figures, then y, skip, quit

    run_curation_session(
        graph,
        _store(tmp_path),
        input_fn=lambda _prompt: next(answers),
        output_fn=lambda _msg: None,
    )

    result = clean_connection_sets(graph)
    assert result.curated_confirmed == {"ursa_demo"}  # first alphabetically
    assert result.unverified == {"yara_demo", "zed_demo"}


def test_curation_session_assume_all(tmp_path):
    from curate_session import run_curation_session

    graph = _mini_graph(tmp_path, ["zed_demo", "yara_demo"])
    answers = iter(["50", "3", "a"])

    run_curation_session(
        graph,
        _store(tmp_path),
        input_fn=lambda _prompt: next(answers),
        output_fn=lambda _msg: None,
    )

    result = clean_connection_sets(graph)
    assert result.curated_confirmed == {"yara_demo", "zed_demo"}
    assert result.unverified == set()


def test_store_save_never_clobbers_existing_file(tmp_path):
    """The store guard never overwrites a non-empty confirmed file with empty."""
    from connections.curation_store import CurationStore

    store = CurationStore(root=tmp_path, export_dir=None)
    store.confirmed_path.write_text("# existing\ngood_handle\n", encoding="utf-8")

    outcome = store.save(set(), set(), meta={"app_followers": 10, "app_following": 2})

    assert outcome.confirmed_written is False
    assert outcome.skipped_existing == 1
    assert "good_handle" in store.confirmed_path.read_text(encoding="utf-8")


def test_curation_session_writes_meta(tmp_path):
    """The session persists the in-app figures for app-derived counts."""
    from connections.cleaning import load_curation_meta
    from curate_session import run_curation_session

    graph = _mini_graph(tmp_path, ["zed_demo"])
    answers = iter(["583", "402", "q"])

    run_curation_session(
        graph,
        _store(tmp_path),
        input_fn=lambda _prompt: next(answers),
        output_fn=lambda _msg: None,
    )

    meta = load_curation_meta([tmp_path])
    assert meta["app_followers"] == 583
    assert meta["app_following"] == 402

def test_store_resolve_default_is_export_dir(tmp_path):
    """Without an explicit --curated file, curation lives next to the export."""
    from connections.curation_store import CurationStore

    store = CurationStore.resolve(
        explicit_curated=None, export_dir=tmp_path, project_root=tmp_path
    )
    assert store.root == tmp_path


def test_store_resolve_zip_extraction_uses_per_export_cache(tmp_path, monkeypatch):
    """A temp-extracted --zip export stores curation in a stable per-export cache."""
    from connections.curation_store import CurationStore

    fake_home = tmp_path / "fakehome"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))

    temp_export = tmp_path / "ig-export-abc123"
    temp_export.mkdir()

    store = CurationStore.resolve(
        explicit_curated=None, export_dir=temp_export, project_root=tmp_path
    )
    # Root is under the fake cache dir, keyed by the export folder name.
    assert store.root == fake_home / ".cache" / "ig-analyzer" / "ig-export-abc123"


def test_migrate_legacy_curation(tmp_path):
    """One-time transition: copy repo-root curated state into the export store."""
    from connections.curation_store import (
        CurationStore,
        CURATED_FILE_NAME,
        CURATION_META_FILE_NAME,
        migrate_legacy_curation,
    )

    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / CURATED_FILE_NAME).write_text("amy_demo\n", encoding="utf-8")
    (legacy / CURATION_META_FILE_NAME).write_text(
        '{"app_followers": 583}', encoding="utf-8"
    )

    export = tmp_path / "export"
    export.mkdir()
    store = CurationStore.resolve(
        explicit_curated=None, export_dir=export, project_root=tmp_path
    )
    assert store.root == export

    moved = migrate_legacy_curation(store, legacy)
    assert moved == 2
    assert (export / CURATED_FILE_NAME).exists()
    assert (export / CURATION_META_FILE_NAME).exists()

    # Never overwrites an existing curated file (data-loss guard).
    (legacy / CURATED_FILE_NAME).write_text("other_handle\n", encoding="utf-8")
    assert migrate_legacy_curation(store, legacy) == 0
    assert "amy_demo" in (export / CURATED_FILE_NAME).read_text(encoding="utf-8")


def _mini_graph_for_state(following):
    """Minimal graph for state-machine tests (no filesystem needed)."""
    from connections.graph import ConnectionGraph

    return ConnectionGraph(followers={"alice_demo"}, following={"alice_demo", *following})


def test_curation_state_transitions():
    """CurationState extracts the session state machine (ADR-0006)."""
    from curate_session import CurationState

    state = CurationState(graph=_mini_graph_for_state(["zed_demo", "yara_demo"]))
    assert state.remaining == ["yara_demo", "zed_demo"]  # sorted

    assert state.record_yes() == "yara_demo"
    assert state.confirmed == {"yara_demo"}
    assert state.answered == 1

    assert state.record_no() == "zed_demo"
    assert state.denied == {"zed_demo"}
    assert state.remaining == []
    assert state.done is True
    assert state.estimate_followers == 2  # 1 export follower + 1 confirmed


def test_curation_state_apply_decisions():
    """Non-interactive driver applies a {handle: bool} decision map."""
    from curate_session import CurationState

    state = CurationState(graph=_mini_graph_for_state(["zed_demo", "yara_demo"]))
    decisions = {"yara_demo": True, "zed_demo": False, "missing_demo": True}
    applied = state.apply_decisions(decisions)
    assert applied == 2  # missing_demo isn't in the queue
    assert state.confirmed == {"yara_demo"}
    assert state.denied == {"zed_demo"}


def test_curation_state_assume_all():
    """Bulk 'a' promotes the entire remaining queue."""
    from curate_session import CurationState

    state = CurationState(graph=_mini_graph_for_state(["zed_demo", "yara_demo", "bob_demo"]))
    assumed = state.assume_all()
    assert assumed == 3
    assert state.confirmed == {"zed_demo", "yara_demo", "bob_demo"}
    assert state.done is True


def test_run_curation_batch_persists_non_interactive(tmp_path):
    """Batch driver: apply machine answers, no prompts, state saved."""
    from curate_session import run_curation_batch

    graph = _mini_graph_for_state(["zed_demo", "yara_demo"])
    store = _store(tmp_path)

    state = run_curation_batch(
        graph,
        store,
        decisions={"yara_demo": True, "zed_demo": False},
        app_followers=583,
        app_following=402,
    )
    assert state.confirmed == {"yara_demo"}
    assert state.denied == {"zed_demo"}

    # Answers are persisted to the store.
    snap = store.load()
    assert snap.confirmed == {"yara_demo"}
    assert snap.denied == {"zed_demo"}


def test_app_derived_reconciliation(tmp_path, capsys, monkeypatch):
    """Summary derives one-way counts from in-app totals vs curated mutuals."""
    import instagram_analysis as ia
    from connections.cleaning import write_curation_meta

    confirmed_target = tmp_path / "curated_followers.txt"
    write_curation_meta(tmp_path / "curation_meta.json", 583, 402)

    ia.main(
        [
            "--export-dir", str(FIXTURE_EXPORT),
            "--section", "connections",
            "--curated", str(confirmed_target),
        ]
    )
    out = capsys.readouterr().out
    # Fixture: 3 curated mutuals (2 raw + eve promoted).
    assert "583 followers / 402 following vs 3 mutuals" in out
    assert "402 − 3 = 399" in out
    assert "583 − 3 = 580" in out


def test_main_curate_flag(tmp_path, capsys, monkeypatch):
    """--curate drives the wizard from the CLI and prints the curated report."""
    import instagram_analysis as ia

    answers = iter(["100", "3", "a"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))

    confirmed_target = tmp_path / "curated_followers.txt"
    ia.main(
        [
            "--export-dir", str(FIXTURE_EXPORT),
            "--curate",
            "--curated", str(confirmed_target),
        ]
    )
    out = capsys.readouterr().out
    assert "Interactive curation session" in out
    assert "Session summary" in out
    # eve was already curated in the fixture; 'a' confirms nothing new
    assert "Mutuals incl. curation    3" in out
    assert confirmed_target.exists()


def test_zip_export_path(tmp_path):
    """A Meta-style ZIP is extracted and the export root found inside it."""
    import zipfile

    from export_paths import resolve_export_dir

    zip_file = tmp_path / "instagram-demo-2026-01-01-TEST01.zip"
    with zipfile.ZipFile(zip_file, "w") as zf:
        for file in FIXTURE_EXPORT.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(FIXTURE_EXPORT.parent))

    root = resolve_export_dir(zip_path=zip_file)
    assert root.name == "instagram-demo-2026-01-01-TEST01"
    assert (root / "connections/followers_and_following/following.json").is_file()

    graph = ConnectionGraph.from_export_dir(root)
    assert graph is not None
    assert len(graph.following) == 4
