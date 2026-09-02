# ADR-0006: Extract `CurationState` from the session

Status: Accepted

## Context
All curation-session state originally lived closure-local inside
`run_curation_session()` (see the pre-ADR code). The session already persisted
via `CurationStore` (ADR-0002) and the injected `input_fn`/`output_fn` seams
made the interactive loop testable, but there was no way to drive the same
state machine non-interactively.

## Decision
Extract the mutable session state into a `CurationState` dataclass in
`curate_session.py`:

- `from_snapshot(graph, store)` seeds confirmed/denied/queue from a persisted
  `CurationStore`, so the session is resumable.
- `__post_init__` lets the same class be built directly from a graph (used by
  the unit tests and the non-interactive path).
- The state machine exposes the `record_yes` / `record_no` / `skip` /
  `assume_all` / `apply_decisions` transitions, so the interactive loop in
  `run_curation_session()` is a thin shell.
- A second driver now exists: `run_curation_batch(graph, store, decisions)`,
  which applies a machine-readable `{handle: follows_back}` map and persists
  through the same store — closing the second-driver requirement.

## Consequences
- The state machine is reusable by future drivers (CLI batch, API, tests)
  without re-deriving confirmed/denied/queue each time.
- `run_curation_session` stays focused on I/O orchestration and progress
  messaging.
- No speculative complexity added to the store layer; the store remains the
  single owner of the on-disk files.
