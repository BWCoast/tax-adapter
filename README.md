# tax-adapter

The **translation layer** between the trading/bot ecosystem and the tax
software. It reads canonical fills (and exports) from the engines and emits
canonical tax **Event** rows that the `Taxes` software ingests — and nothing
more.

A one-sentence boundary:

> The adapter answers **"what happened"** (normalize fills/fees/transfers into
> tax events with provenance). It never answers **"what it meant for tax"**
> (the deterministic tax core does that) or **"what to do with the money"**
> (the capital router does that).

## Why this exists as its own module

The ecosystem has many producers of financial activity — the MM/funding lab
strategies, the prediction-market bot, the DCA/accrual buys, future engines —
and one tax authority of record (`Taxes/`). Without a single normalizing
bridge, every engine would grow its own private "export to tax" format, and
the deterministic tax core would need source-specific logic per bot. That is
exactly the combinatorial coupling the tax software's ADR-0001 (canonical
event model) was written to forbid.

So: **many producers, one canonical ledger, one adapter, one tax intake.**

```
  trading lab (trade_ledger)  ─┐
  prediction-market bot        ─┤
  DCA / accrual buys           ─┼──►  tax-adapter  ──►  Taxes/ (events.csv intake)
  capital-router transfers     ─┤      (this repo)        → FIFO (NO) / S104 (UK)
  exchange CSVs (manual)       ─┘                         → RF-1159 / UK CGT
```

## What it is NOT (scope fence — see [decisions/ADR-001](decisions/ADR-001-adapter-scope-boundary.md))

| Not this | Lives in | Why separate |
|---|---|---|
| The tax calculation (FIFO, S104, valuation, gain/loss) | `Taxes/` deterministic core | Tax math is pure, audited, jurisdiction-aware; the adapter must never embed it (Taxes Rule 1; Trading ADR-005 "tax reads only the ledger") |
| The capital router (tax-reserve, accrual allocation) | future `capital-router` (Trading ADR-006) | Allocation is a *decision* downstream of realized PnL; translation is not a decision |
| P&L attribution / reporting / dashboards | future `pnl-service` | Interpretation, not translation |
| Strategy logic, quoting, sizing | the engines (Trading ADR-005, L16) | Strategies propose; they do not own accounting |
| Venue-native payload handling | venue adapters in the trading repo | The adapter reads the *canonical* ledger, never raw venue payloads (Trading L20) |

## The two contracts it bridges

**Input — canonical `trade_ledger`** (Trading `SCHEMAS.md`, frozen by ADR-005):
one row per fill, sim/paper/live structurally identical, tagged `book`
(`lab`|`accrual`) and carrying `fill_kind`, `fee`/`fee_asset`,
`realized_pnl_quote`, `fx_usdnok_at_fill` (captured at fill time), and the
`decision_id → order → intent → experiment_hash` provenance chain.

**Output — canonical tax `Event`** (Taxes `ADR-0001`): the 20-column
`events.csv` intake — `event_id, timestamp, event_type, asset, quantity,
nok_value, source_id, source_row_index, provenance` — jurisdiction-agnostic,
`Decimal`-safe, with `event_type ∈ {DISPOSAL, ACQUISITION, INCOME, FEE,
TRANSFER_IN, TRANSFER_OUT, SWAP, REQUIRES_REVIEW}`.

The full field-by-field mapping (including the load-bearing cases —
derivatives realized-PnL, funding, internal book transfers, prediction-market
resolutions) is in [SCHEMAS.md](SCHEMAS.md).

## Design principles

See [LAWS.md](LAWS.md). Headlines: read only the canonical ledger (A1), never
fabricate basis or value (A2 — inherited from Taxes ADR-0005), ambiguity
becomes `REQUIRES_REVIEW` never a safer-looking guess (A3), no tax math in the
adapter (A4), deterministic + idempotent `event_id`s stable across re-imports
(A5), provenance preserved end-to-end (A6), `Decimal` only (A7).

## Status

**Scoping stage.** Contracts on both sides are read and pinned; the mapping
spec and scope fence are written. Nothing implemented yet — by design, the
adapter is built only once there are live `trade_ledger` rows to translate
(Trading's lab is pre-edge; see Trading `PROGRESS.md`). See
[PROGRESS.md](PROGRESS.md) for the devlog, [SOURCES.md](SOURCES.md) for where
the upstream/downstream contracts live, and
[decisions/](decisions/) for the frozen scope.

## Related repos (read-only references)

| Repo | Role | Path |
|---|---|---|
| `Taxes` | Tax authority of record; owns the canonical Event contract & tax core | `Documents/Taxes` |
| `Trading` | Lab/accrual engines; owns `trade_ledger`, intent, order contracts | `Documents/Trading` |
| `PM algo` | Standalone prediction-market bot; exports fills/PnL to the adapter | `Documents/PM algo` |
| `SovereignForgeV1` | Broader platform context | `Documents/SovereignForgeV1` |

See [SOURCES.md](SOURCES.md) for the exact files and what each owns.
