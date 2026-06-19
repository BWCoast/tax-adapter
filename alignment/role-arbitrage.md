# ROLE — Arbitrage Bot

> Read [`ECOSYSTEM.md`](ECOSYSTEM.md) first. This card is your lane within it.
> Repo: *(TBD — not yet built / not yet feeding the pipeline)*.
>
> **No local override.** If this session needs different ledger, Event, P&L,
> fee, funding, transfer, settlement, or book semantics, do not redefine them
> locally — propose an additive change back to the Tax Adapter alignment folder.

## Status
**Active ecosystem project, not yet wired.** This card exists so Arbitrage is
first-class in the topology from day one. Most specifics are **OPEN** until the
bot exists; fill them in here as they settle, don't invent them now. When in
doubt, follow [`role-producer-template.md`](role-producer-template.md).

## Your lane
*What happened (you produce it).* You are an arbitrage strategy producer. You
emit fills/exports into the adapter; you are **not** a tax or allocation layer.

## What you own
- Your strategy logic, venue execution, and internal ledger.
- Conforming to the adapter's interface — either by writing canonical
  `trade_ledger` rows (if you run under the Trading ledger) or by a standalone
  export that conforms to the adapter's contract (`SCHEMAS.md` §3.4). **Decide
  which, and record it here (OPEN).**

## What you must NOT do
- Don't emit tax conclusions or compute tax P&L — emit *facts*.
- Don't invent a private export format — conform to the adapter's contract.
- Don't expect the adapter to read your internals — declared canonical
  fills/exports only (A1).

## Arbitrage-specific watch-outs (flag early, decide with the adapter)
Arbitrage tends to stress exactly the load-bearing mapping rules — settle them
*before* live fills accumulate:
- **Multi-leg / multi-venue fills**: each leg is its own fill with its own
  provenance; don't net them into one row.
- **Stablecoin-quoted legs are SWAPs** (two taxable legs), not one-sided
  acquisitions.
- **Cross-venue transfers to rebalance inventory** are linked
  `TRANSFER_OUT`/`TRANSFER_IN` pairs, never disposal+acquisition.
- **Funding/borrow/fee legs** must carry their own `fee_asset` and FX
  `{rate, source, as_of_ts}` at fill time.
- High fill frequency feeds **A3 classification-defense** — keep it auditable.

## What you owe the adapter
Canonical fills (or a conforming export) with: side/price/size/asset/ts, fee +
fee_asset, FX `{rate, source, as_of_ts}` captured at fill time, provenance
chain, and structurally-identical sim/paper/live rows.

## Onboarding & lint
Follow the hub's `ONBOARDING-PRODUCER.md` and keep `tools/producers.json` + this
producer's golden fixture green (`Trading Alignment/tools/check_producer_alignment.py`).

## How to request a contract change
Propose additive changes to the **Tax Adapter** alignment folder (for the export
shape) or the **Trading** session (if you write the shared `trade_ledger`).
Never redefine Event/ledger semantics locally.

## Read order
`ECOSYSTEM.md` → this card → [`role-producer-template.md`](role-producer-template.md)
→ adapter [`SCHEMAS.md`](../SCHEMAS.md) + [`GOTCHAS.md`](../GOTCHAS.md).
