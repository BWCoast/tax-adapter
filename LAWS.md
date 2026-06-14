# LAWS — non-negotiable rules for the tax adapter

Living list. A law is added when its absence would corrupt the tax position or
break the boundary between this module and its neighbours. Prefixed `A` (for
adapter) to avoid confusion with Trading's `L` laws and Taxes' ADRs, which
these inherit from. Removed only with a written decision memo.

## A1 — Read only the canonical ledger / declared exports
The adapter consumes the canonical `trade_ledger` (Trading SCHEMAS.md), the
declared prediction-market export contract, and declared CSVs. It NEVER reads
raw venue payloads, bot logs, or strategy-internal state. If a needed fact is
not in the canonical ledger, the fix is an additive ledger schema bump
upstream (Trading L6/L20) — never a side-channel into this adapter.
**Why:** Trading ADR-005/L20 — "tax reads only the canonical ledger." A bot
that exports through a private channel re-creates the per-engine coupling the
canonical contract exists to kill.

## A2 — Never fabricate basis or value
Unknown cost basis or NOK/GBP value is emitted as `nok_value = None`
(UNRESOLVED) and surfaced for review. The adapter never zeroes, guesses, or
interpolates a price the upstream ledger did not capture. It passes through
`fx_usdnok_at_fill` where present and marks absence explicitly.
**Why:** Taxes ADR-0005 / CLAUDE Rule 2 — UNRESOLVED is explicit, never zero.
A fabricated number is indistinguishable from a real one in a tax filing.

## A3 — Ambiguity becomes REQUIRES_REVIEW, never a safer-looking guess
Where the source record is ambiguous or the type is jurisdiction-sensitive,
the adapter emits `REQUIRES_REVIEW` with a counted reason. It does not pick the
type that happens to minimise tax or look tidy.
**Why:** Taxes ADR-0001 design principle ("explicit about ambiguity"). Silent
mapping to a safer type is a bug that hides as clean output.

## A4 — No tax math, no tax characterization, in the adapter
The adapter normalizes economic facts into typed events. It does NOT compute
gain/loss, run FIFO/S104, value lots, or decide capital-vs-income. event_type
is a normalization label, not a tax ruling; the deterministic tax core rules.
**Why:** Taxes Rule 1 (no AI/logic in the calculation path) + Trading ADR-005.
Tax logic embedded in an adapter is untestable, unauditable, and drifts from
the authoritative core.

## A5 — Deterministic and idempotent
Same input → byte-identical events, always. `event_id` is a pure function of
upstream identifiers; `source_row_index` from a stable sort. No clock, no
randomness, no network in the mapping path. Re-importing a ledger is a no-op.
**Why:** Taxes deterministic-core principle + ADR-0002 (FIFO ordering depends
on stable `source_row_index`). Non-deterministic events break golden fixtures
and re-import safety.

## A6 — Provenance preserved end-to-end
Every emitted event carries, in `provenance`, the full upstream chain:
`decision_id → order_id → trade_id → experiment_hash`, plus `run_id`,
`git_commit`, `book`, `mode`, and the original ledger row reference. Nothing is
discarded that a future audit would need to trace an event back to its fill.
**Why:** Trading L17 / PM algo law 6 — tax facts are captured at fill time and
the trail must survive translation; retrofitting provenance is impossible.

## A7 — Decimal only, positive quantities
All quantities and values are `Decimal`. `quantity` is always positive; sign /
direction is carried by `event_type` and `side`, never by a negative quantity.
No binary floating point anywhere near money.
**Why:** Taxes ADR-0001 (Decimal-safe) + PM algo §14/§15 — floats lie at money
boundaries.

## A8 — Internal book transfers are transfers, not disposals
Capital-router allocations between books (lab → accrual, Trading ADR-006) emit
a linked `TRANSFER_OUT`/`TRANSFER_IN` pair with matching asset/quantity/time,
never disposal+acquisition. Beneficial ownership does not change, so no taxable
event is created.
**Why:** mis-typing an internal move as a disposal manufactures phantom
gains/losses and double-counts capital. Relies on Taxes transfer-linking
(ADR-0007/0013).

## A9 — The adapter owns translation only (scope fence)
No capital-allocation logic, no P&L attribution, no reporting, no strategy
logic, no dashboard. Those are the capital-router, pnl-service, and engine
modules respectively (ADR-001).
**Why:** combining translation with allocation or interpretation blurs three
independently-evolving responsibilities and is the exact anti-pattern the
"adapter session first" decision rejected.

## A10 — event_id namespace is verified collision-free
Any `event_id` format the adapter emits is checked against Taxes' reserved
prefixes (`inflow_group:`, and the canonical `xrpl:`/`csv:` parser formats,
ADR-0001 addendum) before use. The adapter's `ledger:`/`pm-algo:` prefixes are
reserved here and must not be reused by upstream parsers.
**Why:** Taxes ADR-0001 addendum — a colliding event_id silently merges or
shadows unrelated events.
