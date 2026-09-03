# ADR-0007: AdsInsights compute-once + inventory-first missing data

Status: Accepted and implemented

## Context

Ads & Tracking reports lived as ad-hoc printers in `instagram_analysis.py`.
They printed advertiser names only (ignoring audience-type flags), emitted
absolute-path `[!] File not found` noise for optional Meta files, and did not
parse ads viewed/clicked. A sparse ZIP looked broken rather than incomplete.

## Decision

1. Build **`AdsInsights` once per run** (`ads/insights.py`) — inventory,
   advertisers + flag counts, interests/categories, engagement, preferences,
   off-Instagram apps — and render via `ads/report.py`.
2. Use shared **`export_inventory`** for present / missing / empty status across
   ads file groups (aliases supported). Optional ads files never spam absolute
   paths in the ads section.
3. Advertiser **flag histogram is mandatory** whenever the advertisers file is
   present (`data-file` / `remarketing` / `in-person store visit`).
4. Sample lists respect **`--ads-limit`** (default 30; `0` = unlimited).

## Consequences

- Ads section matches Connections' compute-once pattern (ADR-0003).
- Users learn *how* advertisers target them, not only names.
- Sparse exports show a clear inventory instead of path errors.
- Future pillars (activity/security deepen, messages) reuse `export_inventory`.
