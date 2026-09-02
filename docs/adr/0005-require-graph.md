# ADR-0005: Uniform missing-data handling for connections reports

Status: Accepted and implemented (via `_connections`)

## Context
Connections report paths handled missing graph/data inconsistently.

## Decision
Use `_connections(ctx)` as the single guard for connection graph availability.
When required files are missing, it prints one diagnostic and returns `None`.
Section functions early-return on that shared result.

`load()` and `load_first()` support quiet mode so callers do not invoke loaders
only for print side effects.

## Consequences
- One missing-data behavior for all connections sections.
- Simpler report code with consistent early-return semantics.
