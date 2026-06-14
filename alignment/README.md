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
   to the owner** (see ECOSYSTEM §6) — it never redefines semantics locally.
4. When a contract or a fact changes, **update this folder** — it is only useful
   while it is current.

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
