# ADR-0003: Compute-once ConnectionsInsights per run

Status: Accepted and implemented (with renderer scope adjustment)

## Context
Connection reports repeatedly recomputed the same graph/cleaning pipeline,
which risked inconsistencies and unnecessary file reads.

## Decision
Build `ConnectionsInsights` once per run context (graph + cleaning result +
promotion set + effective graph + derived counts) and reuse it across
connections report sections.

The original "pure `insights -> str` renderers" idea was narrowed: report
functions still print directly, but they consume a shared compute-once value.

## Consequences
- Connection sections remain consistent within one run.
- Expensive connection derivations run once per context.
- Future structured output can still reuse `ConnectionsInsights`.
