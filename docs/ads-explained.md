# Ads & Tracking explained

Watchr's `--section ads` report summarises marketing and tracking files from
your Instagram JSON export. Numbers only reflect **this ZIP snapshot** — Meta
often omits categories you did not select when requesting a download.

## Export inventory

The section starts with present / missing / empty status for:

| Logical file | Typical path |
|---|---|
| Advertisers using your activity or information | `ads_information/instagram_ads_and_businesses/advertisers_using_your_activity_or_information.json` |
| Ads interests | `…/ads_interests.json` |
| Other categories used to reach you | `…/other_categories_used_to_reach_you.json` |
| Ads viewed / clicked | `ads_information/ads_and_topics/ads_viewed.json`, `ads_clicked.json` |
| Ad preferences | `ads_information/ad_preferences.json` |
| Off-Instagram activity | `logged_information/ads_and_topics/off_instagram_activity.json` |

Missing files are normal when you requested a partial download. Re-enable those
categories in Accounts Centre and request a new export if you need them.

## Advertiser audience types

Each advertiser row can carry three flags (an advertiser may have more than one):

| Flag | Meaning (plain language) |
|---|---|
| **data-file custom audience** | The business uploaded a list that includes you (email, phone, or similar) so Meta can match and target you. |
| **remarketing** | The business is targeting people who interacted with them before (site/app/pixel-style audiences). |
| **in-person store visit** | Targeting related to physical store visit signals Meta associates with you. |

Watchr prints a **histogram** of these flags first (e.g. 892 data-file / 0
remarketing / 0 store visit), then a capped sample of names with labels.
Use `--ads-limit 0` (or `--output FILE`) for the full list.

## Interests and categories

- **Ads interests** — topics Meta inferred about you for ad targeting.
- **Other categories used to reach you** — additional reach categories from the
  export (structure varies by Meta export generation).

## Ads engagement

From `ads_viewed` / `ads_clicked` when present:

- Total viewed and clicked counts
- Date span (month granularity)
- Top advertisers by views and by clicks

## Off-Instagram activity

Apps and websites that sent activity events to Meta (counts per app/site).
Paths sometimes differ; Watchr checks known aliases.

## Related docs

- [export-checklist.md](export-checklist.md) — what to enable when downloading
- [counts-explained.md](counts-explained.md) — connection counts (separate domain)
