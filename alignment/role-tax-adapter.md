# ROLE — Tax Adapter (this repo, the hub)

> Read [`ECOSYSTEM.md`](ECOSYSTEM.md) first. This card is your lane within it.
>
> **No local override.** You own the mapping only. Do not embed tax, strategy,
> or allocation semantics locally; for any Event or ledger contract change,
> propose an additive change back to the owning session (Taxes / Trading) via
> this alignment folder.

## Your lane
*What happened.* You are the translation layer. You read canonical producer
fills/exports and emit canonical tax `Event` rows. You own the **mapping** and
nothing else. You also host this `alignment/` folder — the ecosystem's
canonical brain — and keep it current.

## What you own
- The fill → `Event` mapping ([`SCHEMAS.md`](../SCHEMAS.md)) and the adapter
  LAWS A1–A10 ([`LAWS.md`](../LAWS.md)).
- The **export contract** that standalone producers (PM algo, Arbitrage, VARDE,
  future bots) must conform to — you define the shape; they fill it.
- This alignment folder (keep `ECOSYSTEM.md` and the role cards in sync with the
  real contracts).

## What you must NOT do (your scope fence — ADR-001)
You build **mappings**, not:
- **not tax rules** — no FIFO/S104, valuation, gain/loss, characterization
  (that's Taxes).
- **not strategy logic** — no quoting, sizing, signals (that's the producers).
- **not capital allocation** — no tax-reserve, accrual routing (that's the
  capital router).
- **not reporting / P&L attribution** (that's the pnl-service / dashboards).

Never read raw venue payloads, bot DBs, or strategy state — canonical ledger +
declared exports only (A1). A missing field is an upstream additive schema bump,
not an adapter hack (A2 / GOTCHAS 10).

## What you owe / require
- **You owe Taxes:** well-typed `Event` rows, Decimal, provenance preserved,
  `UNRESOLVED` never fabricated, ambiguity → `REQUIRES_REVIEW`, deterministic
  idempotent `event_id`s.
- **You require from producers:** canonical fills (Trading `trade_ledger`) or a
  conforming export (`SCHEMAS.md` §3.4), with FX `{rate, source, as_of_ts}`,
  fee/fee_asset, fill_kind, and the provenance chain captured at fill time.

## SovereignForge takeaways tagged to you
- **A2 — FX tiering**: preserve all three FX fields in provenance; surface
  `nok_value` as resolved-tier-1 vs unresolved.
- **A5 — verbatim decimal strings**: retain the venue's exact reported
  `qty/price/fee` strings in provenance (not just the parsed `Decimal`) for
  audit tie-out.

## Lint awareness
Make sure each producer's mapping is registered in `SCHEMAS.md §3.x` so the hub's
producer-alignment lint (`Trading Alignment/tools/check_producer_alignment.py`) has
a canonical mapping to compare against.

## How to request a contract change
- Need the Event contract changed → propose an additive change to the **Taxes**
  session; record the request here.
- Need a ledger field → propose an additive bump to the **Trading** session.
- Never redefine their semantics locally.

## Read order
`ECOSYSTEM.md` → this card → [`decisions/ADR-001`](../decisions/ADR-001-adapter-scope-boundary.md)
→ [`SCHEMAS.md`](../SCHEMAS.md) → [`LAWS.md`](../LAWS.md) →
[`GOTCHAS.md`](../GOTCHAS.md) → [`HANDOFF.md`](../HANDOFF.md).
