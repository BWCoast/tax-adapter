# ADR-003 — First end-to-end producer is MM Strategy Bot; first happy path is spot-only

Date: 2026-06-14 · Status: accepted (sequencing decision; supersede with a new
ADR to change the order)

## Context
Implementation is gated on live `trade_ledger` rows (the lab is pre-edge, see
PROGRESS.md). But *specifying* and *fixturing* one minimal end-to-end path is
not gated, and doing so first is the "end-to-end wiring beats documented-but-
disconnected modules" lesson made concrete (alignment/ECOSYSTEM.md §9). We must
pick which producer and which scenario to wire first.

Two candidates were considered:

1. **MM Strategy Bot / Trading lab** (`trade_ledger`). The input contract is
   already frozen (Trading ADR-005/006, L17). The only genuine unknown is the
   *transport* of canonical rows into the adapter (PROGRESS.md open item 2).
2. **Prediction-Market algo (Kalshi)**. Its export contract is still OPEN
   (SCHEMAS.md §3.4) — wiring it first means designing the contract *and* the
   path simultaneously, more moving parts.

## Decision
1. **MM Strategy Bot / Trading lab is the first producer wired end-to-end.** Its
   contract is settled, isolating the work to transport + mapping rather than
   contract design.
2. **The first happy path is spot-only** — a single vanilla spot buy with a
   fiat quote, one venue, one book (`lab`), no derivatives, no swaps, no
   transfers. It emits exactly one `ACQUISITION` + one `FEE`.
3. The worked example for this path is pinned in **SCHEMAS.md §7 (Happy Path 1)**
   and becomes the first golden fixture when the mapper is built.

Derivatives and stablecoin-quoted swaps are deliberately excluded from the
first path: derivative characterization is the highest-risk mapping and is
already deferred (ADR-002); a stablecoin-quoted buy is a two-leg SWAP
(SCHEMAS.md §3.1). Both belong to later happy paths (HP-2 swap, HP-3
derivative), once the spine is proven.

## Why spot-only first
- A happy path exists to de-risk the *plumbing* (transport → mapper → Event →
  Taxes intake). Mixing the riskiest *semantics* (derivatives) into that test
  defeats its purpose.
- A fiat-quoted spot buy is the only fully one-sided case — single ACQUISITION,
  no SWAP disposal leg, no FX tier needed for `nok_value` when the quote is NOK.
  Fewest fields exercised, cleanest first fixture.
- It still exercises the load-bearing machinery: deterministic `event_id`,
  `source_row_index` ordering, provenance preservation, the FEE leg, and the
  Taxes 20-column intake.

## Consequences
- Raises the **`trade_ledger` → adapter transport** decision (PROGRESS.md open
  item 2 / ECOSYSTEM.md §8) to the top of the Trading-coordination queue — it is
  now the gating unknown for HP-1.
- The PM-algo export contract (§3.4) is *not* on the HP-1 critical path; it can
  be settled in parallel without blocking the first wire-up.
- No implementation is unblocked by this ADR — the live-rows gate still holds.
  This fixes *what to build first* the moment the gate opens.

## Trigger to revisit
If the lab's first live rows are derivative/perp (not spot), or Trading's
transport decision makes a different producer cheaper to wire first, supersede
this ADR.

## Related
SCHEMAS.md §3.1 (spot fills), §7 (Happy Path 1 worked example); ADR-002
(derivative characterization deferred); ADR-001 (scope boundary);
alignment/ECOSYSTEM.md §8 (OPEN items), §9 (end-to-end-wiring lesson);
PROGRESS.md open items 2.
