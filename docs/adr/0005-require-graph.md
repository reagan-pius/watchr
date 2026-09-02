# ADR-0005: One missing-data guard for report sections

Status: Accepted (design) — implementation pending go-ahead

## Context
Report functions handle a missing ConnectionGraph four different ways; one
loads two JSON files and discards the data purely to reuse `load()`'s error
printing.

## Decision
`_require_graph(ctx) -> ConnectionGraph | None` owns the missing-files
diagnostic. `load()` / `load_first()` gain a quiet mode so callers never
invoke them for their print side effects.

## Consequences
- One diagnostic, tested once; report sections stay uniform.
