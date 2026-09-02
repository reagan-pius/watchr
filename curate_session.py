"""
Interactive curation session + state.
=====================================

The export's follower list is often incomplete, so the raw "don't follow
back" claim cannot be trusted. This wizard closes the gap by asking the user
direct questions and persisting the answers, iterating until the curated
numbers resemble the figures shown in the Instagram app:

1.  Asks for the follower/following totals the app displays (defaults come
    from the export's own insights, when present).
2.  Walks through every unverified account from the cleaned ghost list in
    small batches: *does @handle follow you back?*  Answers:

         y  yes, they follow me back    -> promoted into Mutuals
         n  no, they don't              -> stays in the ghost list, never re-asked
         s  skip / decide later
         a  assume ALL remaining follow back (bulk answer)
         q  quit (progress already saved)
         ?  help

3.  After every batch the answers are persisted through the CurationStore
    (ADR-0002) and a live comparison is printed: curated estimate vs the
    in-app totals -- the loop's exit condition.

All session state lives in ``CurationState`` (ADR-0006), so the interactive
loop is a thin shell and the same state machine can be driven non-interactively
(machine-readable answers via ``CurationState.apply_decisions`` /
``run_curation_batch``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping

from connections.cleaning import clean_connection_sets
from connections.curation_store import CurationStore
from connections.graph import ConnectionGraph

BATCH_SIZE = 25

_PROMPT_HELP = (
    "    y = follows me back | n = doesn't | s = skip/unsure | "
    "a = assume all remaining | q = quit | ? = help"
)


@dataclass
class CurationState:
    """Mutable session state, extracted from the loop so the session can be
    paused, inspected, or driven programmatically (ADR-0006)."""

    graph: ConnectionGraph
    confirmed: set[str] = field(default_factory=set)
    denied: set[str] = field(default_factory=set)
    queue: list[str] = field(default_factory=list)
    pos: int = 0
    app_followers: int | None = None
    app_following: int | None = None
    newly_confirmed: int = 0
    newly_denied: int = 0
    answered: int = 0
    display: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_snapshot(
        cls, graph: ConnectionGraph, store: CurationStore
    ) -> "CurationState":
        """Seed state from persisted stores: confirmed/denied already answered,
        queue = the current unverified remainder."""
        snapshot = store.load()
        result = clean_connection_sets(graph, snapshot=snapshot)
        return cls(
            graph=graph,
            confirmed=set(snapshot.confirmed),
            denied=set(snapshot.denied),
            queue=sorted(result.unverified),
            display=dict(graph.display),
        )

    def __post_init__(self) -> None:
        """Allow a state built directly from a graph (no persisted snapshot) to
        still derive its display map and unverified queue. ``from_snapshot``
        supplies these explicitly, so this only fills in what's missing."""
        if not self.display:
            self.display = dict(self.graph.display)
        if not self.queue:
            result = clean_connection_sets(
                self.graph,
                snapshot=type("S", (), {"confirmed": self.confirmed, "denied": self.denied})(),
            )
            self.queue = sorted(result.unverified)

    # -- query ---------------------------------------------------------------
    @property
    def remaining(self) -> list[str]:
        return self.queue[self.pos:]

    @property
    def next_handle(self) -> str | None:
        return self.queue[self.pos] if self.pos < len(self.queue) else None

    @property
    def done(self) -> bool:
        return self.pos >= len(self.queue)

    @property
    def estimate_followers(self) -> int:
        return len(self.graph.followers) + len(self.confirmed)

    @property
    def estimate_mutuals(self) -> int:
        return len(self.graph.mutuals) + len(self.confirmed)

    def show(self, handle: str) -> str:
        return self.display.get(handle, handle)

    # -- transitions ---------------------------------------------------------
    def record_yes(self) -> str | None:
        h = self.next_handle
        if h is None:
            return None
        self.confirmed.add(h)
        self.newly_confirmed += 1
        self.answered += 1
        self.pos += 1
        return h

    def record_no(self) -> str | None:
        h = self.next_handle
        if h is None:
            return None
        self.denied.add(h)
        self.newly_denied += 1
        self.answered += 1
        self.pos += 1
        return h

    def skip(self) -> None:
        if not self.done:
            self.pos += 1

    def assume_all(self) -> int:
        """Promote the whole remaining queue; returns how many were assumed."""
        rest = self.remaining
        self.confirmed.update(rest)
        self.newly_confirmed += len(rest)
        self.answered += len(rest)
        self.pos = len(self.queue)
        return len(rest)

    def apply_decisions(self, decisions: Mapping[str, bool]) -> int:
        """Non-interactive driver: apply {canonical_handle: follows_back} to the
        remaining queue in order. Unknown handles are left in the queue.
        Returns the number of decisions applied."""
        applied = 0
        for handle in list(self.queue[self.pos:]):
            decision = decisions.get(handle)
            if decision is None:
                continue
            if decision:
                self.record_yes()
            else:
                self.record_no()
            applied += 1
        return applied


def run_curation_batch(
    graph: ConnectionGraph,
    store: CurationStore,
    decisions: Mapping[str, bool],
    app_followers: int | None = None,
    app_following: int | None = None,
) -> CurationState:
    """Non-interactive curation: apply machine-readable answers and persist.

    ``decisions`` maps a canonical handle to True (follows back) or False.
    Handles already answered in the store are untouched.
    Returns the resulting (persisted) state.
    """
    state = CurationState.from_snapshot(graph, store)
    state.app_followers = app_followers
    state.app_following = app_following
    state.apply_decisions(decisions)
    store.save(
        state.confirmed,
        state.denied,
        {"app_followers": app_followers, "app_following": app_following},
    )
    return state


def _ask_int(
    prompt: str,
    default: int | None,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> int | None:
    """Ask for an integer, accepting blank = default. Returns None on refusal."""
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input_fn(f"{prompt}{suffix}: ").strip().replace(",", "")
        if not raw and default is not None:
            return default
        try:
            return int(raw)
        except ValueError:
            output_fn(f"  Please enter a number (or press Enter for {default}).")


def _ask_follow_back(
    handle: str,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> str:
    """Prompt until a recognized answer is given. Returns the answer letter."""
    while True:
        answer = input_fn(
            f"  Does @{handle} follow you back? [y/n/s/a/q/?] "
        ).strip().lower()
        if answer in {"y", "n", "s", "a", "q", ""}:
            return answer
        output_fn(_PROMPT_HELP)


def run_curation_session(
    graph: ConnectionGraph,
    store: CurationStore,
    input_fn: Callable[[str], str] | None = None,
    output_fn: Callable[[str], None] | None = None,
) -> dict:
    """Run the interactive curation loop, persisting answers via ``store``.

    ``input_fn`` / ``output_fn`` default to ``input`` / ``print``, resolved at
    call time so tests can monkeypatch them. The loop is a thin shell over
    ``CurationState`` (ADR-0006).

    Returns a dict with the final ``confirmed`` / ``denied`` handle sets.
    """
    input_fn = input_fn or input
    output_fn = output_fn or print
    state = CurationState.from_snapshot(graph, store)
    queue_len = len(state.queue)

    output_fn("\nInteractive curation session")
    output_fn("=" * 28)
    output_fn(
        "The export's follower list is incomplete, so the only way to get accurate\n"
        "numbers is to ask you. First, two reference figures from the Instagram app:"
    )

    state.app_followers = _ask_int(
        "Followers count shown in your app",
        graph.app_follower_count,
        input_fn,
        output_fn,
    )
    state.app_following = _ask_int(
        "Following count shown in your app",
        len(graph.following),
        input_fn,
        output_fn,
    )

    def save() -> None:
        outcome = store.save(
            state.confirmed,
            state.denied,
            {
                "app_followers": state.app_followers,
                "app_following": state.app_following,
            },
        )
        if not outcome.confirmed_written:
            output_fn(
                f"   [!] Skipped writing {store.confirmed_path.name}: session has no "
                "confirmations but the file already contains "
                f"{outcome.skipped_existing} handles (data-loss guard)."
            )

    def show_status() -> None:
        followers = state.estimate_followers
        output_fn("\n   -- curated vs in-app --------")
        output_fn(
            f"   Followers  export {len(state.graph.followers)} + confirmed "
            f"{len(state.confirmed)} ~ {followers}"
            + (
                f"   (app: {state.app_followers})"
                if state.app_followers is not None
                else ""
            )
        )
        output_fn(
            f"   Answered {state.answered}, unverified left: {queue_len - state.answered}"
        )

    save()  # persist state even when there is nothing to ask

    stop = False
    while not state.done and not stop:
        batch_start = state.pos
        batch_end = min(state.pos + BATCH_SIZE, queue_len)
        output_fn(
            f"\nBatch {batch_start // BATCH_SIZE + 1}: accounts "
            f"{batch_start + 1}-{batch_end} of {queue_len}  (y/n/s/a/q, ? = help)"
        )
        while state.pos < batch_end and not stop:
            handle = state.next_handle
            assert handle is not None
            answer = _ask_follow_back(state.show(handle), input_fn, output_fn)
            if answer == "y":
                state.record_yes()
            elif answer == "n":
                state.record_no()
            elif answer == "a":
                assumed = state.assume_all()
                stop = True
                output_fn(
                    f"  -> assumed the remaining {assumed} follow you back "
                    "(revisit anytime: move handles from curated_followers.txt "
                    "to curated_nonfollowers.txt)."
                )
            elif answer == "q":
                stop = True
            else:  # skip / blank
                state.skip()
        save()
        show_status()

    output_fn("\nSession summary")
    output_fn("=" * 15)
    output_fn(f"   Newly confirmed (follow back): {state.newly_confirmed}")
    output_fn(f"   Newly denied (don't follow):   {state.newly_denied}")
    output_fn(f"   Left for later:                {queue_len - state.answered}")

    est_followers = state.estimate_followers
    if state.app_followers is not None:
        delta = est_followers - state.app_followers
        match = (
            "matches"
            if abs(delta) <= max(2, round(state.app_followers * 0.01))
            else "differs from"
        )
        output_fn(
            f"   Curated follower estimate {est_followers} {match} "
            f"the app's {state.app_followers} (delta {delta:+d})."
        )
    output_fn(
        f"   Answers saved to {store.confirmed_path.name} / {store.denied_path.name}"
    )
    output_fn("   Re-run the report to see the curated numbers in place.")

    return {"confirmed": set(state.confirmed), "denied": set(state.denied)}
