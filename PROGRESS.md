# PROGRESS — lab notebook

Newest entries at the bottom of each day; newest day at the bottom.

## 2026-06-14

- **[Step 1] Scoped the adapter against both live contracts** (read-only mine
  of `Documents/{Taxes, Trading, PM algo, SovereignForgeV1}`). Established the
  two anchors the adapter bridges:
  - **Downstream / output:** `Taxes` canonical Event (ADR-0001) — 20-column
    `events.csv`, jurisdiction-agnostic, Decimal-safe, `event_type ∈
    {DISPOSAL, ACQUISITION, INCOME, FEE, TRANSFER_IN, TRANSFER_OUT, SWAP,
    REQUIRES_REVIEW}`, qualified asset keys (ADR-0021), UNRESOLVED never
    fabricated (ADR-0005).
  - **Upstream / input:** `Trading` `trade_ledger` (frozen by ADR-005/L17) —
    one row per fill, `book` (lab|accrual, ADR-006), `fill_kind`,
    `fx_usdnok_at_fill` captured at fill time, `decision_id → order → intent`
    provenance chain.
  - **Also upstream:** `PM algo` standalone prediction-market bot — exports
    fills/fees/PnL/transfers into the adapter via a contract the adapter
    defines.
- **[Step 2] Froze the scope fence** (decisions/ADR-001). The module is
  **translation only**: adapter = *what happened*, tax core = *what it meant*,
  capital router = *what to do with the money*. Allocation, reporting, P&L
  attribution, strategy logic, and venue payloads are all explicitly out of
  scope and owned elsewhere. Ownership model mirrors Trading ADR-005: `Taxes`
  owns the Event contract, `Trading` owns the ledger, this session owns the
  mapping + the export contract for standalone producers.
- **[Step 3] Wrote LAWS** (A1–A10) — each traceable to a Taxes ADR, a Trading
  law, or a PM algo scar: read only the canonical ledger (A1), never fabricate
  (A2), ambiguity → REQUIRES_REVIEW (A3), no tax math (A4), deterministic +
  idempotent (A5), provenance preserved (A6), Decimal only (A7), internal book
  transfers are transfers not disposals (A8), scope fence (A9), event_id
  namespace verified collision-free (A10).
- **[Step 4] Wrote the mapping spec** (SCHEMAS.md) — the load-bearing table:
  spot legs (incl. stablecoin = SWAP), derivative realized-PnL/funding (no
  underlying transfer), capital-router book transfers (linked TRANSFER_OUT/IN),
  prediction-market resolutions, and the determinism/idempotency rules.
- **[Step 5] Deferred derivative & resolution characterization** (ADR-002):
  emit faithful realized-PnL events with provenance; let the tax core classify
  capital-vs-income; `REQUIRES_REVIEW` until the core has an explicit rule.
- **[Step 6] Seeded SOURCES, LESSONS_LEARNED, GOTCHAS, README, CLAUDE.md** from
  the two contracts + PM algo's accounting lessons (via Trading's distillation).

### Build staging (gated, mirrors Trading's discipline)
> *Historical (2026-06-14) — superseded: a first slice (VARDE) is implemented; see
> the 2026-09-29 entry below and ADR-004.*

Nothing is implemented yet, by design.

| gate | unlocks |
|---|---|
| `Taxes` Event contract confirmed stable for adapter intake (it is — ADR-0001) | mapping spec frozen ✅ (this commit) |
| `Trading` lab produces live `trade_ledger` rows (currently pre-edge — see Trading PROGRESS.md) | build the ledger→Event mapper (TDD, golden fixtures) |
| PM algo export contract agreed | build the prediction-market export adapter |
| capital router live (Trading ADR-006) | wire the TRANSFER_OUT/IN book-transfer path (A8) |

- **[Step 7] Built the `alignment/` coordination layer** — one canonical
  `ECOSYSTEM.md` (topology, ownership, binding-priority, anti-patterns, shared
  invariants, structured OPEN items, owner-tagged SovereignForge takeaways) +
  thin per-session role cards (Taxes, Tax Adapter, MM/Trading, PM/Kalshi,
  Arbitrage, VARDE, generic producer template) + a README with per-session
  paste-prompts and a rollout checklist. Hub-only model: sibling repos read it
  read-only; no copies to drift. This is the "one canonical brain prevents
  session drift" lesson made structural.
- **[Step 8] Picked the first end-to-end path** (decisions/ADR-003): **MM
  Strategy / Trading lab** is the first producer wired (its `trade_ledger`
  contract is already frozen), and the first happy path is **spot-only** — a
  fiat-quoted spot buy → one `ACQUISITION` + one `FEE`. Worked example pinned in
  SCHEMAS.md §7 (Happy Path 1); becomes the first golden fixture. HP-2 (swap) /
  HP-3 (derivative) extend the spine later. This raises the `trade_ledger →
  adapter` transport (open item 2) to the gating unknown for HP-1.

### Open questions / next steps
> *Historical (2026-06-14). Items 1–3 are superseded — prefixes ratified 2026-07-13,
> transport format settled by Trading ADR-007, PM export still unbuilt (see the
> 2026-09-29 entry). Item 4 still applies.*

1. **Confirm with the `Taxes` session** that `ledger:`/`pm-algo:` event_id
   prefixes are acceptable and reserved (A10) — propose as an ADR-0001 addendum
   note on their side.
2. **Agree the `trade_ledger` → adapter handoff mechanism** with the `Trading`
   session (file drop of canonical rows? a shared read-only export? format).
   The adapter reads canonical rows only (A1) — settle the transport, not the
   schema.
3. **Define the PM algo export contract** concretely (SCHEMAS §3.4 minimum
   set) and have the PM algo session conform.
4. **Build only against real exported rows or schema-faithful fixtures** — not
   an imagined shape; re-verify when the first live ledger lands (GOTCHAS 11).

## 2026-06-18

- **[Step 9] Read the `Trading Alignment/` stack hub** (created 2026-06-17 — a
  no-code, stack-wide alignment repo covering all five pipeline stages; it names
  this repo's `alignment/ECOSYSTEM.md` as its precursor). **Operator decision:
  `Trading Alignment/` is the canonical stack-wide hub**; this folder narrows to
  the adapter's role cards + producer coordination, with a pointer up
  (`ECOSYSTEM.md §0`). Cross-cutting OPEN items are now authoritative in
  `Trading Alignment/GAPS.md` (OPEN-1…13).
- **Status deltas confirmed upstream:** HP-1 fixture row exists
  (`Trading/fixtures/trade_ledger/hp1_spot_buy.csv`, matches SCHEMAS §7);
  transport = deterministic CSV exporter (Trading ADR-007), mechanism still open;
  `event_id` registry formalized + Taxes-owned (Trading Alignment ADR-006 + Taxes
  ADR-0001-addendum). Producers registered: arb-bot (`arb:`), VARDE (`varde:`),
  SF-NO fork (`sf:ofg:`). The VARDE session has filled in `role-varde.md` (it's
  the `Offshore trading` repo).
- **[Step 10 — FINDING] `SCHEMAS.md` misrepresents the `events.csv` contract.**
  Verified against `Taxes/src/tax_core/models/event.py`: the real `CanonicalEvent`
  is **bilateral** (`asset_out/in`, `quantity_out/in`, `fee_asset/quantity`,
  `nok_value_out/in`, 4 provenance keys) with `event_type ∈ {TRADE, TRANSFER_IN/OUT,
  INCOME, FEE, GIFT_IN/OUT, REQUIRES_REVIEW}`. Our §1/§7 use single-sided
  `ACQUISITION/DISPOSAL/SWAP` + `asset/quantity/nok_value` — which the Taxes model
  rejects at construction. Recorded as a FINDING in `ECOSYSTEM.md §8`.
  **Resolution (operator): do NOT align the adapter to the Firi parser; a dedicated
  build/P&L adapter will reconcile the output shape.** `SCHEMAS.md` left unchanged
  (record-only) pending that work.

## 2026-06-19 → 2026-06-20  *(back-filled 2026-09-29 from git + docs/superpowers/)*

- **[Step 11] Registered VARDE as a producer** (`c0357a2`, 2026-06-19): `SCHEMAS.md
  §3.7` (bilateral mapping + HP-VARDE-001) and `SOURCES.md §5`. §3.7 was written
  natively in the real `CanonicalEvent` shape — the first section to be.
- **[Step 12] Genesis design + plan, then the first code** (`docs/superpowers/specs/
  2026-06-19-tax-adapter-genesis-design.md`, `…/plans/2026-06-19-…-plan.md`;
  `d89ccb1`, 2026-06-20 "bootstrap tax adapter with VARDE mapper and HP-1"): a tiny
  `uv` package — frozen `Event` dataclass mirroring the 20-column `events.csv` with
  construction-time shape validation, the VARDE mapper, a `--producer` CLI, golden
  HP-1 fixtures, an optional real-`CanonicalEvent` conformance test. Decisions
  formalised in ADR-004.

## 2026-09-29  *(docs reconciliation — no code or test changed)*

- **[Step 13] Verified the tree before documenting it** (M4, counts not
  adjectives): `uv run pytest` → **28 passed, 0 skipped** (`test_events_shape` 17,
  `test_varde_hp1` 7, `test_cli` 2, `test_events_columns` 1,
  `test_events_conformance` 1). CLI re-run on the HP-1 fixture is byte-identical
  and equals `hp1_expected_events.csv`. The CLI **fails without `PYTHONPATH=src`**
  (no build-system) — documented in README.
- **[Step 14] Three spec-vs-code gaps confirmed by execution, then labelled** (M2):
  a zero fee still emits a `FEE` event; a blank fee crashes with a bare
  `decimal.InvalidOperation`; `source_row_index` follows input order, not the
  documented `(exchange_ts, trade_id, leg)` sort. Plus the counted-skip ledger and
  the rich provenance dict are unbuilt. Listed in `SCHEMAS.md §3.7`.
- **[Step 15] Re-verified upstream instead of trusting the 06-18 read**: hub OPEN-1
  **closed 2026-07-13**; Taxes ADR-0001 addendum reserves `ledger:`, `arb:`, `varde:`
  as `event_id` prefixes but ratifies **`pm-algo:` only as a `provenance.algo`
  label** (so the PM mapper's `event_id` prefix is unreserved — new OPEN); Trading
  ADR-007 settles the transport *format*; the `hp1_spot_buy.csv` fixture is
  identical to `SCHEMAS §7.1`. The hub itself lags on all three (`CONTRACTS.md` §3,
  OPEN-2/3, worked examples A/B).
- **[Step 16] Docs reconciled** (this commit): `SCHEMAS.md` §1/§3.1/§3.3/§7 to the
  bilateral model + status banners; **ADR-004** (amends ADR-003); README status /
  quick start / repos; `HANDOFF.md` rewritten to current state; `CLAUDE.md`;
  `LESSONS_LEARNED` / `GOTCHAS` from the real build; `SOURCES.md §5`;
  `alignment/ECOSYSTEM.md` topology + §8 (FINDING → RESOLVED). Not touched: the
  `PROPOSED` HP-SF-001 rows (banner only) and other repos' docs (flagged in
  `HANDOFF.md`).
