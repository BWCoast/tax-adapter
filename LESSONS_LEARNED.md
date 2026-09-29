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

Earned in the first slice (VARDE NOK spot buy, `d89ccb1`; verified 2026-09-29,
28 tests passing). Each is tied to evidence in the repo, not to anticipation.

15. **Verify the output shape against the owner's *code*, not its docs — or our own.**
    Our `SCHEMAS.md` (and the stack hub's worked examples) described a single-sided
    `ACQUISITION` row that Taxes' `CanonicalEvent` rejects at construction. It was
    caught only because someone read `event.py` (ADR-004). A spec that has never been
    run against the consumer is a hypothesis.
16. **Mirror the contract, don't import the consumer — and prove the mirror.** The
    adapter carries its own `Event.validate()` and a column-drift test, and a
    skip-if-unavailable conformance test that constructs the *real* `CanonicalEvent`.
    That keeps the read-only repo boundary while still catching drift (ADR-004 §3).
17. **Fail closed on the unmapped, loudly.** Unimplemented shapes raise
    `NotImplementedError` rather than guessing (pinned by the `…sell_and_stablecoin…`
    test in `tests/test_varde_hp1.py`). Better a stopped run than a plausible wrong
    tax row (A3).
18. **A golden fixture is only as good as the *second* run.** The HP-1 output is
    pinned byte-for-byte and a re-run is asserted byte-identical, which is what makes
    "deterministic" a tested claim (A5) instead of a slogan.
19. **Probe the edges before writing "the code does X".** Reading the mapper said it
    handled fees; running it showed a zero fee still emits a `FEE`, a blank fee
    crashes with a bare `InvalidOperation`, and rows are indexed in input order. Docs
    written from a read alone would have overstated v1 (M1/M2/M4).
20. **Re-verify upstream state on the day you cite it.** Between two reads the hub
    closed OPEN-1, Taxes ratified prefixes — and ratified `pm-algo:` as a
    `provenance.algo` label, *not* an `event_id` prefix, contradicting both our docs
    and the hub's. Carrying a months-old "pending" forward would have baked in a
    second wrong claim.
21. **One doc must say which parts are real.** Spec and implementation drift apart
    fast in a docs-first repo; the fix is a status banner at each claim (implemented
    vs spec-only, with a verified date), not a global "in progress".
