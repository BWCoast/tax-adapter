# CLAUDE.md

## Project

The **tax adapter** — the translation layer between the trading/bot ecosystem
and the `Taxes/` software. It reads canonical fills (Trading `trade_ledger`)
and standalone exports (PM algo) and emits canonical tax `Event` rows into the
`Taxes/` intake. It is **not** a tax engine, **not** a capital router, **not** a
reporting layer.

One-sentence boundary: *adapter = what happened; tax core = what it meant;
capital router = what to do with the money.*

**Status:** Scoping. Contracts on both sides are pinned; mapping spec + scope
fence written. Implementation is gated on live `trade_ledger` rows (the lab is
pre-edge). See `PROGRESS.md`.

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
   the code is wrong.
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

- `C:\Users\mrkro\Documents\Taxes` — tax core + canonical Event (ADR-0001…0030)
- `C:\Users\mrkro\Documents\Trading` — `trade_ledger` (ADR-005/006), LAWS L17/L20
- `C:\Users\mrkro\Documents\PM algo` — prediction-market bot (exports back)
- `C:\Users\mrkro\Documents\SovereignForgeV1` — platform/module-map context

See `SOURCES.md` for the file-level map of what each owns and what's reusable.

---

## Workflows

1. **Spec** — write/extend `SCHEMAS.md` for the mapping slice; have it audited.
2. **Plan** — implementation plan from the audited spec.
3. **Implement** — TDD, small commits, golden fixtures for known ledgers.
4. **Verify** — translate a real (or schema-faithful) ledger and diff events.
5. **Document** — update `PROGRESS.md`, and `SCHEMAS.md`/`LAWS.md` on changes.

## Tech stack (intended, to match the ecosystem)

- **Language:** Python 3.12+
- **Math:** `Decimal` (never floats for money)
- **Data:** `dataclasses`; canonical events out as the `Taxes/` 20-column CSV
- **Tests:** pytest; golden fixtures pinned byte-identical (determinism gate)
