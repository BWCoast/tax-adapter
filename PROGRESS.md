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
