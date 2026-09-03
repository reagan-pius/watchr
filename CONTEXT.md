# CONTEXT — Domain glossary

Vocabulary for Watchr. Use these names in code, docs,
and architecture discussions. See `docs/adr/` for recorded decisions.

- **Export snapshot** — one Instagram data download (folder or ZIP as delivered
  by Meta). Immutable input; analyzed via `export_paths.resolve_export_dir()`.
- **ConnectionGraph** — follower/following handle sets derived from an export
  snapshot (`connections/graph.py`). Also carries the app-reported follower
  total from audience insights.
- **Cleaning result** (`CleaningResult`) — the raw "following − followers"
  claim reclassified with every in-export signal: pending follow requests,
  restricted profiles, recently unfollowed, curated confirmations/denials.
  Buckets: pending / restricted / unfollowed / curated-confirmed / denied /
  **unverified remainder**.
- **Curated followers (confirmed)** — handles the user verified follow them
  back; promoted into the followers side.
- **Denied (non-followers)** — handles the user confirmed do NOT follow back;
  they stay in the 👻 list and are never re-asked or promoted.
- **Promotion** — adding curated-confirmed handles (and, under the explicit
  `--assume-mutual` policy, the unverified remainder) to the followers side so
  they appear as mutuals. Denied handles are never promoted.
- **Curation session** — the interactive wizard (`curate_session.py`) that
  asks for in-app totals and walks the user through unverified accounts.
- **Curation store** — the single owner of curated state on disk:
  `curated_followers.txt`, `curated_nonfollowers.txt`, `curation_meta.json`.
- **App-derived counts** — one-way follow totals computed from in-app figures
  vs curated mutuals (following − mutuals; app followers − mutuals). Counts
  only; the export cannot name the accounts.
- **AnalyzerContext** — one immutable value holding a run's configuration
  (export dir, redaction, curated path override, assume-mutual policy,
  ads list limit).
- **ConnectionsInsights** — the compute-once value consumed by report
  renderers: graph + cleaning result + promotion + derived counts.
- **AdsInsights** — compute-once ads/tracking value (inventory, advertisers +
  audience-type flags, interests/categories, engagement, preferences,
  off-Instagram apps). See ADR-0007.
- **ActivityInsights** / **SecurityInsights** / **MessagesInsights** /
  **AppsInsights** / **ContactsInsights** / **ShoppingInsights** /
  **PreferencesInsights** — same compute-once pattern for other export
  domains. Messages never include DM bodies.
- **Export inventory** — present / missing / empty status for logical file
  groups with Meta path aliases (`export_inventory.py`).

## Architecture review — curation state placement

Two candidates were evaluated for where curation state lives. **Candidate 5 (per-export
root via `CurationStore.resolve`)** was adopted; **Candidate 1 (repository-root `curated_followers.txt`)**
was rejected because it lets a fresh clone inherit another user's curation and conflates a
single export with repo-local state.

- Default curation lives at the export folder.
- Temp-extracted `--zip` exports use a stable per-export cache (`~/.cache/watchr/<name>`)
  so curation survives across runs of the same ZIP.
- `--curated FILE` overrides the root to the file's parent.
- Reads are unioned with export-embedded copies when the cache root differs from the export dir.

Accepted by ADR-0002 (addendum) and ADR-0006. The legacy repo-root state is migrated once
into the export store via `migrate_legacy_curation` (skipped inside `--check` and the test tree).
