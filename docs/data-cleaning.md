# Data cleaning & curation

Why the raw "👻 People you follow who DON'T follow you back" list needs cleaning,
what the analyzer does about it, and how to curate it manually.

## The problem

The raw list is computed as `following − followers` from the export's JSON files.
Two things make that raw claim unreliable:

1. **Incomplete follower files.** Instagram's download reliably includes the
   full *following* list, but the *followers* list is frequently truncated —
   sometimes to a small fraction of the real total. Example snapshot:
   402 following in export, 59 followers in export, 583 followers reported by
   the app (≈10% coverage). Every follower missing from the JSON who is also
   followed by you lands in the raw "don't follow back" list as a **false
   positive**, even though they are a real mutual.
2. **Pending follow requests.** Accounts you have requested but who have not
   accepted yet appear in `following.json`. They *cannot* follow back by
   definition, so counting them as "not following back" is misleading.

## The cleaning pipeline (`connections/cleaning.py`)

The analyzer reclassifies the raw claim using every signal available inside the
export, in this order:

| Step | Signal file | Effect on the raw list |
|------|-------------|------------------------|
| 1 | `recent_follow_requests.json` | Moved to a separate **⏳ pending requests** bucket |
| 2 | `restricted_profiles.json` | Removed (relationship deliberately muted) |
| 3 | `recently_unfollowed_profiles.json` | Removed (stale entries) |
| 4 | `curated_followers.txt` (manual) | Removed — you confirmed they follow back |
| — | remainder | **Unverified**: the curated 👻 list |

The report prints a `🧹 Data cleaning` block showing every subtraction, so the
numbers stay auditable: raw claim → each bucket removed → unverified remainder.

## Manual curation workflow

When follower coverage is low, the unverified remainder will still contain
mostly false positives — no file in the ZIP can prove who follows you. The fix
is a small, human-verified allowlist:

1. Open the 👻 list and check each account in the Instagram app
   (their profile → *Following* → search your handle).
2. Add every account that really follows you to **`curated_followers.txt`**:

   ```
   # Handles confirmed to follow me back (verified in the app, 2026-04)
   eve_demo
   some_other_user
   ```

   One handle per line, `#` starts a comment, matching is case-insensitive.
3. Re-run the analyzer. Confirmed handles are subtracted and shown as
   "Manually confirmed −N".

Where the files are looked up, in order (see ADR-0002):

- `--curated FILE` (explicit path) — root is the file's parent directory, else
- the export folder itself (the resolved `--export-dir` / `--zip` target), else
- for a temp-extracted `--zip` run, a stable per-export cache at
  `~/.cache/ig-analyzer/<export-name>` so curation survives across runs of the
  same ZIP.

Either way the three files (`curated_followers.txt`,
`curated_nonfollowers.txt`, `curation_meta.json`) live **next to your export**
and are **per-user / gitignored** — a fresh clone starts with no curated state
so everyone curates their own data independently.

## Promoting confirmed mutuals into the Mutuals list

Accounts that are verified to follow you back are **promoted into the
followers set**, so they appear under 🤝 **Mutuals** ("people you follow AND
who follow you") — not merely omitted from the 👻 list. The summary shows both
numbers: raw export mutuals and `Mutuals incl. curation (+N …)`.

Three ways to promote, from safest to most assertive:

1. **Manual curation** — add verified handles to `curated_followers.txt`
   (uncommented). They are promoted on every run.
2. **`--bootstrap-curated`** — writes a commented checklist of all unverified
   handles to `curated_followers.txt`:

   ```bash
   python3 instagram_analysis.py --bootstrap-curated
   ```

   Verify each account in the app, delete the leading `# ` on the ones that
   follow you, then re-run the report. Commented lines are never promoted.
3. **`--assume-mutual`** — explicit policy flag: the *entire* unverified
   remainder is promoted into Mutuals as "confirmed + assumed". Use only when
   you know you follow back everyone you follow; the report labels these
   accounts as assumed so the assumption stays visible.
4. **`--curate` (interactive wizard)** — asks for your in-app follower and
   following totals, then walks you through the unverified accounts in
   batches of 25: `y` (follows back → promoted to Mutuals), `n` (doesn't →
   stays in the 👻 list, recorded so it's never re-asked), `s` (skip),
   `a` (assume all remaining), `q` (quit; progress saved). After every batch
   it prints *curated estimate vs in-app figures* — keep going until they
   match. Answers persist in `curated_followers.txt` /
   `curated_nonfollowers.txt` and are applied to every future run.

   ```bash
   python3 instagram_analysis.py --curate
   python3 instagram_analysis.py --curate --zip ~/Downloads/instagram-you.zip
   ```

## Running directly from the Meta ZIP

No need to unzip: pass the download as-is and it is extracted for the run.

```bash
python3 instagram_analysis.py --zip ~/Downloads/instagram-yourname-2026-04-02-AbCdEf.zip
python3 instagram_analysis.py --zip ~/Downloads/instagram-….zip --curate
python3 instagram_analysis.py --zip ~/Downloads/instagram-….zip --section connections
```

## App-derived counts (reconciliation)

Once a curation session has recorded your in-app totals (`curation_meta.json`),
the Connection summary derives the one-way follow counts from arithmetic that
doesn't depend on the broken follower export:

```
📐  App-derived counts (curation session: 583 followers / 402 following vs 401 mutuals):
   You follow → don't follow back:          402 − 401 = 1
   They follow you → you don't follow back: 583 − 401 = 182
```

- **Mutuals M** = raw export mutuals + curated/confirmed followers.
- **You follow → don't follow back** = following (G) − M. With a complete
  following list, this is reliable as soon as M is.
- **They follow you → you don't follow back** = in-app followers (F) − M.
- These are **counts only** — the export cannot name which accounts they are.
  Use `--curate` to classify named accounts, or check the 🙈 list (followers
  present in the export but not followed back), which is complete on its side.

## Interpreting the result

- **Pending requests** are informational: decide whether to cancel or keep waiting.
- **Unverified remainder** is trustworthy only when follower coverage is high
  (the analyzer treats < 80% of the app-reported total as incomplete — see
  [counts-explained.md](counts-explained.md)).
- With low coverage, treat the remainder as a *checklist for verification*, not
  as a list of people who genuinely don't follow back.
- The underlying follower-file gap cannot be fixed offline; requesting a fresh
  export sometimes delivers a fuller followers list. Everything else in this
  pipeline is deterministic and re-runnable.
