# SOURCES — where the contracts the adapter bridges live

The adapter owns no schema of its own; it owns the *mapping* between two
schemas that live elsewhere, plus the export contracts it imposes on
standalone producers. This file maps where each side lives, who owns it, and
what is reusable. All paths are read-only to this repo.

---

## 1. Downstream — the tax intake contract (authority of record)

**`Documents/Taxes`** — owns the canonical Event and the deterministic tax
core. This is the contract the adapter must satisfy; the adapter is a
*producer* for it, on equal footing with the existing CSV/XRPL parsers.

| file | what it gives the adapter |
|---|---|
| `docs/adr/0001-canonical-event-model.md` | the Event schema + reserved event_id prefixes (the output contract) |
| `docs/adr/0002-fifo-ordering-rules.md` | why `source_row_index` ordering must be deterministic |
| `docs/adr/0005-missing-cost-basis-policy.md` | UNRESOLVED, never fabricate (→ adapter law A2) |
| `docs/adr/0006-valuation-source-policy.md` | 7-tier valuation precedence — the adapter feeds it, doesn't replace it |
| `docs/adr/0007` + `0013` (transfer linking) | how the TRANSFER_OUT/IN pair (A8) gets matched downstream |
| `docs/adr/0010-stablecoin-price-policy.md` | stablecoin FX fallback + mandatory WARNING — relevant to §3.1 SWAP legs |
| `docs/adr/0019-override-system.md` | reversible user corrections downstream of the adapter |
| `docs/adr/0020-multi-jurisdiction-dispatch.md` | same events feed Norway + UK; adapter stays jurisdiction-agnostic |
| `docs/adr/0021-generalized-asset-identity.md` | qualified asset keys (`SYMBOL.contract`) the adapter must emit |
| `README.md` / `CLAUDE.md` | `events.csv` 20-column format, exit codes, "no AI in tax math" |

**Authority rule:** the `Taxes` session owns the Event contract. The adapter
session consumes it and proposes additive changes back — it does not redefine
event semantics (mirrors Trading ADR-005 ownership split).

## 2. Upstream — the trading ecosystem ledger

**`Documents/Trading`** — owns `trade_ledger`, `strategy_intent`,
`canonical_order`, and the book model. This is the adapter's primary input.

| file | what it gives the adapter |
|---|---|
| `SCHEMAS.md` (`trade_ledger` section) | the input row: fields, fill_kind, fx_usdnok_at_fill, decision_id chain |
| `decisions/ADR-005-canonical-contracts.md` | "tax reads only the ledger"; engines emit one schema (→ A1) |
| `decisions/ADR-006-two-book-architecture.md` | lab vs accrual books; the capital-router transfer the adapter must type correctly (A8) |
| `LAWS.md` (L17, L20, L6) | one canonical tax-first ledger, contracts outlive engines, additive schemas |

**Note:** the trading lab is pre-edge (no live realized PnL yet — see Trading
`PROGRESS.md`). `trade_ledger` is designed but not yet emitting live rows. The
adapter is therefore specced now, built when rows exist (PROGRESS.md staging).

## 3. Upstream — the prediction-market bot (standalone, reports back)

**`Documents/PM algo`** — a Kalshi prediction-market bot. Standalone in
execution/ops, but exports into the adapter so capital + tax stay unified.

The adapter **defines the export contract**; PM algo conforms to it. Minimum
export set (see SCHEMAS.md §3.4):
- fills (price, size, side, contract id, ts)
- fees
- realized PnL / resolution payouts
- deposits / withdrawals
- year-end position snapshot if relevant

| file | relevance |
|---|---|
| `CLAUDE.md`, `decisions/ADR-000-jurisdiction.md` | jurisdiction + project framing |
| `decisions/LESSONS_LEARNED.md` | proven collector/accounting lessons (seed below) |
| `docs/RUNTIME_TRUTH.md` | what the bot actually records vs designs |

PM algo's own ledger semantics stay its concern; only the export contract is
shared. The adapter never reaches into its DB or logs (A1).

## 4. Upstream — SovereignForge (Belgium-built bot; Norwegian operator's fork)

**`Documents/SovereignForgeV1`** — **PRODUCER (2026-06-14 promotion, PROPOSED ratification).**
SovereignForge is a single-strategy crypto trading bot. The original (Belgian) operator
runs it for himself; the Norwegian operator has a fork (BWCoast/SovereignForgeV1) that
emits canonical `trade_ledger` v3 rows for this adapter. The fork branch in scope:
`claude/norway-producer-seam` (pushed 2026-06-14).

Producer role:
- Strategy: OFG-DCA (Operator Fib-Grid DCA) on Bybit-EU USDC, spot-only.
- Mechanism: SovereignForge records every fill into its existing DAC8 HMAC chain
  (`data/dac8_fills.jsonl`) for Belgian compliance; a thin translator
  (`src/exports/trade_ledger_export.py`) reads that chain and emits canonical
  `trade_ledger` v3 CSV rows that this adapter consumes read-only.
- Producer identity in exported rows: `account="sf_personal_main"` (operator-overridable),
  `strategy_id="ofg_dca"`, `book="accrual"` (OFG-DCA IS the accrual book per Trading
  ADR-006).
- Reserved `event_id` prefix: `sf:ofg:` (per Taxes ADR-0001 addendum 2026-06-14, PROPOSED).

| file | what it gives the adapter |
|---|---|
| (fork) `src/exports/trade_ledger_export.py` | the `FillRecord → trade_ledger v3` mapper (30 columns, byte-faithful to Trading ADR-007) |
| (fork) `scripts/export_trade_ledger.py` | CLI: `python scripts/export_trade_ledger.py --jurisdiction NO` produces a deterministic CSV at `data/exports/trade_ledger.csv` |
| (fork) `docs/norway_producer_seam_handoff.md` | canonical handoff: field-mapping table (§3), priority-ordered OPEN items (§5), patterns from `TAKEAWAY-SOVEREIGNFORGE.md` (§6) |
| (this repo) `proposals/sf_producer_recognition_PROPOSED.md` | this session's draft of the adapter-side changes — SOURCES (this §4), ECOSYSTEM §4 topology, SCHEMAS §3 footnotes |

**Live-rows status:** SovereignForge's DAC8 chain exists today and contains real
fills. The Norwegian operator's fork can emit `trade_ledger` rows immediately —
independent of MM/Trading lab's HP-1 progression. SF is the **second producer** to
come online for this adapter (after MM/Trading lab).

**Authority rule:** SovereignForge owns its DAC8 chain shape (Belgian operator's
contract); SovereignForge's trade_ledger export conforms to Trading's v3 contract
read-only. SovereignForge does NOT own tax semantics — those remain in this
adapter and the Taxes core (LAWS A4). Additive contract changes flow back to
Trading; tax-treatment questions flow to Taxes.

**Patterns (read-only mining, not contract dependencies):** see
`TAKEAWAY-SOVEREIGNFORGE.md` for the five patterns (A1 Oslo year boundary, A2 FX
tiering, A3 classification defense, A4 tamper-evident ledger, A5 verbatim decimal
strings) and their owner tags. Belgian tax *specifics* (`speculative_33`,
2025-12-31 step-up) do NOT transfer; the *patterns* do.

## 5. Upstream — VARDE (educational Norwegian retail PM; standalone declared export)

**`Documents/Offshore trading`** (repo **VARDE**, `BWCoast/VARDE`) — **PRODUCER
(facts-only; realigned 2026-06-19 per Trading Alignment ADR-004 / OPEN-12).** VARDE is
an educational FastAPI + React trading platform for a single operator. It runs DCA /
Swing / XRPL-MM **spot** strategies across Firi (NOK), Kraken, Binance, ByBit, and XRPL,
recording fills in a local SQLite `Trade` table.

Producer role:
- **Facts-only.** VARDE's own FIFO lot store + Norwegian tax exporter were **removed**
  (OPEN-12); tax output comes from the Taxes core via this adapter, like every other
  producer. VARDE emits declared facts, never tax conclusions.
- **Export contract:** VARDE conforms to the adapter's own export shape (not
  `trade_ledger` v3) — the same per-producer pattern as PM algo (§3). 23-column CSV,
  schema `varde/1`.
- **Producer identity in rows:** `venue` (firi/kraken/binance/bybit), `book` (`lab`),
  `mode` (`live`/`paper`), `strategy_id` (`dca_v1`, …).
- **Reserved `event_id` prefix:** **`varde:`** (Trading Alignment ADR-006 / Taxes
  ADR-0001 addendum, proposed).
- **Instrument scope:** spot only — NOK-quoted (Firi) + USDC/USDT-quoted
  (Kraken/Binance/ByBit) + XRPL wallet↔CEX transfers. No derivatives.

| file | what it gives the adapter |
|---|---|
| (VARDE) `scripts/export_fills.py` | the facts exporter — stdlib-only, append-only, deterministic; writes `db-backup/varde-fills.csv` (schema `varde/1`, 23 cols, verbatim period-decimal, blank-for-missing, `pnl` not exported) |
| (VARDE) `fixtures/export/hp1_nok_spot_buy.csv` | byte-pinned HP-1 golden fixture (Firi BTC/NOK spot buy) — the input the adapter's first VARDE golden test maps (→ SCHEMAS.md §3.7 HP-VARDE-001) |
| (VARDE) `docs/adr/ADR-001-producer-only-tax.md` | VARDE's realignment record (facts-only; capital router deferred to OPEN-11) |
| (this repo) `SCHEMAS.md §3.7` | the `varde-fills.csv` → bilateral `CanonicalEvent` mapping + HP-VARDE-001 worked example |

**Transport:** append-only CSV drop — VARDE writes `varde-fills.csv` into `db-backup/`
alongside `varde.db`; Synology Drive picks both up. The adapter reads the CSV
**read-only**; it never reads `varde.db`. Physical row order = append-by-`source_row_id`;
the adapter applies the canonical `(exchange_ts, trade_id, leg)` sort itself.

**Authority rule:** VARDE owns its strategy logic, `Trade` table, and the
`varde-fills.csv` export shape. It does **not** own tax semantics — those are this
adapter + the Taxes core. VARDE's embedded capital router
(`packages/tax/capital_router.py`) is internal cash-management, **not** tax, and does
**not** flow into the export (CONTRACTS.md §4; deferred to OPEN-11). Additive contract
changes flow back via the alignment folder.

**Live-rows status (verified 2026-09-29):** VARDE produces real fills locally; the
facts export + HP-1 fixture exist and are fixture-verified. **The adapter-side mapper
now exists** for the NOK-quoted spot buy (`src/tax_adapter/producers/varde.py`, vendored
input `tests/fixtures/varde/hp1_nok_spot_buy.csv`, golden `hp1_expected_events.csv`;
ADR-004). Remaining before VARDE feeds the pipeline end-to-end: sell, stablecoin-quoted
and XRPL-transfer mappers, the canonical sort, and the known v1 gaps in SCHEMAS.md
§3.7. Taxes reserved `varde:` (ADR-0001 addendum 2026-07-13) as "not yet emitted" — it
is emitted now.

## 6. Reusable patterns (extract, don't import)

From the existing ecosystem, proven and worth copying into the adapter:
- **Canonical-event normalization** (Taxes ADR-0001) — the adapter is a parser
  in that model: source → canonical, provenance preserved, ambiguity explicit.
- **Deterministic golden fixtures** (Taxes `tests/integration`) — pin the
  adapter's output for known ledgers byte-identical.
- **Counted skip reasons + heartbeat discipline** (PM algo / Trading) — every
  unmapped row counted; `sum(reasons) == n_unmapped`.
- **Decimal-string money handling** (Taxes, PM algo §14/15) — never float.
- **Spec → audit → plan → TDD → verify → document** workflow (Taxes CLAUDE.md).
