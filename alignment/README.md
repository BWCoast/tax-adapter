# alignment/ — the canonical coordination layer

This folder is the **one canonical project brain** for every session in the
tax/trading/reporting ecosystem. The Tax Adapter repo
(`C:\Users\mrkro\Documents\Tax adapter\`) is the hub; all sessions read this
folder **read-only**.

> **adapter = what happened · tax core = what it meant · capital router = what
> to do with the money**

## Files

| File | What it is |
|---|---|
| [`ECOSYSTEM.md`](ECOSYSTEM.md) | The shared truth: topology, ownership, invariants, SovereignForge takeaways, coordination protocol. **Every session reads this.** |
| [`role-taxes.md`](role-taxes.md) | Taxes — requirements owner / tax core |
| [`role-tax-adapter.md`](role-tax-adapter.md) | Tax Adapter — source→Event mapping only |
| [`role-mm-strategy.md`](role-mm-strategy.md) | MM Strategy Bot / Trading lab — `trade_ledger` producer |
| [`role-pm-kalshi.md`](role-pm-kalshi.md) | Prediction-Market algo (Kalshi) — producer |
| [`role-arbitrage.md`](role-arbitrage.md) | Arbitrage Bot — producer (not yet wired) |
| [`role-varde.md`](role-varde.md) | VARDE — producer (not yet built) |
| [`role-producer-template.md`](role-producer-template.md) | Generic card for future producers |

## How to use

1. At the **start of each session**, paste that session's prompt below.
2. The session reads `ECOSYSTEM.md` + its role card, then proceeds.
3. If a session needs another's contract changed, it **proposes additively back
   to the owner** (see ECOSYSTEM §8) — it never redefines semantics locally.
4. When a contract or a fact changes, **update this folder** — it is only useful
   while it is current.

## Rollout status

Tick a session once it has received its paste block and is reading this folder.
This is the migration state — no need to copy files into each repo.

- [ ] Taxes session aligned
- [x] Tax Adapter session aligned (2026-06-14)
- [ ] MM Strategy / Trading lab session aligned
- [ ] PM Kalshi session aligned
- [ ] Arbitrage session aligned
- [x] VARDE session aligned (2026-05-12)

---

## Paste prompts (per session)

### Taxes
```
Before continuing, read:
C:\Users\mrkro\Documents\Tax adapter\alignment\ECOSYSTEM.md
C:\Users\mrkro\Documents\Tax adapter\alignment\role-taxes.md

Treat these as canonical and binding for tax/trading/reporting alignment. You
are the tax authority of record: you set the requirements and own the canonical
Event contract. Do not redefine ledger, Event, P&L, fee, funding, transfer,
settlement, or book semantics outside your own ADRs. If you need a producer or
adapter contract changed, request it via the Tax Adapter alignment folder.
```

### Tax Adapter (this repo)
```
Before continuing, read:
C:\Users\mrkro\Documents\Tax adapter\alignment\ECOSYSTEM.md
C:\Users\mrkro\Documents\Tax adapter\alignment\role-tax-adapter.md

Treat these as canonical and binding. You build source→Event mappings — not tax
rules, not strategy logic, not allocation, not reporting. Read only canonical
ledgers / declared exports. Keep this alignment folder current.
```

### MM Strategy Bot / Trading lab
```
Before continuing, read:
C:\Users\mrkro\Documents\Tax adapter\alignment\ECOSYSTEM.md
C:\Users\mrkro\Documents\Tax adapter\alignment\role-mm-strategy.md

Treat these as canonical and binding for tax/trading/reporting alignment. You
own trade_ledger; you are a producer of fills, not tax conclusions. Do not
redefine ledger, Event, P&L, fee, funding, transfer, settlement, or book
semantics locally. If this session needs a contract change, propose it back to
the Tax Adapter alignment folder instead.
```

### Prediction-Market algo (Kalshi)
```
Before continuing, read:
C:\Users\mrkro\Documents\Tax adapter\alignment\ECOSYSTEM.md
C:\Users\mrkro\Documents\Tax adapter\alignment\role-pm-kalshi.md

Treat these as canonical and binding for tax/trading/reporting alignment. You
are a producer: conform to the adapter's export contract (SCHEMAS.md §3.4); do
not invent a private tax/export format. Do not redefine ledger, Event, P&L,
fee, funding, transfer, settlement, or resolution semantics locally. If this
session needs a contract change, propose it back to the Tax Adapter alignment
folder instead.
```

### Arbitrage Bot
```
Before continuing, read:
C:\Users\mrkro\Documents\Tax adapter\alignment\ECOSYSTEM.md
C:\Users\mrkro\Documents\Tax adapter\alignment\role-arbitrage.md

Treat these as canonical and binding for tax/trading/reporting alignment. You
are a producer (not yet wired). Settle the OPEN items in your role card before
feeding the pipeline. Do not redefine ledger, Event, P&L, fee, funding,
transfer, settlement, or book semantics locally. Propose contract changes back
to the Tax Adapter alignment folder.
```

### VARDE
```
Before continuing, read:
C:\Users\mrkro\Documents\Tax adapter\alignment\ECOSYSTEM.md
C:\Users\mrkro\Documents\Tax adapter\alignment\role-varde.md

Treat these as canonical and binding for tax/trading/reporting alignment. You
are a producer, not yet built out and not yet feeding the Taxes pipeline. Settle
the OPEN questions in your role card first. Do not redefine ledger, Event, P&L,
fee, funding, transfer, settlement, or book semantics locally. Propose contract
changes back to the Tax Adapter alignment folder.
```

### A new / future producer
```
Before continuing, read:
C:\Users\mrkro\Documents\Tax adapter\alignment\ECOSYSTEM.md
C:\Users\mrkro\Documents\Tax adapter\alignment\role-producer-template.md

Treat these as canonical and binding for tax/trading/reporting alignment. You
are a producer of fills/exports, not a tax/allocation/reporting layer. Conform
to the adapter's export contract; do not redefine ledger, Event, P&L, fee,
funding, transfer, settlement, or book semantics locally. When you become a
first-class project, copy the template to role-<name>.md and propose contract
changes back to the Tax Adapter alignment folder.
```

---

## Active task prompts — HP-1 cycle (opened 2026-06-14) — **RETIRED 2026-09-29**

> **Both blocks below are retired per this section's own rule** (their `ECOSYSTEM.md
> §8` items flipped): Trading delivered the transport *format* (ADR-007) and the
> `hp1_spot_buy.csv` fixture; Taxes ratified the prefixes (ADR-0001 addendum
> 2026-07-13) and the adapter's emitted rows are proven against the real
> `CanonicalEvent` (`tests/test_events_conformance.py`). Kept as history. Do **not**
> paste them into a new session; note the Taxes block's "ACQUISITION + FEE" wording
> is superseded by `TRADE` + `FEE` (ADR-004). Live transport mechanics remain open —
> see `HANDOFF.md`.

**Time-bound, unlike the evergreen blocks above.** These drive the first
end-to-end path (ADR-003: MM spot-only). Paste the targeted block *after* that
session's generic block. Retire a block when its `ECOSYSTEM.md §8` OPEN items
flip to settled. The two can run **in parallel** — the Taxes prep does not
depend on Trading's transport choice.

### Trading / MM Strategy — settle transport + produce HP-1 fixture
```
You have already read ECOSYSTEM.md and role-mm-strategy.md. Now also read the
adapter's decisions/ADR-003 (MM = first producer, HP-1 = spot-only) and
SCHEMAS.md §7 (Happy Path 1 worked example).

Your job this session is to unblock HP-1 for the Tax Adapter with exactly two
deliverables, both fully inside the Trading lab's ownership:

1. DECIDE + DOCUMENT the trade_ledger -> Tax Adapter transport for HP-1.
   Pick one concrete, file-based transport (read-only CSV drop, or a read-only
   SQLite/Parquet snapshot, or equivalent). It MUST be:
     - read-only from the adapter's point of view,
     - deterministic/reproducible (same Trading input -> same export bits),
     - append-only (no in-place mutation of historical rows).
   Output: a short transport description committed in the Trading repo, plus a
   one-line confirmation that HP-1 depends on it. Reference it by path from the
   ECOSYSTEM.md §8 "trade_ledger -> adapter transport" OPEN item.

2. PRODUCE one schema-faithful trade_ledger fixture row for HP-1.
   Per ADR-003 / SCHEMAS.md §7: a fiat-quoted, spot-only BUY on the frozen
   trade_ledger contract (ADR-005/006). No derivatives, no SWAP leg, no FX tier,
   no allocations. The row must be fully valid per the trade_ledger schema,
   minimal but realistic, and carry every field SCHEMAS.md §7 marks as consumed.
   Emit it in the transport format chosen in (1), e.g.
   fixtures/trade_ledger/hp1_spot_buy.csv. Output: the fixture committed in the
   Trading repo + a note confirming it is contract-faithful, so the adapter can
   build its first golden fixture without inventing any Trading-side semantics.

Scope / guardrails:
- You do NOT define tax semantics, Event layout, or P&L rules — those are Taxes
  and the Tax Adapter (per the alignment docs).
- You DO own: how trade_ledger is exported for HP-1, and the exact contents of
  the HP-1 row.
- If HP-1 seems to need a NEW trade_ledger field, do not compute it locally for
  the adapter — propose an additive schema bump back via the Tax Adapter
  alignment folder.

Done = ECOSYSTEM.md §8 OPEN items "trade_ledger -> adapter transport" and
"HP-1 schema-faithful trade_ledger fixture" can both flip OPEN -> settled, each
with a clear reference into the Trading repo.
```

### Taxes — confirm HP-1 intake + reserve event_id prefixes (runs in parallel)
```
You have already read ECOSYSTEM.md and role-taxes.md. Now also read the adapter's
decisions/ADR-003 and SCHEMAS.md §7 (the two exact Event rows HP-1 emits: one
ACQUISITION of BTC + one FEE in NOK).

Your job this session is to make the Taxes core ready to RECEIVE HP-1 Events,
with two deliverables inside the Taxes lane (independent of Trading's transport):

1. RESERVE the adapter's event_id prefixes. Confirm `ledger:` and `pm-algo:`
   are reserved and collision-free against your existing prefixes
   (inflow_group:, xrpl:, csv:). Record it as an ADR-0001 addendum. This closes
   the ECOSYSTEM.md §8 "event_id prefixes" OPEN item.

2. CONFIRM intake of the SCHEMAS.md §7 Event rows. Verify the two rows ingest
   into the 20-column events.csv intake without error, with no tax math required
   at ingest. If any required column the adapter does NOT populate would reject
   the row, list it precisely so the adapter can map or mark it UNRESOLVED.

Scope / guardrails:
- You OWN the Event contract and all tax characterization; ratify Event changes
  in your own ADRs.
- You do NOT reach into the adapter's mapping or Trading's ledger. For anything
  you need from them, request an additive change via the alignment folder.
- `event_type` from the adapter is normalization, not a tax ruling — you do the
  ruling at compute time, not at intake.

Done = the "event_id prefixes" §8 OPEN item flips OPEN -> settled (ADR-0001
addendum), and HP-1 intake is confirmed (or a precise list of required-but-
unpopulated columns is sent back to the adapter).
```
