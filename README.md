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
  VARDE (varde-fills.csv)  ✅ implemented (NOK spot buy) ─┐
  trading lab (trade_ledger)        spec only             ─┤
  SovereignForge (trade_ledger v3)  spec only, PROPOSED   ─┤
  prediction-market bot (PM algo)   spec only             ─┼──►  tax-adapter  ──►  Taxes/ (events.csv intake)
  arb-bot (own tax_export.csv)      registered, spec only ─┤      (this repo)        → FIFO (NO) / S104 (UK)
  capital-router transfers          spec only             ─┘                         → RF-1159 / UK CGT
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

**Output — canonical tax `Event`** (Taxes `ADR-0001`, `CanonicalEvent`): the
**bilateral** 20-column `events.csv` intake — `event_id, timestamp, event_type,
source_id, source_row_index, asset_out, quantity_out, asset_in, quantity_in,
fee_asset, fee_quantity, income_subtype, label, notes, nok_value_out,
nok_value_in, parser, parser_version, source_type, source_ref` —
jurisdiction-agnostic, `Decimal`-safe, with `event_type ∈ {TRADE, TRANSFER_IN,
TRANSFER_OUT, INCOME, FEE, GIFT_IN, GIFT_OUT, REQUIRES_REVIEW}`. A spot buy or
sell is one **`TRADE`** (both legs) plus a standalone **`FEE`**;
`ACQUISITION`/`DISPOSAL`/`SWAP` are **not** event types (ADR-004).

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

> Last verified: **2026-09-29** · Verify-by: **2026-12-29**, or the next
> producer mapper landing, whichever is first.

**First executable slice landed** (`d89ccb1`, 2026-06-20; ADR-004). Counts, not
adjectives — verified 2026-09-29 with `uv run pytest`: **28 passed, 0 skipped**
(`test_events_shape` 17, `test_varde_hp1` 7, `test_cli` 2, `test_events_columns` 1,
`test_events_conformance` 1 — the last runs against the real Taxes `CanonicalEvent`
when Taxes is importable at its local path and skips otherwise).

| Area | State |
|---|---|
| VARDE NOK-quoted spot **buy** → `TRADE` + `FEE` | ✅ implemented, golden-pinned, byte-identical on re-run |
| VARDE sell / stablecoin-quoted / XRPL transfers | ❌ spec only — mapper raises `NotImplementedError` (fail-closed) |
| Trading `trade_ledger` mapper (HP-1) | ❌ spec only (`SCHEMAS.md §7`); input fixture exists in `Trading`, transport still open |
| SovereignForge / PM algo / arb-bot mappers | ❌ spec only |
| Counted-skip ledger, `REQUIRES_REVIEW` routing, canonical `source_row_index` sort | ❌ not built — see the known-gaps list in `SCHEMAS.md §3.7` |

**One mapping is implemented; everything else in `SCHEMAS.md` is specification.**
The docs now say so at the point of each claim.

### Quick start

```bash
uv sync                                   # dev deps (pytest)
uv run pytest                             # 28 tests
PYTHONPATH=src uv run python -m tax_adapter.cli \
  --producer varde --in tests/fixtures/varde/hp1_nok_spot_buy.csv --out events.csv
```

`PYTHONPATH=src` is **required** for the CLI (the project has no build-system, so
`tax_adapter` is not installed; pytest gets the path from `pyproject.toml`). Layout:
`src/tax_adapter/events.py` (frozen `Event` + shape validation + CSV writer),
`producers/varde.py` (mapper), `cli.py` (`--producer` registry).

See [PROGRESS.md](PROGRESS.md) for the devlog, [SOURCES.md](SOURCES.md) for where
the upstream/downstream contracts live, [HANDOFF.md](HANDOFF.md) for where to pick
up, and [decisions/](decisions/) for the binding scope (ADR-001…004).

## Where this sits in the stack

The stack-wide map lives in **`Documents/Trading Alignment`** (topology, frozen
seams, `event_id` registry, cross-cutting OPEN items, the producer-alignment lint).
This repo's [`alignment/`](alignment/) folder is narrowed to the adapter's role cards
and producer-coordination notes and defers to the hub where they overlap
(`alignment/ECOSYSTEM.md §0`).

## Related repos (read-only references)

| Repo | Role | Path |
|---|---|---|
| `Taxes` | Tax authority of record; owns the canonical Event contract & tax core | `Documents/Taxes` |
| `Trading` | MM research lab; owns `trade_ledger` v3 + the HP-1 fixture (pre-edge, no live rows) | `Documents/Trading` |
| `Offshore trading` (VARDE) | Facts-only producer; the only one with an implemented mapper here | `Documents/Offshore trading` |
| `PM algo` | Standalone Kalshi bot; export contract defined here (`SCHEMAS §3.4`), unbuilt | `Documents/PM algo` |
| `arb-bot` | Registered producer with its own `tax_export.csv` (hub ADR-005); unbuilt here | `Documents/arb-bot` |
| `SovereignForgeV1` | Norway-fork producer (PROPOSED); also methodology reference | `Documents/SovereignForgeV1` |
| `Trading Alignment` | Stack-wide alignment hub (no code) | `Documents/Trading Alignment` |

See [SOURCES.md](SOURCES.md) for the exact files and what each owns.
