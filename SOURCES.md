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

## 4. Platform context

**`Documents/SovereignForgeV1`** — broader platform/orchestration context
(`repo/README.md`, `roadmap.md`, `AGENTS.md`, `CLAUDE.md`). Read for the
system-wide module map (market-data / strategy-engine-* / risk / execution /
ledger / pnl / capital-router / tax-export) the adapter slots into. Not a
direct contract dependency.

## 5. Reusable patterns (extract, don't import)

From the existing ecosystem, proven and worth copying into the adapter:
- **Canonical-event normalization** (Taxes ADR-0001) — the adapter is a parser
  in that model: source → canonical, provenance preserved, ambiguity explicit.
- **Deterministic golden fixtures** (Taxes `tests/integration`) — pin the
  adapter's output for known ledgers byte-identical.
- **Counted skip reasons + heartbeat discipline** (PM algo / Trading) — every
  unmapped row counted; `sum(reasons) == n_unmapped`.
- **Decimal-string money handling** (Taxes, PM algo §14/15) — never float.
- **Spec → audit → plan → TDD → verify → document** workflow (Taxes CLAUDE.md).
