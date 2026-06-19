# Tax Adapter Genesis — Design Note (v1: VARDE HP-1)

**Status:** Design — awaiting approval before writing-plans / code.
**Scope:** The Tax Adapter's first executable code. One producer (VARDE), one golden path (HP-1), one output (`events.csv`).
**Repo:** `C:\Users\mrkro\Documents\Tax adapter` (currently docs-only).

---

## Goal

Turn one VARDE `varde-fills.csv` row into the correct canonical `events.csv` rows,
deterministically and verified against a golden fixture — establishing the adapter's
architecture (seam, validation, test strategy) on the smallest real slice.

The contract is already pinned: **SCHEMAS.md §3.7** (the bilateral mapping +
HP-VARDE-001) and the frozen **20-column `events.csv`** (CONTRACTS.md Seam B), with
Taxes `src/tax_core/models/event.py` as the authoritative shape.

---

## The four architectural decisions

### 1. Seam — internal typed `Event` (validated) → serialize to `events.csv`

The adapter maps producer facts into a small **frozen `Event` dataclass that mirrors
the frozen 20-column `events.csv` contract** AND **replicates `event.py`'s
construction-time shape invariants** (fail-fast), then serializes to the CSV.

- **Why typed+validated, not dumb rows:** emitting an `events.csv` row that Taxes
  rejects at ingest is a silent failure. Mirroring `_validate_shape` (TRADE needs both
  legs; standalone FEE needs neither; quantities ≥ 0; 4 provenance keys; tz-aware
  timestamp) makes the adapter fail at build time, not at Taxes' intake.
- **Why mirror, not import (decision 4):** the seam is the **CSV contract**, not
  Taxes' Python class. The class is Taxes' implementation detail; coupling to it
  crosses the read-only repo boundary (ECOSYSTEM §5). The 20-col CSV is frozen, so a
  local mirror is stable; drift is guarded by a test (below).

### 2. Project shape — deliberately tiny

A minimal `uv` Python package (matches stack tooling: `uv run pytest`, Decimal-only,
py3.11+). One mapper, one CLI, one serialization layer, golden + unit tests. No
framework, no DB, no plugin system on day one.

### 3. Test strategy — golden HP-1 + a thin invariant net

- **`test_varde_hp1` (golden, the centerpiece):** map the vendored
  `hp1_nok_spot_buy.csv` → assert byte-equal to a pinned `hp1_expected_events.csv`
  (the TRADE + FEE rows from SCHEMAS §3.7).
- **`test_events_shape` (unit):** the validator invariants (TRADE both legs / FEE
  neither / negative qty rejected / missing provenance rejected / unknown type
  rejected) — these mirror `event.py` and protect the seam cheaply.
- **`test_events_conformance` (OPTIONAL, skip-if-unavailable):** if the Taxes package
  is importable locally, construct the **real** `CanonicalEvent` from each emitted row
  — proving CSV-compliance against ground truth *without* a build-time dependency.
  Skipped (not failed) when Taxes isn't on the path.
- **Column drift-guard:** assert the adapter's column set == the 20 documented
  `events.csv` columns.

### 4. Dependency boundary — Taxes as external contract (no runtime import in v1)

The adapter emits compliant `events.csv` rows; it does **not** import the Taxes model
package at runtime/build. Only the optional conformance test touches it, guarded by an
import-skip. Revisit direct import only if a stable local editable-install of Taxes is
deliberately set up.

---

## File tree (v1 scaffold)

```
Tax adapter/
  pyproject.toml                          # uv project; pytest; py3.11+; stdlib + Decimal only
  src/tax_adapter/
    __init__.py
    events.py                             # Event (frozen dataclass, 20-col mirror) + validate() + EVENTS_COLUMNS + write_events_csv()
    producers/
      __init__.py
      varde.py                            # read_varde_fills(path) + map_varde_fills(rows) -> list[Event]  (SCHEMAS §3.7)
    cli.py                                # python -m tax_adapter.cli --producer varde --in <fills.csv> --out <events.csv>
  tests/
    __init__.py
    fixtures/
      varde/hp1_nok_spot_buy.csv          # vendored copy of VARDE's HP-1 (source: Offshore trading/varde/fixtures/export/)
      varde/hp1_expected_events.csv       # byte-pinned expected 2-row events.csv output
    test_events_shape.py
    test_varde_hp1.py
    test_events_conformance.py            # optional, skip-if-Taxes-not-importable
```

> **Fixture vendoring:** the adapter test owns a *copy* of HP-1 as its pinned input
> (self-contained, no cross-repo path dependency). Source noted in a header comment;
> HP-1 is frozen so drift risk is low.

---

## The `Event` type (mirrors `events.csv` 20 cols / `event.py`)

Fields: `event_id, timestamp (tz-aware), event_type, source_id, source_row_index,
asset_out, quantity_out, asset_in, quantity_in, fee_asset, fee_quantity,
income_subtype, label, notes, nok_value_out, nok_value_in, parser, parser_version,
source_type, source_ref`. Decimals are `Decimal`; unused bilateral fields are `None`.

`validate()` enforces (per `event.py`): `event_type ∈ {TRADE, TRANSFER_IN/OUT, INCOME,
FEE, GIFT_IN/OUT, REQUIRES_REVIEW}`; TRADE ⇒ both legs; TRANSFER_IN/GIFT_IN/INCOME ⇒
in-only; TRANSFER_OUT/GIFT_OUT ⇒ out-only; standalone FEE ⇒ fee fields, no legs;
quantities ≥ 0; the 4 provenance keys non-empty; tz-aware timestamp.

---

## v1 mapping (VARDE, NOK-quoted spot buy = HP-1)

Per SCHEMAS §3.7: `side=buy` spot → **TRADE** (`asset_out=quote`,
`quantity_out=qty×price`; `asset_in=base`, `quantity_in=qty`) + standalone **FEE**.
NOK quote → `nok_value_out/in` = the NOK notional directly. `event_id =
varde:{run_id}:{trade_id}:{leg}`; `source_id = varde-fills:{book}`; `source_row_index`
from `(exchange_ts, trade_id, leg)`. The 4 provenance keys: `parser=varde_adapter`,
`parser_version=varde/1→event/1`, `source_type=varde-fills`,
`source_ref=varde-fills.csv#{trade_id}`.

---

## Acceptance criteria — first executable slice

1. `test_varde_hp1` green: `hp1_nok_spot_buy.csv` → exactly **two** rows equal to the
   pinned expected output:
   - **TRADE** — `asset_out=NOK, quantity_out=30000.00000000, asset_in=BTC,
     quantity_in=0.05000000, nok_value_out=30000.00, nok_value_in=30000.00,
     event_id=varde:varde-run-2026-03-02:varde-1:0, source_row_index=0`, 4 provenance
     keys populated.
   - **FEE** — `fee_asset=NOK, fee_quantity=150.00000000,
     event_id=varde:varde-run-2026-03-02:varde-1:1, source_row_index=1`.
2. `test_events_shape` green (validator invariants).
3. `test_events_conformance` green-or-skipped (real `CanonicalEvent` accepts both rows
   when Taxes is importable).
4. CLI: `python -m tax_adapter.cli --producer varde --in <fixture> --out <tmp>`
   produces the 2-row CSV; re-run is byte-identical (deterministic, idempotent).
5. `uv run pytest` green.

---

## v1 NON-GOALS (explicit)

- **Other VARDE shapes** — sell (TRADE base-out/quote-in), USDC/USDT-quoted (still a
  TRADE; needs `fx_usdnok_at_fill`; missing FX → `nok_value=None` UNRESOLVED), and XRPL
  wallet↔CEX transfers (linked TRANSFER_OUT/IN). **Documented in SCHEMAS §3.7,
  deferred to slice 2.** v1 mapper raises a clear `NotImplementedError` (or routes
  `REQUIRES_REVIEW`) for these rather than guessing.
- **Other producers** (trade_ledger / SovereignForge / PM algo / arb-bot).
- **Runtime coupling to the Taxes package** (optional conformance test only).
- **Any valuation/FX fetching** — the adapter never invents FX (A2); it passes through
  what the producer supplied.
- **Tax characterization, FIFO, capital-router/allocation** — out of scope by contract,
  forever (these belong to Taxes / the capital router).
- **Counted-skip framework, multi-file batching, config system** — not on day one.

---

## Next steps after approval

1. writing-plans → a reversible-slice implementation plan (scaffold → `events.py` +
   validator (TDD) → `producers/varde.py` mapper (TDD against HP-1) → CLI → conformance
   test).
2. Slice 2 (separate): the deferred VARDE shapes (sell / USDT / transfer) with unit
   tests, extending the same `Event`/validator.
