# HANDOFF — for the next session

Date: 2026-06-14 · From: scoping session · To: next tax-adapter session

## TL;DR

The **tax-adapter** repo was scoped and documented. It is a **translation
layer only**: reads canonical `trade_ledger` fills + standalone exports, emits
canonical tax `Event` rows into `Taxes/`. No tax math, no capital allocation,
no reporting. Nothing is implemented yet — by design, the build is gated on
live `trade_ledger` rows (the trading lab is pre-edge).

> adapter = *what happened* · tax core = *what it meant* · capital router =
> *what to do with the money*

## Location & state

- **This repo now lives at** `C:\Users\mrkro\Documents\Tax adapter\` (moved
  here from `C:\Users\mrkro\Tax adapter` this session, alongside the sibling
  repos `Taxes`, `Trading`, `PM algo`, `SovereignForgeV1`).
- The old path `C:\Users\mrkro\Tax adapter` may still show as an **empty
  folder** — it was the previous session's working directory and the OS held a
  lock on the directory itself; its contents were copied (verified identical)
  and emptied. Delete the empty husk if it lingers.
- **Not a git repo yet.** Consider `git init` + a baseline commit early next
  session (the sibling repos are all git-tracked).
- Start the next session with the working directory set to the new path.

## What exists (read these in order)

1. `README.md` — what it is/isn't, the producer→adapter→tax diagram.
2. `decisions/ADR-001-adapter-scope-boundary.md` — **the scope fence** and
   ownership model. Read this first if you read nothing else.
3. `SCHEMAS.md` — **the mapping spec** (the real work product): how each
   ledger/export row becomes tax events.
4. `LAWS.md` — A1–A10, the non-negotiables.
5. `decisions/ADR-002-...deferred.md` — why derivative/resolution tax
   characterization is deferred to the tax core.
6. `SOURCES.md`, `LESSONS_LEARNED.md`, `GOTCHAS.md`, `PROGRESS.md`, `CLAUDE.md`.

All docs are grounded in the **actual** contracts read this session:
`Taxes/docs/adr/0001` (canonical Event) and `Trading/SCHEMAS.md` +
`ADR-005/006` (trade_ledger, two books). They are not boilerplate.

## The two anchors the adapter bridges

- **Output (downstream):** `Taxes/` canonical Event — 20-column `events.csv`,
  `event_type ∈ {DISPOSAL, ACQUISITION, INCOME, FEE, TRANSFER_IN,
  TRANSFER_OUT, SWAP, REQUIRES_REVIEW}`, qualified asset keys, Decimal,
  UNRESOLVED never fabricated. (`Documents/Taxes`, ADR-0001.)
- **Input (upstream):** `Trading/` `trade_ledger` — one row per fill, `book`
  (lab|accrual), `fill_kind`, `fx_usdnok_at_fill`, `decision_id` provenance
  chain. (`Documents/Trading`, ADR-005/L17.) Plus `PM algo` exports.

## Highest-risk mapping decisions (don't get these wrong)

- Derivative fills are **NOT** acquisitions/disposals of the underlying — emit
  realized-PnL/funding in the settle asset only (SCHEMAS §3.2, GOTCHAS 1).
- A stablecoin-quoted buy is a **SWAP** (two taxable legs), not a one-sided
  acquisition (SCHEMAS §3.1, GOTCHAS 2).
- Capital-router book transfers are a **linked TRANSFER_OUT/IN pair**, never
  disposal+acquisition (law A8, GOTCHAS 3).
- `event_type` is a normalization, not a tax ruling — ambiguity →
  `REQUIRES_REVIEW`, never a guess (laws A3/A4).

## Open items needing cross-session coordination (carried from PROGRESS.md)

1. **`Taxes` session:** confirm + reserve the adapter's `ledger:` / `pm-algo:`
   `event_id` prefixes (propose as an ADR-0001 addendum note on their side).
2. **`Trading` session:** agree the `trade_ledger` → adapter **transport**
   (how canonical rows are handed over — file drop? shared read-only export?).
   The schema is settled; only the transport is open. Adapter reads canonical
   rows only (law A1).
3. **`PM algo` session:** define + conform to the prediction-market export
   contract (SCHEMAS §3.4 minimum set: fills, fees, realized PnL,
   deposits/withdrawals, year-end positions).

## Build gating (nothing to implement until these unlock)

| gate | unlocks |
|---|---|
| Taxes Event contract stable (done — ADR-0001) | mapping spec frozen ✅ |
| Trading lab emits live `trade_ledger` rows (pre-edge today) | build the ledger→Event mapper (TDD, golden fixtures) |
| PM algo export contract agreed | build the prediction-market export adapter |
| Capital router live (Trading ADR-006) | wire the TRANSFER_OUT/IN book-transfer path |

When implementation starts: TDD, golden-fixture-pinned, build against **real
exported rows or schema-faithful fixtures** — not an imagined shape (GOTCHAS
11). Re-verify the whole mapping when the first live ledger lands.

## Boundary reminders (the easy ways to go wrong)

- Never read raw venue payloads, bot DBs, or strategy state — canonical ledger
  + declared exports only (A1).
- Never compute tax, allocate capital, or build reports here — those are other
  modules (A9 / ADR-001). If a task seems to need them, stop.
- A missing ledger field is an **upstream additive schema bump**, not an
  adapter-side computation (GOTCHAS 10).
