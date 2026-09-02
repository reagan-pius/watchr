# ADR-0004: Promotion is a graph operation via `ConnectionGraph.with_promoted()`

Status: Accepted and implemented

## Context
Promotion semantics (curated-confirmed, optional assume-mutual) were previously
spread across call sites and docs.

## Decision
`ConnectionGraph.with_promoted(promoted)` returns a copy with promoted handles
added to `followers`. Call sites use the effective graph so `mutuals` and
related properties reflect promotion consistently.

Denied handles are never promoted.

## Consequences
- One promotion definition in one place.
- Clear separation between effective mutuals and cleaning-driven ghost list.
