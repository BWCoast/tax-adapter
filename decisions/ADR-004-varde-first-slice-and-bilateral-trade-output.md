# ADR-004 — First executable slice is VARDE HP-1; the bilateral `TRADE` model is the output contract

Date: 2026-09-29 (records decisions taken in the 2026-06-19 genesis design and
implemented in `d89ccb1`, 2026-06-20) · Status: accepted · **Amends ADR-003**
(sequencing and event-type notation); does not otherwise supersede it.

## Context
ADR-003 (2026-06-14) sequenced **MM Strategy / Trading lab** as the first producer
wired end-to-end, with a `trade_ledger` spot buy emitting one `ACQUISITION` + one
`FEE`. Three things then happened:

1. **Trading stayed pre-edge.** No live `trade_ledger` rows exist and the transport
   is still open (hub `GAPS.md` OPEN-3), so the MM mapper had nothing real to be
   built against (GOTCHAS 11).
2. **VARDE became buildable first.** VARDE was realigned to a facts-only producer
   (hub ADR-004 / OPEN-12), shipped a deterministic `varde-fills.csv` exporter and a
   byte-pinned HP-1 fixture (`hp1_nok_spot_buy.csv`), and was registered here
   (`SCHEMAS.md §3.7`, `SOURCES.md §5`).
3. **The output shape in our own spec was wrong.** Verified against Taxes
   `src/tax_core/models/event.py` (recorded as the 2026-06-18 ECOSYSTEM FINDING):
   `CanonicalEvent` is **bilateral** and has no `ACQUISITION`/`DISPOSAL`/`SWAP`
   type; a one-sided "in" is only valid as `TRANSFER_IN`/`GIFT_IN`/`INCOME`. The
   `ACQUISITION + FEE` pair in ADR-003 / SCHEMAS §7 would be rejected at Taxes'
   construction-time validation.

## Decision
1. **The first executable slice is VARDE's NOK-quoted spot buy (HP-VARDE-001)**,
   delivered in `d89ccb1` (`src/tax_adapter/producers/varde.py`, CLI, golden test).
   ADR-003's *sequencing* is amended accordingly. The MM/Trading `trade_ledger` HP-1
   (`SCHEMAS.md §7`) remains the contract for the **next** mapper, gated on the
   transport decision and the mapper itself — it is not abandoned.
2. **The adapter's output contract is the real bilateral `CanonicalEvent`** exactly
   as Taxes defines it. A spot buy or sell is **one `TRADE`** (both legs) plus a
   standalone **`FEE`**. `ACQUISITION`/`DISPOSAL`/`SWAP` are not `event_type`
   values; in older prose they are descriptive shorthand only. `SCHEMAS.md`
   §1/§3.1/§7 were reconciled to this on 2026-09-29. This **mirrors** the owning
   contract and does not redefine Event semantics (CLAUDE.md rule 4).
3. **The seam is the CSV, not Taxes' Python class.** The adapter carries its own
   frozen `Event` dataclass whose `validate()` re-implements the construction-time
   shape rules, so a row Taxes would reject fails in the adapter first. There is no
   runtime import of Taxes; `tests/test_events_conformance.py` optionally proves
   compliance against the real class when Taxes is importable locally.
4. **Fail closed on the unmapped.** In v1 any shape the mapper does not implement
   (sell, stablecoin-quoted, transfers, non-spot) raises `NotImplementedError`
   rather than guessing (A3). Counted-skip / `REQUIRES_REVIEW` routing is later work.

## Why
- A first slice must be built against **real or schema-faithful data** (CLAUDE.md
  rule 6); VARDE had it, Trading did not.
- Emitting rows the tax core rejects is a silent failure; validating at build time
  in the adapter turns it into a loud one.
- Mirroring instead of importing keeps the read-only repo boundary (ECOSYSTEM §5)
  while the frozen 20-column CSV keeps the mirror stable.

## Consequences
- ADR-003's decision text ("one `ACQUISITION` + one `FEE`") is superseded in
  notation: read it as one `TRADE` + one `FEE`. Its "MM first" ordering is amended
  as above. A pointer was added to ADR-003's header; its body is left as a record.
- **Known v1 gaps** between spec and code (input-order `source_row_index`, `FEE` on
  zero fee, blank-fee crash, no counted-skip ledger, no rich provenance dict) are
  listed in `SCHEMAS.md §3.7`. They are labelled, not fixed, by this ADR.
- Two artefacts elsewhere still use the legacy shape and are **not** ours to edit:
  the hub `Trading Alignment/CONTRACTS.md` worked examples A/B, and the
  `PROPOSED` HP-SF-001 example (flagged with a banner in `SCHEMAS.md §3.1`).
  Owners: Trading Alignment and the SovereignForge recognition proposal.
- Adding the next producer is now "write a mapper + pin a golden fixture", reusing
  `Event`, `write_events_csv` and the CLI registry.

## Trigger to revisit
Taxes changes `CanonicalEvent` (new Taxes ADR) → update `events.py` + the
conformance test in the same commit. Trading emits live rows and settles transport →
build the `trade_ledger` mapper against §7 and pin its golden fixture.

## Related
ADR-001 (scope), ADR-002 (characterization deferred), ADR-003 (amended);
`docs/superpowers/specs/2026-06-19-tax-adapter-genesis-design.md`;
`SCHEMAS.md §1, §3.1, §3.7, §7`; hub `decisions/ADR-004` (VARDE realignment),
`GAPS.md` OPEN-3 / OPEN-12.
