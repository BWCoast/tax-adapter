# ROLE — Taxes (tax core / authority of record)

> Read [`ECOSYSTEM.md`](ECOSYSTEM.md) first. This card is your lane within it.
>
> **No local override.** You own the Event contract — ratify changes to it in
> your own ADRs. For producer/ledger/adapter semantics you need changed, do not
> redefine them locally; request an additive change via the Tax Adapter
> alignment folder.

## Your lane
*What it meant.* You are the tax authority of record. You own the canonical
`Event` contract and the deterministic, jurisdiction-aware tax core. You **set
the requirements** every other session satisfies.

## What you own
- The canonical `Event` model / 20-column `events.csv` intake (ADR-0001) and the
  reserved `event_id` prefixes.
- All tax characterization and computation: FIFO (NO) / S104 (UK), valuation
  precedence (ADR-0006), missing-basis policy (ADR-0005), transfer linking
  (ADR-0007/0013), overrides (ADR-0019), multi-jurisdiction dispatch (ADR-0020),
  asset identity (ADR-0021).
- The exit codes, the `events.csv` format, and "no AI / no guessing in tax math".

## What you must NOT do
- Don't reach into producer internals or the adapter's mapping — you consume
  canonical `Event` rows only.
- Don't ask producers or the adapter to emit tax conclusions; they emit *facts*
  (`event_type` is normalization, not a ruling — you do the ruling).
- Don't bend the Event contract per-source; one canonical model, source-agnostic.

## What you require from the adapter
- Well-typed `Event` rows with provenance preserved, `Decimal` values,
  `UNRESOLVED` never fabricated, ambiguity as `REQUIRES_REVIEW`.
- FX supplied as a tier-1 `{rate, source, as_of_ts}` triple (see A2) — flag any
  bot fill that fell through to your warned fallback; it means upstream capture
  failed.

## SovereignForge takeaways tagged to you
- **A1 — Oslo year-boundary** ⭐: bucket the income year on Europe/Oslo
  wall-clock, not UTC. Golden fixture: `2025-12-31T23:30:00Z` → tax year 2026.
- **A2 — FX tiering** ⭐: treat adapter-supplied FX as tier-1, above the
  ADR-0010 warned fallback; flag fallback use on bot fills.
- **A3 — classification-defense** ⭐⭐⭐ (with Trading): surface
  activity-frequency/turnover metrics per year, emit a discretion/audit
  appendix, and flag when activity approaches business-classification
  thresholds *before* filing.
- **A6 — baseline step-up guard**: if any `inngangsverdi` baseline date ever
  applies, FIFO must refuse to compute basis on pre-baseline lots (loud).

## How to request a contract change
You are the owner of the Event contract — ratify additive changes in *your*
ADRs, then note it back here. For producer/adapter changes you need, file the
request to the Tax Adapter alignment folder and let that owner ratify.

## Read order
`ECOSYSTEM.md` → this card → your own `docs/adr/0001…0030` → adapter
[`SCHEMAS.md`](../SCHEMAS.md) (to see what the adapter feeds you).
