# ROLE — Producer (generic template for new/future builds)

> Read [`ECOSYSTEM.md`](ECOSYSTEM.md) first. Copy this card to
> `role-<name>.md` when a new producer becomes a first-class ecosystem project.
> Repo: *(fill in)*.

## Your lane
*What happened (you produce it).* You are a producer of financial activity —
fills, fees, funding, payouts, deposits/withdrawals, transfers. You emit *facts*
into the adapter and nothing about *what they meant for tax* or *what to do with
the money*.

## What you own
- Your strategy/execution logic and internal ledger.
- Conforming to the adapter's interface. Choose one:
  - **Write canonical `trade_ledger` rows** (run under the Trading ledger), or
  - **Emit a standalone export** that conforms to the adapter's export contract
    (`SCHEMAS.md` §3.4 minimum set).
  - Record which, here.

## What you must NOT do
- **Not tax rules** — no characterization, FIFO/S104, valuation, gain/loss.
- **Not allocation** — no tax-reserve, capital routing.
- **Not reporting / P&L attribution.**
- Don't invent a private "export to tax" format; conform to the contract.
- Don't expect the adapter to read your internals — declared canonical
  fills/exports only (A1). A missing field is an upstream additive schema bump.

## What you owe the adapter (minimum)
- Fills: side, price, size, qualified asset, timestamp.
- Fees with `fee_asset`.
- Realized PnL / payouts in the **settle asset** (derivatives & resolutions are
  not acquisitions/disposals of an underlying).
- Deposits / withdrawals; transfers expressed as linkable
  `TRANSFER_OUT`/`TRANSFER_IN` pairs.
- FX as `{rate, source, as_of_ts}` captured at fill time (A2).
- Decimal-string money; verbatim venue strings retained (A5); provenance chain;
  structurally-identical sim/paper/live rows; export-freshness stamp
  (`run_id`/`git_commit`/generated-time).

## Inherited invariants (non-negotiable — see ECOSYSTEM §5)
Decimal-only · never fabricate (UNRESOLVED) · ambiguity → `REQUIRES_REVIEW` ·
provenance preserved · deterministic + idempotent · append-only/auditable ·
counted skips (`sum(reasons) == n_dropped`).

## SovereignForge takeaways
Inherit all ecosystem invariants. Once trading is systematic, **A3
classification-defense**: keep activity dated, signed, and auditable from the
first fill.

## How to request a contract change
Propose additive changes to the **Tax Adapter** alignment folder (export shape)
or the **Trading** session (shared `trade_ledger`). Mark unsettled fields OPEN
and name the owner. Never redefine Event/ledger semantics locally.

## Read order
`ECOSYSTEM.md` → this card → adapter [`SCHEMAS.md`](../SCHEMAS.md) §3.4 +
[`GOTCHAS.md`](../GOTCHAS.md).
