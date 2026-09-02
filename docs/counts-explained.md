# Counts explained

Three different numbers show up when analyzing an Instagram export. They measure different things.

## 1. Raw JSON entry counts

What is literally in the connection files — no deduplication logic beyond what Instagram stored:

- **`followers_*.json`** — one object per row in the array (or `relationships_followers` list).
- **`following.json`** — one object per row in `relationships_following`.

Example from the test fixture:

| File | Raw entries |
|------|------------:|
| `followers_1.json` | 3 |
| `following.json` | 4 |

There is **no mutuals file**. Instagram does not export a mutuals list.

## 2. Computed sets (what the analyzer derives)

After loading handles from JSON, the tool computes:

| Metric | Formula |
|--------|---------|
| Mutuals | accounts in both follower and following lists |
| Don't follow you back | following − followers |
| You don't follow back | followers − following |

These are only as complete as the **lists** in the export. If followers are missing from JSON, mutuals and one-way counts will not match the app.

The "don't follow you back" list is additionally **cleaned** before display —
pending follow requests, restricted profiles, stale unfollows, and manually
confirmed followers are subtracted (see [data-cleaning.md](data-cleaning.md)).
The report's 🧹 block shows raw claim → subtractions → unverified remainder.

## 3. App insights headline (optional)

If your export includes `logged_information/past_instagram_insights/audience_insights.json`, the **Followers** field is a single number (e.g. `583`) — a summary from Instagram analytics, **not** a list of usernames.

The analyzer shows this beside export totals:

```
Followers in export       59
Followers (app insights)  583  ⚠ export incomplete
```

Use insights as a **sanity check**, not as the source for named lists.

## Why export lists ≠ app profile

Meta’s download is not guaranteed to mirror live profile counts. Common reasons:

- Incomplete follower list in the ZIP (widely reported for larger accounts).
- Deactivated, pending, or restricted accounts listed in separate files.
- Export snapshot taken at a different time than the app UI.
- Partial export job still delivered as a ZIP.

## What to trust for what

| Question | Trust this |
|----------|------------|
| How many rows in my follower JSON? | Raw entry count / `--check` |
| Who is in my export? | Names printed in connection lists |
| What does the app say my total is? | Insights headline (if present) |
| Who are my mutuals in real life? | Only reliable if follower export is complete |

When coverage is below 80% of the insights total, the analyzer labels derived lists **export-only — follower list incomplete**.
