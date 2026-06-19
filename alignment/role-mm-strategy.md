# ROLE — MM Strategy Bot / Trading lab

> Read [`ECOSYSTEM.md`](ECOSYSTEM.md) first. This card is your lane within it.
> Repo: `Documents/Trading`.
>
> **No local override.** If this session needs different ledger, Event, P&L,
> fee, funding, transfer, settlement, or book semantics, do not redefine them
> locally — propose an additive change back to the Tax Adapter alignment folder.

> **You are first.** Per [`ADR-003`](../decisions/ADR-003-first-end-to-end-producer-mm-spot.md),
> MM Strategy / Trading lab is the **first producer wired end-to-end**, because
> `trade_ledger` is already a frozen contract. The first happy path is
> **spot-only** (one fiat-quoted spot buy → `ACQUISITION` + `FEE`), pinned in
> adapter [`SCHEMAS.md`](../SCHEMAS.md) §7. Your gating contribution: settle the
> `trade_ledger → adapter` **transport** (ECOSYSTEM §8 OPEN item).

## Your lane
*What happened (you produce it).* You are the market-making / funding strategy
lab. You own `trade_ledger` and the engines that write it. You are the primary
**producer** the adapter reads.

## What you own
- `trade_ledger`, `strategy_intent`, `canonical_order` and the two-book model
  (ADR-005 canonical contracts, ADR-006 lab vs accrual).
- The fill row: `book` (`lab`|`accrual`), `fill_kind`, `fee`/`fee_asset`,
  `realized_pnl_quote`, `fx_usdnok_at_fill`, and the `decision_id → order →
  intent → experiment_hash` provenance chain (LAWS L17/L20/L6/L21).
- Strategy logic, quoting, sizing, risk staging.

## What you must NOT do
- Don't emit tax conclusions or compute P&L for tax — you emit *fills*; the
  adapter normalizes and Taxes characterizes.
- Don't grow a private "export to tax" format — the canonical `trade_ledger`
  *is* the interface; the adapter reads only that, never your venue payloads or
  bot DB.
- Don't reconstruct a tax fact after the fact — capture it at fill time or mark
  it absent.

## What you owe the adapter
- Canonical `trade_ledger` rows, sim/paper/live structurally identical (the
  adapter maps on `mode` provenance, not structure).
- FX as `{rate, source, as_of_ts}` captured at fill time (A2) — not a constant,
  not a daily close unless that *is* the source.
- Book transfers expressed so the adapter can emit a linked
  `TRANSFER_OUT`/`TRANSFER_IN` pair (never disposal+acquisition).
- Settled transport for handing rows to the adapter (OPEN item — you own this
  decision with the adapter).

## SovereignForge takeaways tagged to you
- **A3 — classification-defense** ⭐⭐⭐ (with Taxes): make the discretionary
  posture *structural and audited* — operator sets parameters; each parameter
  set/change is journaled, dated, signed. The two-book split (neutral lab vs
  conviction accrual) is itself defensible structure; make the accrual router's
  operator-triggered buys explicit and logged.
- **A4 — tamper-evident ledger** ⭐: make the insert-only ledger
  *cryptographically* append-only — per-row `prev_hash`/`row_hash`. Decide in a
  Trading ADR; pairs with A3's discretion journal.
- **A2 — FX tiering** ⭐: populate `fx_usdnok_at_fill` from a timestamped source
  with `{rate, source, as_of_ts}`.
- **Part B (B1–B5)**: risk/ops/execution patterns (integrity-vs-performance
  halt split, clock-skew halt, watchdog supervision, idempotent orders) — gated
  on a validated strategy (ADR-003). Reference, not now.

## Onboarding & lint
Follow the hub's `ONBOARDING-PRODUCER.md` and keep `tools/producers.json` + this
producer's golden fixture green (`Trading Alignment/tools/check_producer_alignment.py`).

## How to request a contract change
You own `trade_ledger` — ratify additive bumps in your own ADRs. For Event/tax
needs, file the request to the Tax Adapter alignment folder.

## Read order
`ECOSYSTEM.md` → this card → your `SCHEMAS.md` (`trade_ledger`) + `ADR-005/006`
+ `LAWS.md` (L17/L20/L21) → adapter [`SCHEMAS.md`](../SCHEMAS.md) (how your rows
become Events).
