# ADR-0002: CurationStore is the single owner of curated state files

Status: Accepted (design) — implementation pending go-ahead

## Context
`curated_followers.txt`, `curated_nonfollowers.txt`, and `curation_meta.json`
were read and written from three modules with four different path-resolution
rules. This caused an actual data-loss incident: the curation wizard rewrote
`curated_followers.txt` from an empty in-memory set because writer and reader
disagreed about the file location. A data-loss guard was added as a patch.

## Decision
A `CurationStore` rooted at one directory owns all three files: `load() ->
CurationSnapshot(confirmed, denied, meta)`, `save(...)` (the clobber guard
lives inside the store, protecting every writer), `write_checklist(handles)`.
Root is resolved once by `CurationStore.resolve` (per-export, see below); the
wizard and reports both receive the store, and no other module knows the file
names.

## Root resolution (addendum) -- per-export, never repository-global
1. `--curated FILE`'s parent directory, else
2. the export folder itself (`--export-dir` / `--zip` target), else
3. a stable per-export cache `~/.cache/ig-analyzer/<export-name>` for a
   temp-extracted `--zip` run, so curation survives across runs of the same ZIP.

Reads are unioned with export-embedded copies of the same files when the
cache root differs from the export folder, so a handle answered in an earlier
run is never lost. Curation state is therefore per-export and per-user: the
files are gitignored, and a fresh clone starts with an empty, clean slate. A
one-time `migrate_legacy_curation` copies any pre-existing repo-root curated
files into the export store (skipped under `--check` and in the test tree).

## Consequences
- Silent curated-state loss becomes unrepresentable (no second writer).
- File-layout knowledge is tested once via `save() → load()` round-trips.
