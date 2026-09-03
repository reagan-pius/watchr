# ADR-0008: Full-export section packages

Status: Accepted and implemented

## Context

After AdsInsights (ADR-0007), Activity and Security still used ad-hoc printers
with absolute-path missing-file noise. Messages, apps/websites, contacts,
shopping, and preferences were unparsed, so Watchr could not honestly call
itself a full export analyser.

## Decision

1. Each domain gets a package with `paths` / `parse` / `insights` / `report`,
   following Connections and Ads.
2. Optional files use **export inventory** (present / missing / empty) — no
   absolute-path `[!]` spam in these sections.
3. New CLI sections: `messages`, `apps`, `contacts`, `shopping`, `preferences`
   (plus deepened `activity` and `security`).
4. **Messages are metadata-only** — thread counts, participants, spans, media
   file counts. Message bodies are never printed.
5. Contacts samples are **redacted by default**; `--no-redact` shows raw names.
6. `--ads-limit` caps sample rows across list-heavy sections (historical flag name).

## Consequences

- `all` covers the major JSON export domains Watchr supports.
- Privacy posture stays offline and conservative for DMs/contacts.
