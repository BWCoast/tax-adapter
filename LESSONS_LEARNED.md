# LESSONS LEARNED

What works. Seeded at project start from the two contracts this adapter
bridges — `Taxes` (tax core, ADRs 0001–0030) and `Trading` (ledger contracts,
ADR-005/006) — and from `PM algo`'s production accounting scars (referenced via
Trading's distillation). Grows as the adapter is built.

## Inherited — tax-core discipline (Taxes)

1. **One canonical event model beats per-source logic.** Normalize every
   source to one schema *before* any tax logic; otherwise every downstream
   module needs source-specific branches (ADR-0001). The adapter is one more
   parser in that model — it does not earn an exception.
2. **Never fabricate basis; UNRESOLVED is a first-class value** (ADR-0005). A
   missing number must look missing, not zero. The adapter passes through or
   marks `None` — it never invents.
3. **Explicit about ambiguity.** Unknown/unresolvable events are typed
   `REQUIRES_REVIEW`, never silently mapped to a safer-looking type (ADR-0001).
   Surfacing uncertainty to the user is correct behaviour, not a failure.
4. **Determinism is the substrate of auditability.** Same input → same output,
   no clock/randomness in the path; golden fixtures pin known-good output
   byte-identical. A re-import that changes the answer is a bug.
5. **Decimal, never float, for money** — and qualified asset keys
   (`SYMBOL.contract`) so `USDC.0x…` ≠ `USDC.other` (ADR-0021).
6. **Spec → external audit → plan → TDD → verify → document.** No tax-relevant
   code lands without a reviewed spec and tests (Taxes CLAUDE workflow).

## Inherited — ledger/contract discipline (Trading)

7. **Tax reads only the canonical ledger** (ADR-005/L20). Confining
   venue-specific logic to upstream adapters and reading one schema is what
   keeps the tax side stable as engines come and go. The adapter enforces this
   boundary, it doesn't get to breach it for convenience.
8. **Tax facts are captured at fill time, never reconstructed** (L17, PM algo
   law 6). `fx_usdnok_at_fill`, fee, fee asset, fill kind all live on the
   ledger row. The adapter's job is to *preserve* them, and to refuse to
   reconstruct what wasn't captured.
9. **Contracts are cheap to freeze before engines accumulate, near-impossible
   after** (ADR-005). Specifying the mapping now — before the lab emits live
   rows and before more engines exist — is the same timing logic: write the
   translation contract while nothing has an incentive to bend it.
10. **Sim/paper/live rows are structurally identical** (L20). The adapter maps
    on `mode` (provenance), not on structure — if it had to branch on mode,
    the ledger would be broken upstream.

## Inherited — accounting scars (PM algo, via Trading)

11. **Every skip/drop gets a counted reason; `sum(reasons) == n_dropped`.**
    Uncounted drops drift accounting silently. The adapter counts every
    unmapped row.
12. **Floats lie at money boundaries** (§14/§15). Strip IEEE-754 epsilon before
    any rounding; Decimal end-to-end.
13. **`str(x.get(k, ""))` stores the literal `"None"`; truthiness eats valid
    zeros.** Use `str(x.get(k) or "")` and `if x is None` — a `0` quantity or
    fee is real data, not absence.
14. **Verify output freshness before trusting an artifact** (§47). A crashed
    upstream job leaves a stale ledger export that looks legitimate; check the
    ledger's `run_id`/`git_commit`/generated time before translating it.

## From building the adapter

_(empty — populated as the adapter is implemented and meets real ledger data)_
