# Instagram export checklist

Use this when requesting a download from Meta so the analyzer has the files it needs.

## Request settings

1. Open **Instagram → Settings → Accounts Centre → Your information and permissions → Download your information**.
2. Choose **Some of your information** (or **All** if you want every report section).
3. Under **Connections**, enable **Followers and following**.
4. Enable other sections you care about (activity, security, ads) — missing sections are skipped silently.
5. Set date range to **All time**.
6. Choose format **JSON** (not HTML — both arrive as `.zip` files).
7. Submit and wait for the email (often 5–30 minutes).

## After download

1. Keep the original ZIP as a backup.
2. Either:
   - Unzip and pass the folder: `--export-dir ~/Downloads/instagram-…`, or
   - Pass the ZIP directly: `--zip ~/Downloads/instagram-….zip`
3. Run the setup check before your first full report:

   ```bash
   python3 instagram_analysis.py --check --export-dir /path/to/export
   ```

## What to verify

| Check | Good sign |
|-------|-----------|
| Follower files | One or more `connections/followers_and_following/followers_*.json` |
| Following file | `following.json` (or `following_1.json`, …) |
| Raw counts | `--check` shows entry counts; compare to your app if insights are present |
| Format | Files contain `.json`, not `.html` |

## Common mistakes

- **HTML export** — looks like a ZIP but the analyzer cannot read it. Re-request as JSON.
- **Wrong section** — forgot **Followers and following**; connection reports fail.
- **Only opened `followers_1.json`** — large accounts split across `followers_2.json`, …; the tool merges them, but all parts must be in the folder.
- **Expecting app profile counts** — the export list and the app headline number often differ. See [counts-explained.md](counts-explained.md).
