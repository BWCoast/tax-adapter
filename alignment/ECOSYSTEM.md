# ECOSYSTEM — canonical alignment for all tax/trading sessions

> **Status:** binding · **Owner:** Tax Adapter session (this repo) · **Updated:** 2026-06-14
>
> This is the shared mental model for every session in the ecosystem. Read it
> before doing tax/trading/reporting work in *any* repo. It does not replace a
> repo's own ADRs/LAWS/SCHEMAS — it tells you how the repos fit together, who
> owns what, and the invariants none of them may break. Where this doc and an
> owning repo's contract disagree, **the owning repo wins** (see §3 precedence)
> and this doc is stale — fix it.

---

## 1. Purpose

Many producers of financial activity, one tax authority of record. Without a
single shared alignment, every session reinvents ledger/Event/PnL/fee/transfer
semantics locally and they drift. This folder is the **one canonical project
brain** that keeps them aligned. One canonical brain prevents session drift.

## 2. The one-sentence boundary

> **adapter = what happened · tax core = what it meant · capital router = what
> to do with the money**

Memorize this. Almost every "which session owns this?" question resolves by
asking which of the three clauses the work belongs to.

## 3. Binding priority (precedence)

When two sources seem to conflict, resolve in this order (highest wins):

1. **The owning repo's contract for its own domain** — the authoritative source
   for anything that repo owns. Specifically, the **Taxes Event contract**
   (ADR-0001) for tax requirements / Event semantics, and each producer's own
   ledger/export contract for its fields.
2. **`ECOSYSTEM.md`** (this file) for the *ecosystem boundary* — topology,
   ownership lanes, cross-session invariants, coordination protocol.
3. **Accepted ADRs** (any repo) for decisions of record within their scope.
4. **Role cards** (`role-*.md`) for per-session behaviour.
5. **README paste-prompts** for session bootstrapping.

Read it as: *owning-repo contract* beats *this doc* on the contract's own
content; *this doc* beats role cards and prompts on how the pieces fit. If you
find a real conflict, don't paper over it — fix the lower-priority doc and note
it. A stale alignment doc is a bug, not an authority.

## 4. Topology — producers → adapter → tax core → consumers

```
  MM Strategy Bot / Trading lab (trade_ledger) ─┐
  SovereignForge (Norwegian fork) trade_ledger  ─┤
  Prediction-Market algo (Kalshi)               ─┤
  Arbitrage Bot                                  ─┼─► Tax Adapter ─► Taxes/ ─► capital router
  VARDE (future)                                 ─┤   (this repo)    (tax core)   (consumer)
  future producers / manual exchange CSVs       ─┘   what happened   what it     dashboards /
                                                                      meant       pnl-service
                                                                                  (consumers)
```

| Session (your name) | Repo path | Role in the pipeline |
|---|---|---|
| **Taxes** | `Documents/Taxes` | Tax authority of record. **Sets requirements.** Owns the canonical Event contract + deterministic tax core. |
| **Tax Adapter** | `Documents/Tax adapter` | Translation layer. Owns source→Event **mapping** only. The hub that holds this alignment folder. |
| **MM Strategy Bot / Trading lab** | `Documents/Trading` | Producer. Owns `trade_ledger`, intent, order contracts, the two-book model. |
| **SovereignForge** | `Documents/SovereignForgeV1` (Norwegian operator's fork: `BWCoast/SovereignForgeV1`) | Producer (promotion 2026-06-14, **PROPOSED** ratification). Emits canonical `trade_ledger` v3 rows via a thin translator over its existing DAC8 chain. Strategy: OFG-DCA spot-only on Bybit-EU USDC. Reserved `event_id` prefix `sf:ofg:`. Branch: `claude/norway-producer-seam`. Detail: `SOURCES.md` §4, `proposals/sf_producer_recognition_PROPOSED.md`. |
| **Prediction-Market algo (Kalshi)** | `Documents/PM algo` | Producer. Standalone bot; conforms to the adapter's export contract. |
| **Arbitrage Bot** | *repo path TBD* | **First-class planned producer** — not yet built / not yet feeding the pipeline. First-class in the topology now (not a generic future system). |
| **VARDE** | *repo path TBD* | **First-class planned producer** (another bot) — not yet built / not yet feeding the pipeline. First-class now, specifics OPEN. |
| **Capital router / dashboards / pnl-service** | *future* | Consumers. Downstream of realized PnL and tax Events. |

> **Note (superseded 2026-06-14):** an earlier framing called `SovereignForgeV1`
> "platform context only — not a contract dependency." That framing reflected the
> pre-Norwegian-fork state; SF is now a live producer (PROPOSED ratification).
> The five PATTERNS in §9 (A1–A5) still apply as mining-only; the SF role above
> is the contract dependency.

## 5. Ownership & direction of authority

The hard rule that makes the pipeline composable:

- **Taxes sets the requirements.** It owns the canonical `Event` / `events.csv`
  intake (ADR-0001) and every tax characterization. Everyone else satisfies it.
- **Producers emit declared facts.** They own their own ledger/export contracts
  (`Trading` owns `trade_ledger`, ADR-005/006; `PM algo` owns its export *after*
  the adapter defines the shape). They never emit tax conclusions.
- **The Tax Adapter owns the mapping** — and *only* the mapping. It consumes the
  producer contracts and the Taxes contract; it owns neither.
- **Additive-only, propose-back.** A session that needs another session's
  contract changed proposes an **additive** change back to that owner. No
  session redefines another's semantics locally. A missing field is an upstream
  additive schema bump, never a local computation or hack.
- **Read-only across boundaries.** No session reads another's raw internals
  (venue payloads, bot DBs, strategy state). You read the *declared canonical
  contract* of the upstream, nothing else.

If a task seems to need you to cross one of these lines — stop. It belongs in
another session.

## 6. Anti-patterns — explicitly banned

These are the specific ways the pipeline rots. None are allowed in any session:

- **"Conversation architecture."** Treating a decision settled in a chat as if
  it were a contract. If it isn't written into the owning repo's ADR/LAWS/
  SCHEMAS (or marked OPEN here with an owner), it does not bind. Chats propose;
  documents decide.
- **Producer-owned tax semantics.** A bot deciding what a fill *means for tax*
  (gain/loss, income vs capital, characterization). Producers emit facts; Taxes
  rules. `event_type` is normalization, not a tax ruling.
- **Adapter-owned tax math.** The adapter computing FIFO/S104, valuation,
  gain/loss, or any characterization. The adapter says *what happened* and stops.
- **Capital-router / allocation logic leaking backward into Event mapping.**
  Tax-reserve, accrual routing, sizing, or "what to do with the money" must
  never influence how a fill becomes an Event. Allocation is a downstream
  *decision*; translation is not a decision.
- **Reporting / P&L attribution in the adapter or a producer.** Interpretation
  lives in the pnl-service / dashboards, not in the producers or the bridge.

## 7. Shared invariants (non-negotiable, every session inherits these)

These hold everywhere money or quantities move. They are not adapter-only.

1. **Decimal only** for all monetary/quantity values. Never float — IEEE-754
   epsilon fails an audit tie-out.
2. **Never fabricate** a missing source fact. UNRESOLVED / `None` is a
   first-class value. A missing number must look missing, not zero.
3. **Ambiguity becomes `REQUIRES_REVIEW`**, never a safer-looking guess.
   Surfacing uncertainty is correct behaviour, not failure.
4. **Preserve provenance** end-to-end: `decision_id → order → intent →
   experiment_hash`, plus `run_id`, `git_commit`, `book`, `mode`.
5. **Deterministic + idempotent.** Same input → same output; stable IDs; no
   clock/randomness in the path; re-import is a no-op. Golden fixtures pin
   known-good output byte-identical.
6. **Append-only / auditable ledger behaviour.** Fills are insert-only; a tax
   fact is captured at fill time, never reconstructed after the fact.
7. **Counted skips.** Every dropped/unmapped row gets a counted reason;
   `sum(reasons) == n_dropped`. Uncounted drops drift accounting silently.

### Load-bearing mapping rules (so producers emit facts the adapter can map)

These are the four that are easiest to get wrong (Adapter `GOTCHAS.md`,
`SCHEMAS.md` §3):

- **Derivative fills are NOT acquisitions/disposals of the underlying** — emit
  realized-PnL / funding in the settle asset only.
- **A stablecoin-quoted buy is a SWAP** (two taxable legs), not a one-sided
  acquisition.
- **Book / capital-router transfers are a linked `TRANSFER_OUT` / `TRANSFER_IN`
  pair**, never disposal + acquisition.
- **`event_type` is a normalization, not a final tax ruling.** The adapter says
  what happened; the Taxes core decides what it meant.

## 8. Coordination protocol

1. **Read first.** Before defining anything, check whether an ADR, `LAWS.md`,
   `SCHEMAS.md`, `SOURCES.md`, `HANDOFF.md`, or an existing repo doc already
   settles it. Reference it by path/name. Do not invent a new schema that
   already exists.
2. **Mark OPEN, assign an owner.** If a contract is genuinely unsettled, write
   it as `OPEN` in the structured form below — never silently fill the gap.
3. **Propose additive changes back to the owner.** Changes to the Event
   contract → Taxes session. Changes to `trade_ledger` → Trading session. The
   adapter records the request in *its* docs and the owner ratifies in *theirs*.

### OPEN item format

Every OPEN item carries four fields so it cannot be quietly ignored:

```
OPEN: <short title>
  owner:           <session(s) that must decide / ratify>
  blocking_for:    <what cannot proceed until this is settled>
  decision_needed: <the specific question to answer>
  target_doc:      <where the ratified decision will live>
```

### Open cross-session items (carried from `HANDOFF.md` / `PROGRESS.md`)

```
OPEN: event_id prefixes for adapter-produced events
  owner:           Taxes (ratify) + Tax Adapter (propose)
  blocking_for:    deterministic event_id scheme; adapter implementation
  decision_needed: reserve the `ledger:` and `pm-algo:` event_id prefixes
  target_doc:      Taxes ADR-0001 addendum

OPEN: trade_ledger → adapter transport
  owner:           Trading (decide with Tax Adapter)
  blocking_for:    adapter reading live canonical rows; Happy Path 1 (HP-1)
  decision_needed: how canonical rows are handed over (file drop vs shared
                   read-only export). Schema is settled; only transport is open.
  target_doc:      Trading ADR (transport) + adapter SOURCES.md

OPEN: HP-1 schema-faithful trade_ledger fixture
  owner:           Trading (produce) + Tax Adapter (consume)
  blocking_for:    the adapter's first golden fixture (SCHEMAS §7 / ADR-003)
  decision_needed: one contract-faithful fiat-quoted spot-buy row, emitted in
                   the chosen HP-1 transport format
  target_doc:      Trading repo fixture (e.g. fixtures/trade_ledger/hp1_spot_buy.csv)

OPEN: prediction-market export contract
  owner:           PM algo (conform) + Tax Adapter (define shape)
  blocking_for:    building the PM-algo export adapter
  decision_needed: ratify the §3.4 minimum set (fills, fees, realized PnL /
                   payouts, deposits/withdrawals, year-end positions)
  target_doc:      adapter SCHEMAS.md §3.4

OPEN: Arbitrage Bot wiring
  owner:           Arbitrage Bot (when built) + Tax Adapter
  blocking_for:    Arbitrage feeding the pipeline
  decision_needed: shared trade_ledger vs standalone export; instrument types
                   that stress the load-bearing rules; repo path
  target_doc:      alignment/role-arbitrage.md + adapter SCHEMAS.md

OPEN: VARDE definition & wiring
  owner:           VARDE (when built) + Tax Adapter
  blocking_for:    VARDE feeding the pipeline
  decision_needed: VARDE's distinct purpose; shared ledger vs standalone export
  target_doc:      alignment/role-varde.md
```

## 9. SovereignForge takeaways (owner-tagged)

From a read-only review of the live-trading Belgian sibling. Full detail +
golden-fixture requirements in [`TAKEAWAY-SOVEREIGNFORGE.md`](../TAKEAWAY-SOVEREIGNFORGE.md).
The tax *specifics* don't transfer; these *patterns* do.

| # | Takeaway | Owner | One-line |
|---|---|---|---|
| **A3** | **Classification-defense** ⭐⭐⭐ | cross: Trading + Taxes | Produce dated, signed evidence that *the operator set the parameters; the bot merely executed* — defends private-investor (kapitalinntekt) vs business (virksomhet). Cheap now, impossible to reconstruct later. |
| **A1** | **Oslo year-boundary** ⭐ | Taxes | Bucket the income year on **Europe/Oslo wall-clock**, not UTC. A fill at `2025-12-31T23:30:00Z` is tax year **2026**. |
| **A2** | **FX tiering** ⭐ | Trading → Adapter → Taxes | `fx_usdnok_at_fill` carries `{rate, source, as_of_ts}`, captured at fill time. Adapter preserves all three; Taxes treats it as tier-1, above the warned fallback. |
| **A4** | **Tamper-evident ledger** ⭐ | Trading | Append-only fill ledger with a per-row hash chain (`prev_hash`, `row_hash`) — provably unedited to an auditor. |
| **A5** | Verbatim decimal strings | Adapter | Keep the venue's exact reported `qty/price/fee` strings in provenance for bit-for-bit audit tie-out. |

Two meta-lessons that apply to **every** session:

- **End-to-end wiring beats documented-but-disconnected modules.** A contract
  that is specified but never actually wired through is worth little. Prefer one
  thin path that runs end-to-end over many polished, unconnected modules.
- **One canonical project brain prevents session drift.** This folder is that
  brain. Keep it current; read it before you assume.

## 10. Read order

1. This file (`ECOSYSTEM.md`).
2. Your role card: `role-<your-role>.md`.
3. The contracts your role card points you to.
