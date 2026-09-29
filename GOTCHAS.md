# GOTCHAS

Pitfalls specific to translating fills into tax events. Each entry:
trap → consequence → handling. Many are inherited as warnings before the
adapter has its own scars; those are marked *(anticipated)* until a real
capture confirms them.

## Mapping semantics

1. **Derivative fills are NOT acquisitions/disposals of the underlying.**
   A BTCPERP fill never transfers BTC ownership. Emitting ACQUISITION/DISPOSAL
   of BTC for a perp fabricates a spot lot that never existed and double-counts
   against the real holdings. → Perps emit realized-PnL/funding events in the
   *settle* asset only (SCHEMAS §3.2). *(anticipated)*
2. **A stablecoin "buy" is not a clean one-sided acquisition.** `side=buy` with a
   USDC/USDT quote disposes of the stablecoin and acquires the base — both legs
   are taxable under Norwegian rules. Treating it as one-sided loses the stablecoin
   disposal. → In the bilateral model (ADR-004) it is one `TRADE` whose `asset_out`
   is the stablecoin (SCHEMAS §3.1); the core rules on that leg. *(anticipated —
   the mapper raises `NotImplementedError` for it today.)*
3. **Internal book transfers must never read as disposals.** The capital
   router moving lab PnL to the accrual book (ADR-006) is not a change of
   owner. Mis-typing it manufactures phantom gains. → linked TRANSFER_OUT/IN
   pair with matching asset/qty/ts (A8); relies on Taxes transfer-linking
   ADR-0007/0013, whose **6-hour window** the emitted timestamps must respect.
4. **Funding sign decides INCOME vs FEE.** A received funding payment is income;
   a paid one is a fee. The sign of the ledger value, not the position side,
   determines it. Document per-row; never assume. *(anticipated)*
5. **`event_type` is a normalization, not a tax ruling.** It's tempting to
   resolve capital-vs-income in the adapter because the data is right there.
   Don't — that's the tax core's job (A4). Where characterization matters and
   isn't settled, `REQUIRES_REVIEW`.

## Identity & determinism

6. **event_id collisions silently merge unrelated events.** Taxes reserves
   `inflow_group:` and uses `xrpl:`/`csv:` canonical formats (ADR-0001
   addendum). The adapter's `ledger:`/`pm-algo:` prefixes must be verified
   non-colliding before any emit (A10).
7. **Unstable `source_row_index` corrupts FIFO downstream.** FIFO ordering
   (Taxes ADR-0002) ties on `(timestamp, source_row_index)`. If the adapter's
   sort isn't stable across re-imports, lot matching changes between runs and
   golden fixtures break. → sort on `(exchange_ts, trade_id, leg)`, fixed.
   **⚠ Confirmed live trap (2026-09-29): the v1 VARDE mapper does NOT do this** — it
   indexes in input order (a later-timestamp row listed first gets index 0). Feed it
   canonical-order input until the sort lands (SCHEMAS §3.7 known gap 1).
8. **The `"None"` string trap and the truthy-zero trap.** `str(x.get(k,""))`
   stores `"None"`; `if not x` skips a legitimate `0` fee/qty (PM algo §7/§13).
   Use `or ""` and explicit `is None` checks.

## Boundary discipline

9. **Reaching into a bot's DB/logs re-creates per-engine coupling.** The moment
   the adapter reads PM algo's SQLite or a strategy's internal state directly,
   the canonical-ledger boundary (A1) is dead and tax becomes engine-specific
   again. → consume only the canonical ledger + declared export contracts.
10. **A missing ledger field is an upstream schema bump, not an adapter
    hack.** If tax needs a field the ledger doesn't carry, the fix is an
    additive `trade_ledger` version (Trading L6) — not a private computation in
    the adapter. Quietly deriving it here hides the gap and drifts from the
    authoritative ledger.
11. **Building before live rows exist risks spec-to-fantasy drift.** The lab is
    pre-edge; `trade_ledger` isn't emitting live yet. Build the mapping against
    *real* exported rows (or faithful fixtures derived from the frozen schema),
    not an imagined shape — and re-verify when the first live ledger lands.

## Process / environment (Windows ecosystem)

12. **Windows PowerShell mangles UTF-8 docs on regex edits** (Trading GOTCHAS
    27): `Get-Content … -replace … | Set-Content` double-encodes `—`, `§`, `µ`.
    Edit docs with proper file tools, not PowerShell text rewrites.
13. **CSV is lossy for structured/Decimal data.** If the adapter ever
    round-trips through CSV (the `events.csv` intake is CSV), Decimal precision
    and provenance JSON must be string-preserved — don't let a float
    serializer touch money or a `"None"` leak in (cf. §8, Trading GOTCHAS 22).

## From building the adapter *(confirmed 2026-09-29 — not anticipated)*

14. **`ACQUISITION`/`DISPOSAL`/`SWAP` are not `event_type` values.** Taxes'
    `CanonicalEvent` has 8 types (`TRADE`, `TRANSFER_IN/OUT`, `INCOME`, `FEE`,
    `GIFT_IN/OUT`, `REQUIRES_REVIEW`) and rejects a one-sided "in" that isn't
    `TRANSFER_IN`/`GIFT_IN`/`INCOME`. A fiat buy is a `TRADE` with home fiat on the
    out-leg. Older prose in this repo and the hub's worked examples A/B still use the
    legacy words — read them as shorthand (ADR-004).
15. **`pm-algo:` is a `provenance.algo` label, not an `event_id` prefix** (Taxes
    ADR-0001 addendum 2026-07-13). Don't emit `pm-algo:`-prefixed `event_id`s; the
    PM mapper's prefix is unreserved until Taxes decides.
16. **The CLI needs `PYTHONPATH=src`.** The project has no build-system, so
    `tax_adapter` is never installed; only pytest gets the path (from
    `pyproject.toml`). `uv run python -m tax_adapter.cli …` alone raises
    `ModuleNotFoundError`.
17. **A zero fee still emits a `FEE` event, and a blank fee crashes.** The spec says
    "only when `fee > 0`" and "missing = blank, never 0"; v1 does neither
    (`decimal.InvalidOperation` on `""`). Pass a real fee string until fixed
    (SCHEMAS §3.7 known gaps 2–3).
18. **`notes` is write-only.** It carries `venue;strategy_id;mode;book;fill_kind` for
    humans. Never parse it for logic — the four provenance columns are the only
    first-class provenance in `events.csv`.
19. **Two Decimal regimes on one row.** Derived values are quantized (8 dp for
    quantities, 2 dp for NOK values, `ROUND_HALF_EVEN`); verbatim source strings
    (`quantity_in = qty`, `fee_quantity = fee`) pass through unrounded. Expect
    `30000.00000000` beside `30000.00` on the same `TRADE` — that is intended.
