# ROLE — VARDE

> Read [`ECOSYSTEM.md`](ECOSYSTEM.md) first. This card is your lane within it.
> Repo: `C:\Users\mrkro\Documents\Offshore trading\varde` (local; no GitHub remote yet).
>
> **No local override.** If this session needs different ledger, Event, P&L,
> fee, funding, transfer, settlement, or book semantics, do not redefine them
> locally — propose an additive change back to the Tax Adapter alignment folder.

## Status

**Producer built — export pipeline implemented, not yet wired into a live adapter run.**
VARDE is a running system (FastAPI + SQLite, Windows desktop app; 161 tests).
As of 2026-05-12 the export pipeline is BUILT: the Trade model carries all
adapter-required fields as A5 Decimal strings, `scripts/export_fills.py` produces
the append-only `db-backup/varde-fills.csv`, and the HP-1 golden fixture exists
and is drift-guarded against the live exporter. All three OPEN questions are now
settled and the schema bumps are implemented (see §OPEN items). What remains is
the adapter ingesting `varde-fills.csv` end-to-end (adapter-side work).

## VARDE's distinct purpose (settled 2026-05-12)

Norwegian retail crypto portfolio manager for a single operator. It:
- Manages capital across multiple CEX venues (Firi NOK, Kraken, Binance, ByBit)
  and XRPL, via a shared capital router and strategy runners.
- Runs three strategy types: DCA accumulation, Swing/RSI, and XRPL Market Maker.
- Tracks all fills in a local SQLite database (`varde.db`, `Trade` table).
- Has a capital router (`CapitalAccount`, `CapitalTransaction`) that allocates
  realized gains to tax-reserve, fee-buffer, and accumulation buckets.

VARDE is **distinct from the Trading lab / MM Strategy Bot** — different operator,
different repo, different strategy set, different execution stack. It does not
share the Trading lab's `trade_ledger`.

## Your lane

*What happened (you produce it).* VARDE emits fills as a **standalone export**
that conforms to the adapter's export contract. It is **not** a tax, reporting,
or allocation layer (even though the internal capital router does allocation —
that logic stays internal to Varde and does not flow into the export).

## Export approach (settled 2026-05-12)

**Standalone export** — VARDE will write a read-only, append-only export file
(format TBD: CSV or SQLite snapshot; see OPEN: transport below) from its
`Trade` table. The adapter reads that file; it does not read VARDE's internal
DB directly.

The export will conform to the adapter's minimum set
([`role-producer-template.md`](role-producer-template.md)):
fills, fees with `fee_asset`, deposits/withdrawals, FX at fill time, decimal
strings, provenance chain, export-freshness stamp.

## Instrument types that stress the load-bearing rules (settled 2026-05-12)

Currently **spot-only**. Two quote-currency types are active:

1. **NOK-quoted fills** (Firi: BTC/NOK, XRP/NOK) — simplest case. Maps to
   one-sided `ACQUISITION` (buy) or `DISPOSAL` (sell) + `FEE`. Identical to
   HP-1 (SCHEMAS.md §7). No FX tier needed for `nok_value` (quote already NOK).

2. **Stablecoin/USD-quoted fills** (Binance: BTC/USDT, Kraken: BTC/USD) —
   loads the **SWAP** rule (SCHEMAS.md §3.1): a stablecoin-quoted buy is a
   disposal of the quote + acquisition of the base. `fx_usdnok_at_fill` is
   required for `nok_value`.

3. **XRPL transfers** (between XRPL wallet and CEX) — must emit linked
   `TRANSFER_OUT` / `TRANSFER_IN` pairs, never disposal + acquisition.

No derivatives currently. If VARDE adds perp trading later, that is an
additive schema bump and requires a new OPEN item.

## What you own

- VARDE's strategy logic, execution, and internal `Trade` table.
- Producing a conforming standalone export from that table.
- `fee_asset`, `fill_kind`, `product_type`, `fx_usdnok_at_fill`, and the
  provenance chain are VARDE's responsibility to record at fill time and
  include in the export.

## What you must NOT do

- Don't emit tax conclusions, P&L characterization, FIFO/S104, or valuations.
- Don't define a private export format — conform to the adapter's contract.
- Don't expect the adapter to read `varde.db` directly.
- Don't compute or export `nok_value` — that's the adapter's job (using
  `fx_usdnok_at_fill` you supply).
- Don't embed allocation logic (tax-reserve routing, capital-bucket splits)
  in the export. The capital router is internal to VARDE.

## Export schema gaps — IMPLEMENTED 2026-05-12

> All fields in the table below have been ADDED to the `Trade` model
> (`apps/api/models.py`) and are surfaced by `scripts/export_fills.py`. The table
> is retained as the rationale record. `decision_id` / `git_commit` were NOT added
> (deferred — not required for HP-1; `strategy_id`/`run_id` cover provenance for now).

VARDE's `Trade` model now covers:
`id, user_id, exchange, symbol, side, qty, price, fee, ts, pnl, status, fee_asset,
fill_kind, product_type, fx_usdnok_at_fill, order_id, trade_id, strategy_id, book,
mode, run_id`

Fields the adapter required that VARDE's `Trade` table previously lacked (now added):

| Missing field | Needed for | Priority |
|---|---|---|
| `fee_asset` | FEE event `asset` field | HIGH — blocks any FEE mapping |
| `fill_kind` | maker/taker/funding routing | HIGH — blocks correct event_type |
| `product_type` | spot vs derivative guard | HIGH — blocks load-bearing rule enforcement |
| `fx_usdnok_at_fill` | `nok_value` for non-NOK fills | HIGH — blocks USDT-quoted mapping |
| `order_id` / `trade_id` | deterministic `event_id` | HIGH — blocks `ledger:{run_id}:{trade_id}:{leg}` |
| `decision_id` / `strategy_id` | provenance chain | MEDIUM |
| `book` | `source_id` (`trade_ledger:lab` vs `:accrual`) | MEDIUM |
| `mode` | live/paper/sim provenance | MEDIUM |
| `run_id` / `git_commit` | export-freshness + `event_id` | MEDIUM |
| `schema_version` | contract-version pinning | LOW |

The local `pnl` column is a VARDE-internal performance tracker, not an
export field. The adapter does not consume it. Do not confuse it with
`realized_pnl_quote` (adapter field for derivative fills — not applicable to
VARDE spot trades).

## OPEN items

```
SETTLED + IMPLEMENTED: VARDE export transport (decided 2026-05-12, built 2026-05-12)
  decision:        CSV drop — VARDE writes varde-fills.csv to db-backup/ alongside
                   varde.db. Synology Drive picks both up. Adapter reads CSV; never
                   reads varde.db directly. Rows are appended only; no in-place
                   mutation of historical rows.
  ordering:        PHYSICAL file order is append order by source_row_id (= Trade.id,
                   monotonic, the deterministic dedup key — export resumes from
                   max(source_row_id) already in the file). The adapter applies the
                   CANONICAL sort (exchange_ts, trade_id) on its own side; it must not
                   assume physical row order equals canonical order.
  implementation:  VARDE scripts/export_fills.py — stdlib-only (sqlite3+csv), 23-col
                   COLUMNS contract, append-only, UTF-8, verbatim period-decimal
                   qty/price/fee, blank-for-missing (never 0), realized_pnl_quote="0"
                   (spot), pnl NOT exported, schema_version="varde/1". Tolerates a
                   pre-migration DB (PRAGMA-gated optional columns).
  target_doc:      VARDE scripts/export_fills.py + adapter SOURCES.md (pending)

IMPLEMENTED: VARDE Trade model schema bumps (2026-05-12)
  owner:           VARDE (implemented)
  was_blocking:    producing a contract-faithful export row
  done:            apps/api/models.py — qty/price/fee migrated Float→Text (A5 verbatim
                   Decimal strings); added 10 nullable Text columns: fee_asset,
                   fill_kind, product_type, fx_usdnok_at_fill, order_id, trade_id,
                   strategy_id, book, mode, run_id. apps/api/database.py —
                   _migrate_trade_schema(engine) (two-phase: REAL→TEXT rename+recreate
                   preserving NULLs; ALTER ADD COLUMN for missing cols), wired into
                   init_db(); idempotent across all 4 DB states. Backward-compatible:
                   new cols nullable, filled on new fills only.
  target_doc:      VARDE apps/api/models.py + apps/api/database.py

IMPLEMENTED: VARDE HP-1 fixture (2026-05-12)
  owner:           VARDE (produced) — Tax Adapter still to confirm contract-faithful
  was_blocking:    adapter building its first VARDE golden fixture
  done:            fixtures/export/hp1_nok_spot_buy.csv — one Firi BTC/NOK spot BUY
                   (qty 0.05, price 600000, fee 150 NOK), generated by the real
                   export_fills then frozen (fixed run_id/generated_at). Header is
                   drift-guarded == export_fills.COLUMNS; a consistency test re-runs
                   the live exporter and compares every column except the two
                   clock-derived provenance fields. nok_value intentionally absent
                   (adapter computes 0.05 x 600000 = 30000.00 NOK).
  target_doc:      VARDE fixtures/export/hp1_nok_spot_buy.csv
                   + tests/fixtures/test_hp1_fixture.py
```

## SovereignForge takeaways tagged to you

Inherit ecosystem invariants (§7). Priority for VARDE:

- **A3 classification-defense**: record that parameters were set by the operator,
  not the algorithm. Capture `strategy_id`, `mode`, `decision_id` from the first
  fill — impossible to reconstruct later.
- **A4 tamper-evident ledger**: consider a row-hash chain on `Trade` inserts —
  the `AuditLog` table partially covers this but is not append-only fill provenance.
- **A5 verbatim decimal strings**: `Trade.qty/price/fee` are currently `Float` —
  they must become `Text` (Decimal strings) before export. A schema migration is
  needed (same pattern as `CapitalAccount.balance` which already uses `Text`).

## Onboarding & lint
Follow the hub's `ONBOARDING-PRODUCER.md` and keep `tools/producers.json` + this
producer's golden fixture green (`Trading Alignment/tools/check_producer_alignment.py`).

## How to request a contract change

Propose additive changes to the **Tax Adapter** alignment folder (export shape)
or the **Trading** session (shared ledger). Never redefine Event/ledger semantics
locally.

## Read order

`ECOSYSTEM.md` → this card → [`role-producer-template.md`](role-producer-template.md)
→ adapter [`SCHEMAS.md`](../SCHEMAS.md) §3.4.
