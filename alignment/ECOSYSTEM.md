# ECOSYSTEM — canonical alignment for all tax/trading sessions

> **Status:** binding · **Owner:** Tax Adapter session (this repo) · **Updated:** 2026-06-14
>
> This is the shared mental model for every session in the ecosystem. Read it
> before doing tax/trading/reporting work in *any* repo. It does not replace a
> repo's own ADRs/LAWS/SCHEMAS — it tells you how the repos fit together, who
> owns what, and the invariants none of them may break. Where this doc and an
> owning repo's contract disagree, **the owning repo wins** and this doc is
> stale — fix it.

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

## 3. Topology — producers → adapter → tax core → consumers

```
  MM Strategy Bot / Trading lab (trade_ledger) ─┐
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
| **Prediction-Market algo (Kalshi)** | `Documents/PM algo` | Producer. Standalone bot; conforms to the adapter's export contract. |
| **Arbitrage Bot** | *(TBD)* | Producer. Not yet built / not yet feeding the pipeline. |
| **VARDE** | *(TBD)* | Producer (another bot). Not yet built / not yet feeding the pipeline. |
| **Capital router / dashboards / pnl-service** | *(future)* | Consumers. Downstream of realized PnL and tax Events. |

`SovereignForgeV1` (`Documents/SovereignForgeV1`) is **platform context only** —
a live-trading Belgian sibling we mine for patterns/failure modes (see §7). Its
tax *specifics* do not transfer; it is not a contract dependency.

## 4. Ownership & direction of authority

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

## 5. Shared invariants (non-negotiable, every session inherits these)

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

## 6. Coordination protocol

1. **Read first.** Before defining anything, check whether an ADR, `LAWS.md`,
   `SCHEMAS.md`, `SOURCES.md`, `HANDOFF.md`, or an existing repo doc already
   settles it. Reference it by path/name. Do not invent a new schema that
   already exists.
2. **Mark OPEN, assign an owner.** If a contract is genuinely unsettled, write
   it as `OPEN` and name the owning session — don't silently fill the gap.
3. **Propose additive changes back to the owner.** Changes to the Event
   contract → Taxes session. Changes to `trade_ledger` → Trading session. The
   adapter records the request in *its* docs and the owner ratifies in *theirs*.

### Open cross-session items (carried from `HANDOFF.md` / `PROGRESS.md`)

- **[Taxes]** reserve the adapter's `ledger:` / `pm-algo:` `event_id` prefixes
  (ADR-0001 addendum).
- **[Trading]** agree the `trade_ledger → adapter` **transport** (file drop /
  shared read-only export). Schema is settled; only transport is OPEN.
- **[PM algo]** define + conform to the prediction-market export contract
  (`SCHEMAS.md` §3.4 minimum set).

## 7. SovereignForge takeaways (owner-tagged)

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

## 8. Read order

1. This file (`ECOSYSTEM.md`).
2. Your role card: `role-<your-role>.md`.
3. The contracts your role card points you to.
