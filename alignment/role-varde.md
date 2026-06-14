# ROLE — VARDE

> Read [`ECOSYSTEM.md`](ECOSYSTEM.md) first. This card is your lane within it.
> Repo: *(TBD — not yet built / not yet feeding the tax pipeline)*.
>
> **No local override.** If this session needs different ledger, Event, P&L,
> fee, funding, transfer, settlement, or book semantics, do not redefine them
> locally — propose an additive change back to the Tax Adapter alignment folder.

## Status
**Another bot, not yet built out and not yet feeding the Taxes pipeline.** This
card reserves VARDE's place in the topology so it doesn't get bolted on later as
an afterthought. Treat the producer mechanics via
[`role-producer-template.md`](role-producer-template.md) until VARDE has a
distinct, settled purpose — then sharpen this card. Everything below the lane is
**OPEN**; do not invent specifics.

## Your lane
*What happened (you produce it).* VARDE is a strategy/trading producer. When it
goes live it emits fills/exports into the adapter and is **not** a tax,
reporting, or allocation layer.

## What you own (provisional)
- VARDE's strategy logic, execution, and internal ledger.
- Conforming to the adapter's interface — canonical `trade_ledger` rows *or* a
  standalone conforming export (`SCHEMAS.md` §3.4). **Which one is OPEN** until
  VARDE's shape is decided; record the decision here.

## What you must NOT do
- Don't emit tax conclusions or tax P&L — emit *facts*.
- Don't define a private export format — conform to the adapter's contract.
- Don't expect the adapter to read VARDE internals — declared fills/exports only
  (A1).

## OPEN questions to settle before VARDE feeds the pipeline
1. **What is VARDE's distinct purpose?** (If it's just another strategy under an
   existing ledger, it may not need its own export at all — it writes
   `trade_ledger` like the MM lab.)
2. Standalone export vs shared `trade_ledger`?
3. Any instrument types that stress the load-bearing rules (derivatives,
   stablecoin quoting, internal transfers)?

Until these are answered, VARDE is **not wired** and the adapter does not read
it.

## SovereignForge takeaways tagged to you
Inherit the ecosystem invariants (§7) and, once trading is systematic, **A3
classification-defense** — keep activity dated and auditable from the first
fill, because that evidence is impossible to reconstruct after the fact.

## How to request a contract change
Propose additive changes to the **Tax Adapter** alignment folder (export shape)
or the **Trading** session (shared ledger). Never redefine semantics locally.

## Read order
`ECOSYSTEM.md` → this card → [`role-producer-template.md`](role-producer-template.md)
→ adapter [`SCHEMAS.md`](../SCHEMAS.md).
