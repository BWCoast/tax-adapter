# CLAUDE.md

## Project

The **tax adapter** — the translation layer between the trading/bot ecosystem
and the `Taxes/` software. It reads canonical fills (Trading `trade_ledger`)
and standalone exports (PM algo) and emits canonical tax `Event` rows into the
`Taxes/` intake. It is **not** a tax engine, **not** a capital router, **not** a
reporting layer.

One-sentence boundary: *adapter = what happened; tax core = what it meant;
capital router = what to do with the money.*

**Status (verified 2026-09-29):** first slice implemented — **one** mapping (VARDE
NOK-quoted spot buy → `TRADE` + `FEE`), `uv run pytest` = 28 passed, 0 skipped.
Everything else in `SCHEMAS.md` is spec only; the trade_ledger mapper waits on
Trading's live transport. Output is the **bilateral** `events.csv` (`TRADE`, not
`ACQUISITION`/`SWAP` — ADR-004). Known v1 gaps: `SCHEMAS.md §3.7`. Where to pick up:
`HANDOFF.md`. Stack map: `Documents/Trading Alignment`. Verify-by: 2026-12-29.

---

## Architecture principles

1. **Translation only.** Normalize source activity into the canonical Event
   contract. Never compute tax, allocate capital, attribute P&L, or run
   strategy logic (ADR-001).
2. **Read only the canonical ledger / declared exports** (A1). Never raw venue
   payloads, bot DBs, or strategy state. A missing field is an upstream
   additive schema bump, not an adapter hack.
3. **Never fabricate** basis or value; UNRESOLVED (`None`) is explicit (A2).
4. **Ambiguity is visible** — `REQUIRES_REVIEW` with a counted reason, never a
   safer-looking guess (A3).
5. **Deterministic + idempotent** — pure function, stable `event_id` /
   `source_row_index`, re-import is a no-op (A5).
6. **Provenance preserved** end-to-end: `decision_id → order → trade →
   experiment_hash`, `run_id`, `git_commit`, `book`, `mode` (A6).
7. **Decimal only**, positive quantities; sign lives in `event_type`/`side` (A7).

Full list: `LAWS.md` (A1–A10). The mapping is `SCHEMAS.md`.

---

## Rules

1. **No tax math, no tax characterization in the adapter** — that's the
   deterministic `Taxes/` core (their Rule 1). The adapter emits typed events;
   the core classifies and computes.
2. **Docs are source of truth.** If code conflicts with `SCHEMAS.md` / an ADR,
   the code is wrong — *except* that an owning contract (Taxes' `event.py`,
   Trading's `trade_ledger`) outranks this repo's docs (`alignment/ECOSYSTEM.md §3`);
   `SCHEMAS.md` itself was once wrong that way (ADR-004). Label any spec-vs-code gap
   at the claim, with a verified date.
3. **Don't widen scope silently.** If a task seems to need allocation,
   reporting, or tax logic, stop — it belongs in another module (ADR-001).
4. **The adapter consumes contracts it doesn't own.** Propose additive changes
   to the `Taxes` Event contract or the `Trading` ledger back to those
   sessions; never redefine their semantics here.
5. **ADRs are binding.** Supersede with a new ADR; don't silently ignore.
6. **Build against real or schema-faithful data**, golden-fixture-pinned;
   re-verify when the first live ledger lands.

---

## Ownership map (who owns what)

| Contract | Owner session | This repo's relation |
|---|---|---|
| Canonical tax `Event` / `events.csv` intake | `Taxes/` | consumes (output target) |
| `trade_ledger`, intent, order | `Trading/` | consumes (input, read-only) |
| The fill→Event mapping (`SCHEMAS.md`) | **this adapter** | owns |
| PM algo export contract | **this adapter** defines, `PM algo` conforms | owns the contract |
| Capital allocation | future `capital-router` | downstream consumer of our output |

---

## Reference repos (read-only)

- `C:\Users\mrkro\Documents\Trading Alignment` — **stack-wide hub** (topology, seams,
  `event_id` registry mirror, OPEN items, producer-alignment lint); it wins over this
  repo's `alignment/` where they overlap
- `C:\Users\mrkro\Documents\Taxes` — tax core + canonical Event
  (`src/tax_core/models/event.py`, ADR-0001 + addenda)
- `C:\Users\mrkro\Documents\Trading` — `trade_ledger` v3 (ADR-005/006/007), HP-1 fixture
- `C:\Users\mrkro\Documents\Offshore trading` — VARDE (the one implemented producer)
- `C:\Users\mrkro\Documents\PM algo` — prediction-market bot (exports back)
- `C:\Users\mrkro\Documents\arb-bot` — registered producer (own `tax_export.csv`)
- `C:\Users\mrkro\Documents\SovereignForgeV1` — Norway-fork producer (PROPOSED) +
  methodology reference

See `SOURCES.md` for the file-level map of what each owns and what's reusable.

---

## Workflows

1. **Spec** — write/extend `SCHEMAS.md` for the mapping slice; have it audited.
2. **Plan** — implementation plan from the audited spec.
3. **Implement** — TDD, small commits, golden fixtures for known ledgers.
4. **Verify** — translate a real (or schema-faithful) ledger and diff events.
5. **Document** — update `PROGRESS.md`, and `SCHEMAS.md`/`LAWS.md` on changes.

## Tech stack (as built)

- **Language:** Python `>=3.11` (`pyproject.toml`; verified running on 3.14.3), `uv`
- **Runtime deps:** none (stdlib + `Decimal`; never floats for money)
- **Data:** frozen `dataclass` `Event` (`src/tax_adapter/events.py`) → the `Taxes/`
  20-column bilateral CSV
- **Tests:** pytest via `uv run pytest` (28); golden fixtures byte-identical

## Commands

```bash
uv run pytest
PYTHONPATH=src uv run python -m tax_adapter.cli --producer varde --in <fills.csv> --out <events.csv>
```

`PYTHONPATH=src` is required for the CLI (no build-system). `src/tax_adapter/`:
`events.py`, `cli.py`, `producers/varde.py`. Tests + fixtures: `tests/`.
