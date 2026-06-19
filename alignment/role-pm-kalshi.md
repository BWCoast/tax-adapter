# ROLE — Prediction-Market algo (Kalshi)

> Read [`ECOSYSTEM.md`](ECOSYSTEM.md) first. This card is your lane within it.
> Repo: `Documents/PM algo`.
>
> **No local override.** If this session needs different ledger, Event, P&L,
> fee, funding, transfer, settlement, resolution, or book semantics, do not
> redefine them locally — propose an additive change back to the Tax Adapter
> alignment folder.

## Your lane
*What happened (you produce it).* You are the Kalshi prediction-market bot.
Standalone in execution/ops, but you **export into the adapter** so capital and
tax stay unified. You are a producer.

## What you own
- Your own execution, ops, and internal ledger semantics (your concern, not
  shared).
- Conforming to the adapter's **export contract** — the adapter defines the
  shape; you fill it.

## What you must NOT do
- Don't define your own private tax/export format — conform to the adapter's
  contract instead.
- Don't emit tax conclusions; emit *facts* (fills, fees, payouts).
- Don't expect the adapter to read your DB or logs — it reads only your declared
  export (A1).

## What you owe the adapter (export contract — `SCHEMAS.md` §3.4 minimum set)
- **fills** (price, size, side, contract id, ts)
- **fees**
- **realized PnL / resolution payouts** — a market resolution is a realized
  outcome in the settle asset, **not** an acquisition/disposal of an underlying.
- **deposits / withdrawals**
- **year-end position snapshot** if relevant
- Decimal-string money, provenance, and verify export freshness
  (`run_id`/`git_commit`/generated-time) so a crashed job's stale export isn't
  translated as live.

## OPEN item
The prediction-market export contract is **OPEN** — you define + conform to it
with the adapter (`SCHEMAS.md` §3.4). Until ratified, mark fields OPEN rather
than inventing them.

## SovereignForge takeaways tagged to you
- **A2 — FX tiering**: if any leg touches USD/NOK, carry `{rate, source,
  as_of_ts}` captured at event time.
- **A5 — verbatim decimal strings**: keep Kalshi's exact reported numeric
  strings in the export for audit tie-out.
- **A3 — classification-defense** (ecosystem-wide): systematic automated PM
  trading also feeds the private-vs-business question — keep activity auditable.

## Onboarding & lint
Follow the hub's `ONBOARDING-PRODUCER.md` and keep `tools/producers.json` + this
producer's golden fixture green (`Trading Alignment/tools/check_producer_alignment.py`).

## How to request a contract change
The export contract lives in the adapter's `SCHEMAS.md`. Propose additive
changes to the **Tax Adapter** alignment folder; the adapter ratifies.

## Read order
`ECOSYSTEM.md` → this card → adapter [`SCHEMAS.md`](../SCHEMAS.md) §3.4 → your
`docs/RUNTIME_TRUTH.md` (what the bot actually records vs designs) →
`decisions/LESSONS_LEARNED.md`.
