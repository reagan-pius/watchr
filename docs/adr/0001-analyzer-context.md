# ADR-0001: AnalyzerContext replaces module-global configuration

Status: Accepted and implemented

## Context
`instagram_analysis.py` used mutable module globals
(`BASE_DIR`, `REDACT`, `_connections_cache`, `_curated_path`, `_assume_mutual`).
`BASE_DIR` was resolved at import time with different logic than
`export_paths.resolve_export_dir()`. This made tests and repeated in-process
runs fragile.

## Decision
Use one frozen `AnalyzerContext` dataclass (`context.py`) built in `main()`
and passed explicitly to report functions. Import-time export resolution is
removed; `resolve_export_dir()` is the single resolution path.

## Consequences
- Report functions take `ctx`; no function reads runtime globals.
- Repeated in-process calls are isolated (`main()` clears `_connections_cache`).
- The context is the natural cache key for compute-once behavior (ADR-0003).
