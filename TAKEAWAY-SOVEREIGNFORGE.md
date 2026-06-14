# TAKEAWAY — SovereignForgeV1 (sharpened requirements)

What SovereignForgeV1 (a more mature, *live-trading* Belgian sibling) has
solved that the Trading lab / Tax Adapter / Taxes core have **not yet
considered**, turned into owner-tagged requirements. Filtered hard against
what each project already does — items they already cover are listed as
"already covered, no action" so nobody re-litigates them.

Source: read-only review of `Documents/SovereignForgeV1/repo` (2026-06).
SovereignForge is Belgian (speculative_33, 2025-12-31 step-up) — the tax
*specifics* do NOT transfer; the *patterns* and *failure modes* do.
Status: analysis → requirements. Nothing built. Owners act in their session.

Ownership tags: **[Taxes]** = Norwegian tax core · **[Adapter]** = this repo ·
**[Trading]** = the lab / trade_ledger · **[cross]** = spans sessions.

---

## PART A — TAX & COMPLIANCE (the area SovereignForge is years ahead on)

### A1 — Tax-year assignment MUST localize to Europe/Oslo, not UTC  **[Taxes]** ⭐
- **Finding.** SovereignForge has explicit Brussels-local year-boundary
  handling: a fill at `Dec 31 23:30 UTC` is `Jan 1 01:30 CET` → it belongs to
  the *next* income year. They hit this as a real bug.
- **Why it's a gap for us.** Norway is CET/CEST. The canonical Event carries
  `exchange_ts` in UTC ("reported Oslo downstream"). If RF-1159 period/year
  bucketing keys off UTC, every fill in the `23:00–24:00 UTC, Dec 31` window
  (winter ⇒ CET = UTC+1) is filed in the wrong tax year.
- **Requirement.** FIFO period/year bucketing converts to **Europe/Oslo
  wall-clock before assigning the income year**. Golden fixture: a fill at
  `2025-12-31T23:30:00Z` must land in **tax year 2026**. (Boundary is always
  winter/CET = UTC+1, so the at-risk window is 23:00–24:00 UTC on Dec 31.)
- **If already handled:** this is a no-op confirmation + a fixture. Verify,
  don't assume.

### A2 — FX-at-fill is a venue-timestamped TIER-1 rate, carried verbatim with its source  **[Trading] → [Adapter] → [Taxes]** ⭐
- **Finding.** SovereignForge captures the EUR rate at fill time and never
  back-fills it post-hoc; the captured rate is decimal-string, with source.
- **Already covered:** Trading L17 ("NOK FX captured at fill time"); Adapter
  passes `fx_usdnok_at_fill` through, `nok_value=None` if absent (never
  invented); Taxes ADR-0010 has an FX-fallback *with a mandatory warning*.
- **The sharpening (genuine delta).** Distinguish a **bot fill's captured
  rate** from the **Taxes fallback**. Bot fills should almost never use the
  fallback.
  - **[Trading]** `trade_ledger.fx_usdnok_at_fill` must carry `{rate, source,
    as_of_ts}`, populated at write time from a timestamped FX source — not a
    constant, not a daily close unless that *is* the source.
  - **[Adapter]** preserve all three in `provenance`; surface `nok_value`
    as resolved-tier-1 vs unresolved.
  - **[Taxes]** treat adapter-supplied FX as a **tier-1 valuation source**
    (ADR-0006 precedence), explicitly above the ADR-0010 warned fallback;
    flag any bot fill that fell through to fallback (it means upstream
    capture failed — an ingestion bug, not a normal path).

### A3 — Private-investor vs business-income classification defense  **[cross: Trading + Taxes]** ⭐⭐⭐
- **Finding.** SovereignForge's *entire* audit architecture exists to defend
  one thesis to the tax authority: **"the operator set the parameters; the
  bot merely executed."** Decision logs, dated rationale, human-approval
  gates, an HMAC-chained discretion journal — all of it is evidence that this
  is *discretionary private investing*, not an automated trading *business*.
- **Why it's a gap for us (and high-stakes).** Norway distinguishes
  **kapitalinntekt** (private capital income, flat ~22% on net gain) from
  **virksomhetsinntekt** (business income — higher effective rate, bookkeeping
  duty, possible MVA, ongoing obligations). Frequent, systematic, automated,
  capital-at-scale trading is exactly the profile a tax office may reclassify
  as *virksomhet*. **Neither Trading nor Taxes currently produces evidence on
  either side of this line.** This is the single most valuable thing in the
  SovereignForge repo for this operator, and it is tax-*strategy*, not
  engineering.
- **Requirements.**
  - **[Trading]** Make the discretionary posture *structural and audited*,
    not incidental. Operator sets strategy parameters; each parameter set /
    change is **journaled, dated, and signed** (SovereignForge decision-log
    pattern). ADR-006's accrual router already leans discretionary (rare,
    discrete, operator-triggered buys) — make that **explicit and logged** as
    a classification-defense feature, not a side effect. The two-book split
    (neutral lab vs conviction accrual, L21) is itself defensible structure —
    accrual is plainly buy-and-hold investment.
  - **[Taxes]** The report layer should (a) compute and surface
    **activity-frequency / turnover metrics** per year, (b) be able to emit a
    **discretion/audit appendix** (parameter-change log, approval trail)
    supporting the private-investor characterization, and (c) **flag** when
    activity patterns approach plausible business-classification thresholds so
    the operator can seek advice *before* filing.
  - **[cross]** The user should get **professional Norwegian tax advice** on
    where the line sits; the system's job is to *produce the evidence and the
    warning* regardless of where the line lands. Cheap to design in now,
    expensive-to-impossible to reconstruct after years of un-journaled fills.

### A4 — Append-only + tamper-evident fill ledger (consider hash-chain)  **[Trading]** ⭐
- **Finding.** SovereignForge writes fills with an atomic `write → fsync →
  advance HMAC chain`; each row carries `prev_hash` + row HMAC. "Cannot edit a
  fill after the fact" — provable to an auditor.
- **Why it's a gap.** Trading L17 ledger is "insert-only" *by convention*, not
  *cryptographically*. Novel for us.
- **Requirement (consider, not mandate — weigh vs over-engineering for an
  individual).** The canonical fill ledger SHOULD be append-only with a
  per-row hash chain (`prev_hash`, `row_hash`) so the tax trail is provably
  unedited. It is cheap at write time and is the clean answer to "prove this
  ledger to Skatteetaten." Decide in a Trading ADR; pairs naturally with A3
  (the discretion journal wants the same tamper-evidence).

### A5 — Preserve venue-reported decimal strings verbatim for audit tie-out  **[Adapter]**
- **Finding.** SovereignForge stores money fields as **decimal strings** so
  `qty × price` reconciles bit-for-bit against the venue settlement statement
  (one IEEE-754 ULP fails an audit).
- **Already covered:** Adapter + Taxes are `Decimal`-only, no floats.
- **The sharpening.** Preserve the venue's **exact reported strings**
  (`qty, price, fee`, unrounded) in `provenance`, so a future audit ties the
  tax report back to the venue statement with zero drift. Parse to `Decimal`
  with no float intermediate (already the rule — confirm the *raw string* is
  retained, not just the parsed value).

### A6 — Residency/baseline step-up guard (pattern only, low priority)  **[Taxes]**
- **Finding.** SovereignForge has a hard `assert_no_pre_step_up_lots()` guard
  around its 2025-12-31 step-up — refuses to compute basis on pre-baseline
  lots; loud failure, never a silent miscalc.
- **Norway analog.** `inngangsverdi` step-up on becoming Norwegian tax-resident
  (assets valued at market at residency). Likely not relevant to this operator
  now, but the *pattern* is.
- **Requirement (low).** If any baseline-revaluation date ever applies, FIFO
  must **refuse** to compute basis on pre-baseline lots (loud, not silent).
  Probably already implied by never-fabricate / UNRESOLVED (ADR-0005) — note
  the pattern, don't build.

**Already covered by Taxes/Adapter — explicitly NOT new requirements:** FIFO
lots + composite ordering (ADR-0002), never-fabricate basis / UNRESOLVED
(ADR-0005), decimal-only core, deterministic golden-fixture core, stablecoin
FX-fallback-with-warning (ADR-0010), override+recompute (ADR-0019),
multi-jurisdiction dispatch (ADR-0020), qualified asset identity (ADR-0021),
REQUIRES_REVIEW on ambiguity. SovereignForge adds nothing here.

---

## PART B — TRADING LAB: risk / ops / execution

Mostly **gated on a validated strategy** (Trading ADR-003 staging) — reference
implementations for when that gate opens, not now. Listed so they aren't lost.

### B1 — Integrity-vs-performance halt split  **[Trading ADR-003]** ⭐
SovereignForge's sharpest risk principle: **only INTEGRITY violations
auto-halt** (MiCA breach, clock skew, venue unreachable, bot malfunction).
Drawdown / daily-loss / price-crash are **alert + size-down signals, NOT
hard halts** — they are *strategy* inputs, not kill triggers. This is a
cleaner frame than ADR-003's current drawdown-ladder-that-halts; fold it in
when the risk engine is built.

### B2 — Clock-skew as a LIVE order-integrity halt  **[Trading ADR-003]** ⭐
We already obsess over clock drift in *capture* (`interp_offset`). Apply the
same discipline as a *live* halt: poll venue server-time mid-session; halt if
`|drift| > ~10s` (the venue silently rejects orders / you fill on stale
prices). Novel *application* of something we already measure; our host clock
drifts ~50ms/h so the threshold is comfortable but the *check* is the point.

### B3 — Watchdog supervision pattern  **[Trading ops]** — answers GOTCHAS 23
The concrete answer to "a background task is not an OS service": a **standalone
watchdog daemon** (Task Scheduler / systemd), **API-only restart** (never tear
down a live engine — replace only the dashboard/API process), exponential
backoff with a **ceiling** (~900s), a **hard restart cap** → alert-only mode,
and **mode-aware paging** (CRITICAL on live, warning on paper). We sidestepped
the problem by moving to the NAS; this is the more robust general pattern for
any long-running live process.

### B4 — Idempotent order handling + per-venue exception taxonomy  **[Trading, future execution]**
For when execution exists: a **duplicate client-order-id** (lost-ACK retry) is
**already-placed, not a failure** — don't re-place. Build a per-venue exception
taxonomy (their Bybit-V5 set: maker-only-rejected / insufficient-balance /
min-notional / bad-request / duplicate). Track maker→taker fallback rate (a
spike = fast market). Generalizes to Kraken (SPIKE-02) when we multi-venue.

### B5 — Raw-SQL numbered migrations + compliance-reviewer gate  **[Trading, low]**
Numbered idempotent SQL files + a `_schema_meta` version table, with an
explicit reviewer gate on any migration touching the fill ledger / audit
fields. We have versioned schemas (L6) but no migration *tooling*; adopt when
we first alter a persisted tier.

---

## PRIORITY

1. **A3 (classification defense)** and **A1 (Oslo year-boundary)** — cheapest
   now, expensive-to-impossible later. Both touch how fills are *recorded*, so
   they want deciding before live fills exist.
2. **A2 (FX tiering)** and **A4 (tamper-evident ledger)** — design into the
   `trade_ledger` before it's implemented (Trading lab is pre-edge → perfect
   timing).
3. **A5/A6** — confirmations / patterns, low effort.
4. **Part B** — reference for the ADR-003 risk build; gated on a validated
   strategy. Not now.

**Not adopted:** Belgian tax specifics (speculative_33, the 2025-12-31
step-up); the Jarvis agent layer (premature — we're a research lab, not an
agent product); "structurally-off gates" (we already have it as Trading L9).
