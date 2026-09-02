# ADR-0004: Promotion is a graph operation via ConnectionGraph.with_promoted()

Status: Accepted (design) — implementation pending go-ahead

## Context
The `promotion_set` docstring claims promoted handles are "added to
`graph.followers`", but nothing mutates the graph: two call sites hand-union
`graph.mutuals | promoted`. The docstring is false and the promotion
semantics (denied handles never promoted; assume-mutual policy) live at call
sites.

## Decision
`ConnectionGraph.with_promoted(promoted) -> ConnectionGraph` returns a copy
with `followers |= promoted`. Call sites use the effective graph; downstream
properties (`mutuals`, `not_following_back`, `not_followed_back`) reflect
promotion automatically. Denied handles are never members of the promoted
set, so they cannot leak into mutuals.

## Consequences
- One definition of promotion; the docstring becomes true.
- The 👻 list remains CleaningResult-driven (see ADR-0003 nuance).
