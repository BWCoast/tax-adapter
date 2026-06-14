# ADR-001 — The adapter is translation only; allocation and reporting are separate

Date: 2026-06-14 · Status: accepted (scope/architecture; implementation gated
on live `trade_ledger` rows)

## Context
The ecosystem has a tax authority of record (`Taxes/`, deterministic core
reading a canonical Event), and a growing set of activity producers: the
trading lab (lab + accrual books, `trade_ledger`), the standalone
prediction-market bot, future DCA/accrual buys, a future capital router, and
future engines. The question this ADR settles: **what does the bridge between
producers and the tax software do, and what does it deliberately refuse to
do?**

A tempting but wrong answer is one fat "tax + capital + reporting" module.
That blurs three responsibilities that evolve independently:
- **Translation** — *what happened?* (normalize fills/fees/transfers into tax
  events).
- **Interpretation** — *what did it mean financially / for tax?* (FIFO/S104,
  valuation, gain/loss, P&L attribution).
- **Allocation** — *what do we do with the capital now?* (tax-reserve, route
  surplus to accrual, fund engines).

## Decision
This module is the **tax adapter**: translation only. One function in spirit:

> `f(canonical_ledger_rows, declared_exports) -> canonical_tax_events[]`

It normalizes producer activity into the `Taxes/` canonical Event contract
(ADR-0001), preserves provenance, and is explicit about ambiguity. It is a
*producer for the tax core*, peer to the existing CSV/XRPL parsers — not a
second tax engine.

### Explicitly out of scope (delegated)
| Concern | Owner | Boundary |
|---|---|---|
| Tax math (FIFO, S104, valuation, gain/loss, jurisdiction rules) | `Taxes/` deterministic core | adapter emits events; core computes (A4) |
| Capital allocation (tax-reserve, accrual routing, engine funding) | future `capital-router` (Trading ADR-006) | router runs downstream of *realized PnL the adapter has already translated*; it does not live here |
| P&L attribution / reporting / dashboards | future `pnl-service` | interpretation of the ledger, not translation of it |
| Strategy / quoting / sizing | the engines (Trading ADR-005, L16) | strategies propose; they don't own accounting |
| Venue-native payloads | venue adapters in the trading repo | adapter reads the canonical ledger only (A1) |

### Ownership model (mirrors Trading ADR-005's split)
- The **`Taxes` session owns** the canonical Event / intake contract. The
  adapter consumes it and may *propose* additive changes; it never redefines
  Event semantics.
- The **`Trading` session owns** `trade_ledger`, intent, order contracts. The
  adapter consumes the ledger read-only.
- This **adapter session owns** the mapping (SCHEMAS.md), its laws (LAWS.md),
  and the export contract it imposes on standalone producers (e.g. PM algo).

## Sequence (why adapter first)
Adapter → reporting → router. Translation must exist and be trusted before
interpretation or allocation can run on top of it. Letting a trader-centric or
router-centric module define the tax shape first would optimise for execution
convenience over tax completeness — the failure mode the canonical-event model
(Taxes ADR-0001) and "tax reads only the ledger" (Trading ADR-005) both exist
to prevent.

## Consequences
- A clean, testable seam: the adapter is unit-testable with synthetic ledger
  rows and golden-fixture-pinned, exactly like the tax core (Taxes
  `tests/integration`).
- The capital router, when built, consumes already-normalized realized PnL —
  it never sees raw venue quirks or duplicates the mapping.
- New producers (engines, bots) cost one conformance to the ledger/export
  contract, not a new tax integration each.
- Nothing is implemented now: the lab is pre-edge (no live `trade_ledger`
  rows). This ADR freezes the shape; build order is gated (see PROGRESS.md).

## Related
- Trading ADR-005 (canonical contracts), ADR-006 (two books + capital router).
- Taxes ADR-0001 (canonical event model), ADR-0005 (never fabricate basis),
  ADR-0020 (multi-jurisdiction dispatch).
- Adapter laws A1, A4, A9 encode this boundary.
