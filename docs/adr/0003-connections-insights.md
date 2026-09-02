# ADR-0003: Compute-once ConnectionsInsights; renderers are pure

Status: Accepted (design) — implementation pending go-ahead

## Context
The three connection report functions each call the cleaning pipeline
uncached: one `--section connections` run re-reads five files and re-computes
all set arithmetic three times. If curated files change between calls the
sections silently disagree. The only observable output is `print()`, so tests
assert on formatted strings.

## Decision
Build a `ConnectionsInsights` value once per run (graph + cleaning result +
promotion set + effective graph + app-derived counts + source label). Report
functions become pure `insights -> str` renderers; printing happens once at
the edge in `run_reports()`.

## Consequences
- Consistency by construction across report sections.
- The 📐 derived-count math (following − mutuals; app followers − mutuals) is
  unit-testable as a value property.
- A structured output mode (`--output json`) requires no new computation.
- Nuance: the effective (promoted) graph drives summary/mutuals; the 👻 list
  remains driven by the CleaningResult (unverified ∪ denied) so that pending
  and restricted accounts never reappear in it.
