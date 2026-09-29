# HANDOFF — for the next session

Date: 2026-09-29 · From: docs-reconciliation session · To: next tax-adapter session
Last verified: 2026-09-29 · Verify-by: 2026-12-29

---

## ⏭ Pick up here (2026-09-29)

**State, with counts.** `master` was level with `origin/main` at `d89ccb1`
(2026-06-20) before this docs pass. `uv run pytest` → **28 passed, 0 skipped**.
**One mapping is implemented:** VARDE NOK-quoted spot buy → `TRADE` + `FEE`
(`src/tax_adapter/producers/varde.py`, golden-pinned, byte-identical re-run).
Everything else in `SCHEMAS.md` is specification and is labelled as such.

**What changed since the 2026-06-14 handoff below** (read that as history):
- **Code exists.** `src/tax_adapter/{events,cli}.py` + `producers/varde.py`, 5 test
  files, VARDE HP-1 golden fixtures. Run: `uv run pytest`;
  `PYTHONPATH=src uv run python -m tax_adapter.cli --producer varde --in … --out …`.
- **ADR-004** — the first executable slice is VARDE (not MM as ADR-003 planned), and
  the output contract is the real bilateral `TRADE` model. `SCHEMAS §1/§3.1/§7`
  were reconciled to it; the events.csv FINDING is **resolved**.
- **Stack hub** — `Documents/Trading Alignment` is the canonical stack map; this
  repo's `alignment/` defers to it. Hub OPEN-1 (event_id prefixes) is **closed**
  (Taxes ADR-0001 addendum 2026-07-13). Trading **ADR-007** settled the transport
  *format* (CSV drop); live mechanics deferred until live rows exist.
- The old stop-signal ("do NOT add more design until the producer + tax core
  move") is **retired** — the producer and tax core moved.

**Next actions, in priority order:**
1. **Close the known v1 gaps** (`SCHEMAS §3.7`, list of 5) — golden fixture first
   for each: canonical `(exchange_ts, trade_id, leg)` sort for `source_row_index`;
   emit `FEE` only when `fee > 0`; blank `fee` → `REQUIRES_REVIEW` with a counted
   reason instead of a bare `InvalidOperation`; the counted-skip ledger.
2. **VARDE slice 2:** sell, stablecoin-quoted (needs `fx_usdnok_at_fill`; absent →
   blank/UNRESOLVED), XRPL linked `TRANSFER_OUT`/`TRANSFER_IN` pair.
3. **`trade_ledger` mapper** against `SCHEMAS §7` and Trading's
   `fixtures/trade_ledger/hp1_spot_buy.csv`; pin `tests/fixtures/trade_ledger/…`.
4. **Ask Taxes:** the PM-algo `event_id` prefix is unreserved (`pm-algo:` was
   ratified only as a `provenance.algo` label) — blocks the PM mapper; and note that
   `varde:` is now emitted (their addendum says "not yet emitted").
5. **Ask the hub (Trading Alignment):** refresh `CONTRACTS.md` §3 (prefix status) and
   worked examples A/B (still write `ACQUISITION`/`SWAP` as `event_type`); flip
   OPEN-2/3 per Trading ADR-007.
6. **Housekeeping:** `pyproject.toml` `tool.uv.dev-dependencies` is deprecated (uv
   warns every run) → `dependency-groups.dev`; the conformance test hardcodes the
   Taxes path `C:\Users\mrkro\Documents\Taxes\src` (skips on any other machine).

---

> **Everything below this line is the 2026-06-14 scoping handoff, kept as history.**
> Where it says nothing is implemented, or lists prefixes / transport / the HP-1
> fixture as open, the section above supersedes it.

---

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
- ~~**Not a git repo yet.**~~ *(Historical — done 2026-06-14 (`b0b038a`). The repo
  is tracked; `origin` = `https://github.com/BWCoast/tax-adapter`, branch
  `master` → `origin/main`.)*
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
