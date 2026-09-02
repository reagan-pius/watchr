# ADR-0002: CurationStore is the single owner of curated state files

Status: Accepted and implemented

## Context
`curated_followers.txt`, `curated_nonfollowers.txt`, and `curation_meta.json`
were previously read and written from multiple modules with conflicting
path-resolution rules. This caused curated-state mismatches and a data-loss
incident.

## Decision
`CurationStore` owns all three files:
- `load() -> CurationSnapshot(confirmed, denied, meta)`
- `save(...)` with data-loss guard
- `write_checklist(handles)`

Root is resolved once by `CurationStore.resolve`:
1. `--curated FILE` parent directory
2. export folder (`--export-dir` / `--zip` target)
3. per-export cache `~/.cache/watchr/<export-name>` for temp `--zip` extraction

## Migration Rules
- `migrate_legacy_curation(...)` migrates old repo-root curated files into the
  export store (skipped under `--check` and in test exports).
- `migrate_legacy_cache(...)` migrates old ZIP cache data from
  `~/.cache/ig-analyzer/<export>` to `~/.cache/watchr/<export>` and removes
  migrated legacy files.

## Consequences
- Curated-state ownership is centralized and testable.
- Silent curated-state loss from path disagreements is prevented.
- Rebrand migration keeps prior user curation intact.
