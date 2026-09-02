# ADR-0001: AnalyzerContext replaces module-global configuration

Status: Accepted (design) — implementation pending go-ahead

## Context
`instagram_analysis.py` configures runs through five mutable module globals
(`BASE_DIR`, `REDACT`, `_graph_cache`, `_curated_path`, `_assume_mutual`).
`BASE_DIR` is resolved at import time with different logic than
`export_paths.resolve_export_dir()`. State leaks across in-process runs
(`--no-redact` is never restored) and tests can only configure the tool via
`main()`.

## Decision
One frozen `AnalyzerContext` dataclass (`context.py`) built in `main()` and
passed explicitly to every report function. Import-time export resolution is
deleted; `resolve_export_dir()` is the single resolution path.

## Consequences
- Report functions take `ctx`; no function reads a global.
- In-process runs are isolated; tests construct contexts directly.
- The context is the natural cache key for compute-once (ADR-0003).
