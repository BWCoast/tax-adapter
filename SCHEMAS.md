# SCHEMAS — the mapping contract

The adapter is a function:

```
f(trade_ledger_rows, exports, source_meta) -> canonical_tax_events[]
```

It owns exactly one thing: a **deterministic, lossless-where-possible,
explicit-where-not** mapping from each upstream record to one or more
canonical tax `Event` rows. This file is that mapping. It is the spec the
implementation is tested against.

Two anchors, both read-only to this repo:
- **Upstream:** `trade_ledger` — Trading `SCHEMAS.md` (frozen by ADR-005/L17).
- **Downstream:** canonical `Event` — Taxes `ADR-0001`, the 20-column
  `events.csv` intake.

> **Implementation status — verified 2026-09-29 (`uv run pytest`: 28 passed, 0
> skipped).** Exactly **one** mapping is implemented in code: **VARDE NOK-quoted
> spot buy → `TRADE` + `FEE`** (§3.7, `src/tax_adapter/producers/varde.py`). Every
> other row/section below is **specification only** — the mapper for it does not
> exist yet. Known v1 gaps between this spec and the code are listed at the end of
> §3.7 (M2: no silent landmines).

---

## 1. Downstream target — canonical tax Event (Taxes ADR-0001)

> **Reconciled 2026-09-29 (ADR-004).** This section previously described a
> single-sided `asset / quantity / nok_value` row with `event_type ∈ {DISPOSAL,
> ACQUISITION, SWAP, …}`. That was wrong: Taxes `src/tax_core/models/event.py`
> (`CanonicalEvent`) is **bilateral** and has **no** `ACQUISITION`/`DISPOSAL`/`SWAP`
> type. The owning contract wins (ECOSYSTEM §3); this section now mirrors it.

Every emitted row is the frozen **20-column `events.csv`** (header-name matched;
Taxes `ADR-0001`, hub `CONTRACTS.md` Seam B). The adapter's `Event` dataclass
(`src/tax_adapter/events.py`) mirrors it and re-checks the construction-time shape
rules so a row Taxes would reject fails here first.

| column(s) | req | notes |
|---|---|---|
| `event_id` | R | deterministic from source ids (A5): `{prefix}{run_id}:{trade_id}:{leg}`. **Reserved by Taxes ADR-0001 addendum 2026-07-13 (Accepted):** `ledger:` (trade_ledger mapper, unbuilt), `varde:` (**emitted today** — Taxes' addendum still says "not yet emitted"), `arb:` (reserved, unbuilt). **`pm-algo:` is ratified only as a `provenance.algo` label, *not* an `event_id` prefix** — so a PM-algo mapper's `event_id` prefix is **unreserved (OPEN: Taxes + adapter)**; hub `CONTRACTS.md` §3 / Example C still show it as an `event_id` prefix. Registry of record: Taxes ADR-0001 addendum — never emit an unreserved prefix |
| `timestamp` | R | tz-aware; from producer `exchange_ts` (UTC), serialized `…Z`. Europe/Oslo year bucketing is downstream (A1 / hub S10) |
| `event_type` | R | one of `TRADE`, `TRANSFER_IN`, `TRANSFER_OUT`, `INCOME`, `FEE`, `GIFT_IN`, `GIFT_OUT`, `REQUIRES_REVIEW` |
| `source_id`, `source_row_index` | R | e.g. `varde-fills:lab`; the index is the deterministic tie-breaker for FIFO (Taxes ADR-0002) |
| `asset_out`, `quantity_out`, `asset_in`, `quantity_in` | per type | the two legs; `Decimal`, always ≥ 0, direction lives in the type (A7). Unused leg columns are blank. v1 emits bare symbols (`NOK`, `BTC`); qualified keys (`SYMBOL.contract`, Taxes ADR-0021) for tokens are not yet needed by any implemented mapping |
| `fee_asset`, `fee_quantity` | per type | fee on any event, or the sole payload of a standalone `FEE` |
| `income_subtype`, `label`, `notes` | opt | `notes` is **write-only** overflow metadata — no logic may parse it |
| `nok_value_out`, `nok_value_in` | opt | advisory; blank = UNRESOLVED, **never fabricated** (A2). The adapter passes through what the producer captured; it does not invent FX |
| `parser`, `parser_version`, `source_type`, `source_ref` | R | the four mandatory provenance keys (non-empty on every row) |

**Shape rules** (enforced at construction by Taxes and mirrored in
`Event.validate()`): `TRADE` ⇒ both legs · `TRANSFER_OUT`/`GIFT_OUT` ⇒ out-leg only ·
`TRANSFER_IN`/`GIFT_IN`/`INCOME` ⇒ in-leg only · standalone `FEE` ⇒ fee fields only,
no legs · `REQUIRES_REVIEW` ⇒ shape unconstrained.

**Vocabulary.** "acquisition", "disposal" and "swap" survive in this repo's older
prose only as descriptive shorthand for what a `TRADE` *means*. They are **not**
valid `event_type` values; whenever they appear below, read them as resolving into
`TRADE` / `TRANSFER_*` rows. The richer provenance (`decision_id`, `order_id`,
`experiment_hash`, `git_commit`, raw row, …) is the adapter's additional dict, not
`events.csv` columns.

---

## 2. Upstream source — trade_ledger row (Trading SCHEMAS.md, L17)

Fields the adapter consumes: `venue, account, instrument(symbol,
product_type, base, quote, settle), order_id, trade_id, decision_id,
strategy_id, mode, book, side, qty, price, fee, fee_asset, fill_kind,
realized_pnl_quote, fx_usdnok_at_fill, exchange_ts, recv_ts, run_id,
session_id, git_commit, schema_version`.

Two fields drive the mapping: **`product_type`** (spot vs linear_perp/inverse)
and **`fill_kind`** (maker/taker/funding/liquidation/settlement). A spot fill
transfers asset ownership (acquisition/disposal); a derivative fill does not —
its only tax-relevant output is realized PnL in the settle asset.

---

## 3. The mapping (the load-bearing table)

> **Rule of construction (A3):** where a mapping is jurisdiction-sensitive or
> the upstream record is ambiguous, the adapter emits `REQUIRES_REVIEW` with a
> reason — it never silently picks a safer-looking type. event_type is a
> *normalization*, not a tax ruling; the deterministic tax core makes the
> ruling (A4).

> **Recognized producers (`trade_ledger` v3 sources):** **MM/Trading lab**
> (`book=lab|accrual`) and **SovereignForge** (`book=accrual`,
> `strategy_id=ofg_dca`, promotion 2026-06-14, PROPOSED). Any future producer
> that conforms to the v3 contract byte-for-byte joins this list. PM algo
> conforms to its own §3.4 export contract, not trade_ledger. Per-producer
> handling rulings live in this section's footnotes below the §3.4
> sub-table.

### 3.1 Spot fills (`product_type = spot`)

A spot trade transfers ownership in both directions, so in the bilateral model
(§1) **every** spot fill is one `TRADE` carrying both legs, plus a standalone
`FEE`. The quote-asset distinction no longer changes the event *type* — it only
changes whether `nok_value` needs FX:

| ledger row | emitted events |
|---|---|
| `side=buy` | `TRADE` (`asset_out=quote`, `quantity_out=qty×price`; `asset_in=base`, `quantity_in=qty`) + `FEE` |
| `side=sell` | `TRADE` (`asset_out=base`, `quantity_out=qty`; `asset_in=quote`, `quantity_in=qty×price`) + `FEE` |
| quote = fiat (NOK) | `nok_value_out/in` = the NOK notional directly; no FX tier needed |
| quote = crypto/stablecoin | `nok_value` needs `fx_usdnok_at_fill` `{rate, source, as_of_ts}`; if absent → blank/UNRESOLVED (A2), surfaced for review |
| `fee > 0` | standalone `FEE` (`fee_asset`, `fee_quantity=fee`) |

The Norwegian rule that a stablecoin-quoted buy is **not** a clean one-sided
acquisition (GOTCHA 2) is preserved, not lost: the stablecoin disposal is the
`asset_out` leg of the `TRADE`, and the Taxes core rules on it (A4). What the
old single-sided shape got wrong was pretending a fiat buy had no out-leg.

> **Status:** implemented only for VARDE NOK-quoted spot **buy** (§3.7). Sell,
> stablecoin-quoted, and the `trade_ledger`/SovereignForge mappers are spec only.

`book=accrual` spot buys (DCA/conviction, Trading ADR-006) map identically —
the adapter does not special-case books for *type*; `book` is carried into
`source_id`/provenance so downstream can separate lab vs accrual lots cleanly.

#### Worked example: HP-SF-001 — OFG XRP/USDC buy (NO, live, FX populated)

> **⚠ Legacy notation (flagged 2026-09-29, ADR-004).** The Event rows below were
> written in the pre-reconciliation single-sided shape (`ACQUISITION`, `asset`,
> `quantity`, `nok_value`), and their remark that the USDC disposal leg is
> "out-of-scope" is **superseded**: under §1/§3.1 this fill is one bilateral
> `TRADE` (`asset_out=USDC`, `quantity_out=50.0`, `asset_in=XRP`,
> `quantity_in=100.0`) + a standalone `FEE`, and the Taxes core — not the adapter —
> rules on the USDC leg. The **input row, provenance rulings and FX rulings** below
> remain the pinned content. The rows are left verbatim because this example is a
> `PROPOSED` artifact owned by the SovereignForge recognition proposal
> (`proposals/sf_producer_recognition_PROPOSED.md`); re-pin it there when that is
> ratified. No SovereignForge mapper exists in code yet.

> **Status:** PROPOSED 2026-06-14 alongside the SovereignForge per-producer
> handling rulings in §3.6 + the Taxes ADR-0001 identifier-namespace addendum.
> Pinned by `proposals/sf_producer_recognition_PROPOSED.md`.

The first SovereignForge worked example mirrors Trading's HP-1 spine: a single
fiat- or stablecoin-quoted spot buy → `ACQUISITION` + `FEE`. SovereignForge
runs OFG-DCA (book=accrual) USDC-quoted on Bybit-EU. For the Norwegian operator
the FX columns are populated from Norges Bank EOD lookup at export time
(provenance label `derived_at_export`), so the adapter has tier-1 NOK input
without invented numbers.

**Input — one `trade_ledger/3` row** (byte-output of SF's exporter test
`tests/exports/test_trade_ledger_export.py::test_validate_row_passes_no_row_with_fx`;
this row IS the first golden fixture — no hand-reconstruction):

```
venue,account,instrument_symbol,instrument_product_type,instrument_base,instrument_quote,instrument_settle,order_id,trade_id,decision_id,strategy_id,experiment_hash,mode,book,side,qty,price,fee,fee_asset,fill_kind,realized_pnl_quote,fx_rate,fx_source,fx_as_of_ts,exchange_ts,recv_ts,run_id,session_id,git_commit,schema_version
bybit,sf_personal_main,XRP/USDC,spot,XRP,USDC,USDC,ord_xrp_001,trd_bybit_xrp_001,mica:2026-07-15T09:23:11Z:xrp_001,ofg_dca,,live,accrual,buy,100.0,0.5,0.05,USDC,taker,0,10.7421,norgesbank.eod,2026-07-15,2026-07-15T09:23:11Z,2026-07-15T09:23:11Z,r,s,c,trade_ledger/3
```

**Producer-side counted reason emitted with this fill** (exactly one, scoped):

```
fill_kind_defaulted_to_taker_sf_does_not_capture
```

**Output — exactly two canonical Event rows** (per §3.1 row 1 / row 2: stablecoin-
quoted buy is technically a SWAP under §3.1's table, but the operator's tax core
treats USDC at the disposal leg as out-of-scope for the first SF golden fixture —
HP-SF-002 will revisit when BE jurisdiction comes back into scope. HP-SF-001 emits
the `ACQUISITION` + `FEE` pair, mirroring Trading HP-1's spine):

**HP-SF-001-A — ACQUISITION leg**

```
event_id:          ledger:r:trd_bybit_xrp_001:0     # adapter ledger:{run}:{trade_id}:{leg} convention; SF identifiers flow to provenance
timestamp:         2026-07-15T09:23:11Z             # from exchange_ts (UTC); Oslo reporting happens downstream
event_type:        ACQUISITION
asset:             XRP
quantity:          100.0                            # Decimal, positive (from trade_ledger qty)
nok_value:         537.105                          # 100.0 × 0.5 × 10.7421 = qty × price × fx_rate
source_id:         trade_ledger:sf_personal_main    # identifies producer + path (SF trade_ledger feed)
source_row_index:  0                                # stable sort key within this source_id
provenance:        {adapter_schema_version: "trade_ledger/3→event/1",
                    producer: "sovereignforge",
                    strategy_id: "ofg_dca",
                    decision_id: "mica:2026-07-15T09:23:11Z:xrp_001",  # SF identifier; sf:/mica:/sf:ofg: namespaces live here (Taxes ADR-0001 addendum 2026-06-14 PROPOSED)
                    order_id: "ord_xrp_001",
                    trade_id: "trd_bybit_xrp_001",
                    venue: "bybit",
                    instrument_symbol: "XRP/USDC",
                    side: "buy",
                    mode: "live",
                    book: "accrual",
                    quote_asset: "USDC",
                    quote_price: "0.5",
                    fx_rate: "10.7421",
                    fx_source: "norgesbank.eod",
                    fx_as_of_ts: "2026-07-15",
                    fx_resolution: "derived_at_export_norgesbank_eod_pending_fill_time_upgrade",
                    recv_ts_equals_exchange_ts: true,
                    fill_kind: "taker",
                    fill_kind_source: "defaulted_by_sf",                # soft REQUIRES_REVIEW signal per §3.6, not a structural error
                    producer_counted_reasons: ["fill_kind_defaulted_to_taker_sf_does_not_capture"],
                    raw_row: {…verbatim trade_ledger row reference}}
```

**HP-SF-001-B — FEE leg**

```
event_id:          ledger:r:trd_bybit_xrp_001:1     # same trade, second leg
timestamp:         2026-07-15T09:23:11Z
event_type:        FEE
asset:             USDC
quantity:          0.05                             # fee amount in quote asset
nok_value:         0.537105                         # 0.05 × 10.7421
source_id:         trade_ledger:sf_personal_main
source_row_index:  0                                # same source row; leg index is in event_id
provenance:        {adapter_schema_version: "trade_ledger/3→event/1",
                    producer: "sovereignforge",
                    strategy_id: "ofg_dca",
                    decision_id: "mica:2026-07-15T09:23:11Z:xrp_001",
                    order_id: "ord_xrp_001",
                    trade_id: "trd_bybit_xrp_001",
                    venue: "bybit",
                    instrument_symbol: "XRP/USDC",
                    side: "buy",
                    mode: "live",
                    book: "accrual",
                    quote_asset: "USDC",
                    quote_price: "0.5",
                    fee_asset: "USDC",
                    fx_rate: "10.7421",
                    fx_source: "norgesbank.eod",
                    fx_as_of_ts: "2026-07-15",
                    fx_resolution: "derived_at_export_norgesbank_eod_pending_fill_time_upgrade",
                    recv_ts_equals_exchange_ts: true,
                    fill_kind: "taker",
                    fill_kind_source: "defaulted_by_sf",
                    producer_counted_reasons: ["fill_kind_defaulted_to_taker_sf_does_not_capture"],
                    raw_row: {…verbatim trade_ledger row reference}}
```

**Notes pinned by HP-SF-001:**

- No fee-related counted reason fires, because `fee_asset == quote_asset == USDC`.
  HP-SF-004 will be where `fee_in_non_quote_currency_normalize_unavailable` shows up.
- All SF-specific wrinkles (fill_kind defaulting, recv_ts equality, FX provenance) live
  inside `provenance`, NOT as top-level Event fields, so ADR-0001's 9-field contract
  stays intact.
- `event_id` uses the adapter's existing `ledger:{run}:{trade_id}:{leg}` convention.
  SF's `mica:...` (or `sf:ofg:...` when MiCA Art.68 ID is absent — see HP-SF-005)
  identifier flows into `provenance.decision_id`. The Taxes ADR-0001 addendum reserves
  the `sf:` / `sf:ofg:` namespaces at the provenance-identifier layer, NOT at the
  event_id layer (which remains adapter-owned and `ledger:`-prefixed).
- `nok_value` for both legs is computed at the adapter using the SF-supplied tier-1
  FX rate (`derived_at_export` provenance). HP-SF-001 is the concrete realization of
  the §3.6 FX ruling: SF's Norges Bank EOD rate is tier-1 for NOK valuation, with the
  `fx_resolution` audit note carried in provenance.

**Stub list — HP-SF-002 through HP-SF-005** (extend the SF spine in future passes):

```
HP-SF-002 — BE-jurisdiction export
  Same trading pattern as HP-SF-001 but with jurisdiction=BE. FX columns
  remain empty; adapter FX checks fail, signalling that BE operators should
  continue to use the existing DAC8 + tax_export path, not the SF exporter,
  for production tax reporting.

HP-SF-003 — Partial fill
  event_type="partial" on the source FillRecord; one order_id expanded to
  multiple trade_ledger rows with distinct trade_id and qty. Pins the per-fill
  granularity and how these map to one or more ACQUISITION Events.

HP-SF-004 — Fee in non-quote currency
  fee_asset != instrument_quote (e.g. XRP fee on XRP/USDC, or a third
  currency). Exercises the fee_in_non_quote_currency_normalize_unavailable
  counted reason and pins FEE-leg handling when only partial fee info exists.

HP-SF-005 — mica_event_id absent
  decision_id synthesized as sf:ofg:{order_id} because the MiCA Art.68 ID
  is missing. Pins how the adapter treats sf:ofg: in provenance.decision_id
  and how that flows into event_id derivation, if at all.
```

### 3.2 Derivative fills (`product_type = linear_perp | inverse | …`)

A perp open/close does **not** transfer ownership of the underlying — so the
adapter does NOT emit ACQUISITION/DISPOSAL of BTC/XRP for perps. The only
tax-relevant economic events are realized PnL and funding:

| fill_kind | emitted event | asset | notes |
|---|---|---|---|
| `maker`/`taker` with `realized_pnl_quote != 0` (a closing/reducing fill) | one realized-PnL event in `settle` asset | settle (e.g. USDC) | sign of `realized_pnl_quote` decides gain vs loss; characterization (income vs capital) is the tax core's job → see ADR-002 |
| `maker`/`taker` opening fill (`realized_pnl_quote == 0`) | none (position change only) | — | no taxable event on open; provenance row optionally logged, not a tax event |
| `funding` | `INCOME` (received, +) or `FEE` (paid, −) | settle | funding is periodic carry, not an ownership change |
| `liquidation` | realized-PnL event + flag | settle | forced close; same as a close, flagged in provenance |
| `settlement` | realized-PnL event | settle | contract settlement |
| any | `FEE` for `fee`/`fee_asset` | fee_asset | trading fee leg |

> **Open question, flagged not decided (ADR-002):** the *tax characterization*
> of derivative realized PnL (capital gain vs income; per-fill vs per-period
> netting) differs by jurisdiction and is NOT the adapter's call. The adapter
> emits a faithful, typed realized-PnL event with full provenance and lets the
> tax core classify. Until the tax core has an explicit derivative rule,
> these MAY route as `REQUIRES_REVIEW` (A3).

### 3.3 Internal book transfers (capital-router allocations, Trading ADR-006)

When the capital router skims lab realized PnL and moves it to the accrual
book, **no change of beneficial owner occurs** — it must not read as a taxable
disposal. The adapter emits a linked pair:

| router event | emitted events |
|---|---|
| `router_allocation` (lab → accrual) | `TRANSFER_OUT` (lab source) + `TRANSFER_IN` (accrual dest), linked by a shared `transfer_id` in provenance |

These rely on Taxes' transfer-linking (ADR-0007/0013). The adapter's job is to
emit them as a *linkable pair with matching asset/quantity/timestamp*, never as
disposal+acquisition. A subsequent accrual *buy* (a real market spot buy) is a
separate `TRADE` per §3.1.

> **Status:** spec only — no TRANSFER pair is emitted by any implemented mapper.
> The Capital Router that produces these moves is decided but unbuilt (hub
> `CAPITAL_ROUTER.md`, ADR-003; 25% Norway holdback into a `tax-reserve` book).

### 3.4 Prediction-market exports (PM algo, standalone)

The prediction bot runs standalone operationally but exports fills/PnL into the
adapter. A binary-contract resolution is realized PnL, not an ownership
transfer of a fungible asset:

| pm-algo record | emitted event | notes |
|---|---|---|
| contract buy/sell fill | realized-PnL or cost-basis event in quote (USD) | venue = Kalshi etc. |
| resolution payout | `INCOME` or realized gain in quote | characterization deferred (ADR-002), MAY be `REQUIRES_REVIEW` |
| fee | `FEE` | |
| deposit/withdrawal | `TRANSFER_IN`/`TRANSFER_OUT` | links to the funding account |

PM algo must supply the minimum export set: fills, fees, realized PnL,
deposits/withdrawals, year-end position snapshot if relevant. The adapter
defines that export contract (see SOURCES.md §3); the bot conforms to it.

### 3.5 Exchange CSVs (manual / non-bot sources)

Already-supported Taxes parsers (Firi, Coinbase, Kraken, etc.) feed `Taxes/`
directly and are **out of the adapter's scope** unless an engine routes through
an exchange the tax software can't parse. The adapter does not duplicate
existing CSV parsers.

---

### 3.6 Per-producer handling — SovereignForge (PROPOSED 2026-06-14)

> Pinned by `proposals/sf_producer_recognition_PROPOSED.md` per Perplexity audit
> 2026-06-14. Drops to settled when the SF producer recognition is ratified
> and the Taxes ADR-0001 `sf:`/`sf:ofg:` identifier-namespace addendum lands.
>
> **Concrete worked example: see HP-SF-001 at the end of §3.1.** That example
> realizes all three rulings below against a real exporter-generated CSV row,
> with both ACQUISITION and FEE leg provenance blocks pinned byte-faithfully.

SovereignForge's `FillRecord` is rich on regulatory fields (DAC8 HMAC chain, MiCA
Art.68 cross-link, ECB FX, BE TIN) but thin on a few `trade_ledger` v3 columns
that Trading defines as required. The adapter recognizes the gaps explicitly,
per producer, so SF rows ingest cleanly without forcing SF to invent data:

| trade_ledger column | SF behavior | Adapter ruling |
|---|---|---|
| `fill_kind` | SF emits `"taker"` + counted reason `fill_kind_defaulted_to_taker_sf_does_not_capture` (SF doesn't capture maker/taker per fill). | **Soft `REQUIRES_REVIEW` flag in `provenance.fill_kind_resolution = "defaulted_taker_producer_does_not_capture"`. Do NOT block ingestion; do NOT mark the entire Event as REQUIRES_REVIEW.** The Tax core may escalate later if maker/taker matters for the jurisdiction's fee classification. If a future SF wave adds maker/taker capture, SF drops the counted reason and the adapter treats those rows as fully resolved. |
| `recv_ts` | SF emits `recv_ts == exchange_ts` (SF doesn't track a separate receive timestamp) with provenance noting equality. | **Accept as "no extra latency info available." Do NOT mark as UNRESOLVED.** The equality is not a signal of producer error. If a later producer provides distinct `recv_ts`, the Taxes core uses it without penalizing SF. |
| `fx_rate` / `fx_source` / `fx_as_of_ts` | For NO operator: populated from Norges Bank EOD lookup at export time. Provenance label `"derived_at_export"` (not fill-time captured). For BE operator: empty (BE reports EUR, not NOK; BE flow uses SF's existing DAC8 + tax_export). | **Treat `fx_source="norgesbank.eod"` with provenance `"derived_at_export"` as tier-1 valuation, with an audit note: `provenance.fx_resolution = "derived_at_export_norgesbank_eod_pending_fill_time_upgrade"`.** This is honest — auditor sees the FX was looked up by date rather than captured at fill — but doesn't downgrade the tier prematurely. When SF ships fill-time NOK capture (a future SF wave), provenance flips to `"fill_time"` and the audit note drops. If Taxes core (ADR-0006/0010) later reclassifies derived-at-export as the warned fallback, this ruling updates in one place. |

Other SF rows that look like the MM/Trading lab shape (`venue`, `account`,
`order_id`, `trade_id`, Decimal-string `qty`/`price`/`fee`) follow §3.1 spot-fill
mapping unchanged. `book="accrual"` (OFG-DCA is by construction the accrual
book per Trading ADR-006); `strategy_id="ofg_dca"`; `decision_id` is the SF
`mica_event_id` when present, else synthesized as `sf:ofg:{order_id}` per
Taxes ADR-0001 addendum 2026-06-14 (PROPOSED).

---

### 3.7 VARDE — standalone declared export (bilateral target shape)

> **Producer:** VARDE (`Offshore trading`, `BWCoast/VARDE`) — educational Norwegian
> retail crypto PM. Facts-only producer (Trading Alignment ADR-004 / OPEN-12).
> Reserved `event_id` prefix **`varde:`**. Transport: append-only
> `db-backup/varde-fills.csv`, schema `varde/1` (see SOURCES.md §5).
>
> **Shape note.** VARDE conforms to the adapter's *own* export contract (not
> `trade_ledger` v3) — same per-producer pattern as PM algo (§3.4) and arb-bot. This
> section was the first written natively in the **real bilateral `CanonicalEvent`
> shape** verified against Taxes `src/tax_core/models/event.py`; §1, §3.1 and §7 were
> reconciled to it on 2026-09-29 (ADR-004), closing the ECOSYSTEM FINDING of
> 2026-06-18.
>
> **Implementation status — verified 2026-09-29.** The **NOK-quoted spot BUY**
> (HP-VARDE-001 below) is implemented and golden-pinned
> (`src/tax_adapter/producers/varde.py`; `tests/test_varde_hp1.py`; the emitted CSV is
> byte-identical to `tests/fixtures/varde/hp1_expected_events.csv` and re-runs are
> byte-identical). **Not implemented** — the mapper raises `NotImplementedError`
> (fail-closed, A3; it never guesses): spot **sell**, **stablecoin-quoted** fills,
> **XRPL transfers**, non-spot `product_type`.
>
> **Known v1 gaps — code vs this spec (labelled, not silent):**
> 1. **`source_row_index` follows input order**, not the stable sort
>    `(exchange_ts, trade_id, leg)` specified below and in §4. Verified: a
>    later-timestamp row listed first receives index 0. Canonical sort is slice-2 work;
>    until then inputs must already be in canonical order or FIFO tie-breaks are wrong.
> 2. **A `FEE` event is emitted even when `fee == 0`**; this spec says only when
>    `fee > 0`.
> 3. **A blank `fee` (spec: "missing = blank, never 0") crashes** with a bare
>    `decimal.InvalidOperation` instead of routing to `REQUIRES_REVIEW` with a counted
>    reason (§5). Fail-closed by accident, not by design.
> 4. **No counted-skip ledger** (§5 invariant `sum(skip_reasons) == n_unmapped`) —
>    unmapped shapes abort the run rather than being counted.
> 5. **No `raw_row`/rich provenance dict** — only the four mandatory provenance keys
>    and the write-only `notes` string are emitted; `events.csv` has no column for the
>    richer dict shown in the worked example.

**Input — one `varde-fills.csv` row (`varde/1`, consumed columns):**
`source_row_id, exchange_ts, venue, symbol, product_type, base, quote, side, qty,
price, fee, fee_asset, fill_kind, realized_pnl_quote, fx_usdnok_at_fill, order_id,
trade_id, strategy_id, book, mode, run_id`. Decimal strings are verbatim (period
separator); missing = blank, never `0`; `realized_pnl_quote` is always `"0"` (VARDE
is spot-only); the producer's internal `pnl` is **not** exported.

**The mapping — in the bilateral model the quote-currency distinction collapses.**
Every spot fill is a single **`TRADE`** (both legs present) plus a standalone
**`FEE`**; the only difference between a NOK-quoted and a USDC/USDT-quoted fill is
whether `nok_value` needs `fx_usdnok_at_fill`. (Single-sided "ACQUISITION vs SWAP" is
an artifact of the old shape — a `TRADE` already carries both legs.)

| varde-fills row | emitted events |
|---|---|
| `product_type=spot`, `side=buy` | `TRADE` (`asset_out=quote`, `quantity_out=qty×price`; `asset_in=base`, `quantity_in=qty`) + `FEE` |
| `product_type=spot`, `side=sell` | `TRADE` (`asset_out=base`, `quantity_out=qty`; `asset_in=quote`, `quantity_in=qty×price`) + `FEE` |
| quote = NOK (Firi) | `nok_value_out/in` = the NOK notional directly (`qty×price`); no FX tier needed |
| quote = USDC/USDT (Kraken/Binance/ByBit) | `nok_value` requires `fx_usdnok_at_fill` `{rate,source,as_of_ts}`; if absent → `nok_value=None` (UNRESOLVED, A2), surfaced for review |
| XRPL wallet ↔ CEX transfer (same asset, no price) | linked `TRANSFER_OUT` + `TRANSFER_IN` pair (matching asset/qty/ts, shared `transfer_id` in provenance) — never a `TRADE` |
| any fill with `fee > 0` | standalone `FEE` (`fee_asset`, `fee_quantity=fee`) |

`event_id = varde:{run_id}:{trade_id}:{leg}` (TRADE = leg 0, FEE = leg 1).
`source_id = varde-fills:{book}` (e.g. `varde-fills:lab`). `source_row_index` from the
stable sort `(exchange_ts, trade_id, leg)`.

#### Worked example: HP-VARDE-001 — Firi BTC/NOK spot buy (the HP-1 fixture)

**Input** — the byte-pinned VARDE fixture `fixtures/export/hp1_nok_spot_buy.csv` (one
row): `firi`, `BTC/NOK`, `spot`, `buy`, `qty=0.05000000`, `price=600000.00000000`,
`fee=150.00000000`, `fee_asset=NOK`, `fill_kind=taker`,
`fx_usdnok_at_fill={"rate":"10.7421","source":"norgesbank.eod","as_of_ts":"2026-03-02T00:00:00Z"}`,
`order_id=varde-ord-1`, `trade_id=varde-1`, `strategy_id=dca_v1`, `book=lab`,
`mode=live`, `run_id=varde-run-2026-03-02`, `exchange_ts=2026-03-02T10:15:30Z`.

**Output — exactly two `CanonicalEvent` rows.** NOK is home fiat, so the Taxes core
will treat the NOK out-leg as a non-taxable home-fiat movement — but the event is still
a structurally-valid bilateral `TRADE`; the adapter does not pre-decide that, it emits
the full swap and lets the core rule (A4).

**Event 0 — TRADE**
```
event_id:          varde:varde-run-2026-03-02:varde-1:0
timestamp:         2026-03-02T10:15:30Z          # tz-aware, from exchange_ts; Oslo reporting downstream
event_type:        TRADE
asset_out:         NOK
quantity_out:      30000.00000000                # qty × price = 0.05 × 600000
asset_in:          BTC
quantity_in:       0.05000000
nok_value_out:     30000.00                       # advisory (quote=NOK → notional direct)
nok_value_in:      30000.00
source_id:         varde-fills:lab
source_row_index:  0                              # stable sort (exchange_ts, trade_id, leg)
provenance:        {parser: "varde_adapter", parser_version: "varde/1->event/1",
                    source_type: "varde-fills", source_ref: "varde-fills.csv#varde-1",
                    producer: "varde", strategy_id: "dca_v1", order_id: "varde-ord-1",
                    trade_id: "varde-1", venue: "firi", instrument: "BTC/NOK", side: "buy",
                    mode: "live", book: "lab", run_id: "varde-run-2026-03-02",
                    fx_usdnok_at_fill: {rate:"10.7421", source:"norgesbank.eod", as_of_ts:"2026-03-02T00:00:00Z"},
                    raw_row: {…verbatim varde-fills row}}
```

**Event 1 — FEE**
```
event_id:          varde:varde-run-2026-03-02:varde-1:1
timestamp:         2026-03-02T10:15:30Z
event_type:        FEE
fee_asset:         NOK
fee_quantity:      150.00000000
nok_value_out:     150.00                         # advisory; fee already in home fiat NOK
source_id:         varde-fills:lab
source_row_index:  1
provenance:        {… same chain as Event 0, leg: 1 …}
```

The four required provenance keys (`parser`, `parser_version`, `source_type`,
`source_ref`) are mandatory on every event (`event.py` `_validate_provenance`); the
richer dict is the adapter's additional provenance. Quantities are positive (A7);
`event.py` enforces the `TRADE` (both legs) and standalone-`FEE` (no legs) shapes at
construction.

> **Why a purchase is a `TRADE`, not a one-sided acquisition.** The real
> `CanonicalEvent` has **no** `ACQUISITION` type, and `_validate_shape` rejects a
> one-sided "in" that isn't `TRANSFER_IN`/`GIFT_IN`/`INCOME`. The faithful
> representation of a purchase is a `TRADE` with home-fiat on the out-leg. §7 (the
> `trade_ledger` HP-1) was aligned to this shape on 2026-09-29 and is now the same
> `TRADE` + `FEE` pair — spec only, since the `trade_ledger` mapper is not built.

---

## 4. Determinism & idempotency (A5)

- `event_id` is a pure function of upstream identifiers (`run_id`, `trade_id`,
  `leg`) — re-importing the same ledger produces byte-identical events.
- `source_row_index` is assigned by a stable sort of upstream rows
  (`(exchange_ts, trade_id, leg)`) so FIFO ordering downstream is reproducible
  (Taxes ADR-0002).
- The mapping has no clock, no randomness, no network call. Same input → same
  events, always (mirrors Taxes deterministic-core principle).

> **v1 status (verified 2026-09-29):** no-clock/no-randomness/no-network and
> byte-identical re-runs **hold and are tested**. The stable sort for
> `source_row_index` is **not yet implemented** — v1 preserves input order (see the
> §3.7 known-gaps list).

## 5. Validation (what the adapter refuses)

> **v1 status (verified 2026-09-29):** the fail-closed half is implemented — an
> unmapped shape raises `NotImplementedError` and a shape-invalid row raises
> `EventShapeError` (`Event.validate()`); nothing is emitted past a failure. The
> **counted-skip ledger and `REQUIRES_REVIEW` routing described below are not yet
> built**; a blank `fee` currently surfaces as an uncaught `decimal.InvalidOperation`.

Per A2/A3, the adapter emits but also gate-checks:
- missing `fx_usdnok_at_fill` on a row needing NOK value → `nok_value=None`
  (UNRESOLVED), surfaced for review — never back-filled by the adapter.
- unknown `product_type`/`fill_kind`, or an asset that can't be resolved to a
  qualified key → `REQUIRES_REVIEW` with a counted reason.
- every skipped/unmapped row gets a counted reason; invariant:
  `sum(skip_reasons) == n_unmapped` (PM algo lesson — uncounted drops drift
  accounting silently).

## 6. Schema versioning

Both anchored schemas are additive-versioned (Trading L6, Taxes ADR-0004). The
mapping carries an `adapter_schema_version` in provenance; new upstream fields
are absorbed additively, existing mappings never change meaning without a new
ADR superseding this file.

---

## 7. Happy Path 1 — MM Strategy spot buy (end-to-end worked example)

> **Status (verified 2026-09-29): SPEC ONLY — the `trade_ledger` mapper is not
> built.** ADR-003 named MM/Trading as the first producer to wire; in practice the
> first *executable* slice was **VARDE's** identical shape (§3.7, HP-VARDE-001),
> because VARDE had real exported fills and Trading is still pre-edge (ADR-004).
> This section remains the contract the Trading HP-1 mapper will be pinned to
> (fixture: `Trading/fixtures/trade_ledger/hp1_spot_buy.csv`), and its output is now
> the same bilateral `TRADE` + `FEE` pair the VARDE mapper already emits.

The second path (ADR-003 originally the first): **MM Strategy Bot / Trading
lab → adapter → Taxes intake**, deliberately the simplest scenario — one vanilla
**fiat-quoted spot buy**, one venue, `book=lab`, no derivative, no stablecoin
quote, no transfer. Because the quote is NOK, `nok_value` needs no FX tier. The
output is one `TRADE` (NOK out, BTC in) plus a standalone `FEE`.

> Later happy paths extend this spine, not replace it: **HP-2** adds a
> stablecoin-quoted buy (same `TRADE` shape; `nok_value` needs FX, §3.1); **HP-3**
> adds a derivative realized-PnL fill (§3.2, characterization per ADR-002).
> Spot-only first.

### 7.1 Input — one `trade_ledger` row (the only consumed fields shown)

> **Verified 2026-09-29** against `Trading/fixtures/trade_ledger/hp1_spot_buy.csv`:
> every value below matches that pinned fixture row. Notation differs only in that
> the fixture is flat CSV (`instrument_symbol`, `instrument_product_type`, …,
> `fx_rate`, `fx_source`, `fx_as_of_ts` rather than nested `instrument.*` /
> `fx_usdnok_at_fill{…}`). The Trading mapper will read the flat columns.

```
venue:               kraken
account:             lab-main
instrument.symbol:   BTC/NOK
instrument.product_type: spot
instrument.base:     BTC
instrument.quote:    NOK
instrument.settle:   NOK
order_id:            ord_8f31
trade_id:            trd_a12b
decision_id:         dec_77c0
strategy_id:         mm_v1
mode:                live
book:                lab
side:                buy
qty:                 0.05000000          # Decimal, BTC acquired
price:               600000.00           # Decimal, NOK per BTC
fee:                 150.00              # Decimal
fee_asset:           NOK
fill_kind:           taker
realized_pnl_quote:  0                   # a buy — no realized PnL
fx_usdnok_at_fill:   {rate: "10.7421", source: "norgesbank.eod", as_of_ts: "2026-03-02T00:00:00Z"}
exchange_ts:         2026-03-02T10:15:30Z
recv_ts:             2026-03-02T10:15:30.412Z
run_id:              run_2026_03_02_001
session_id:          sess_5e
git_commit:          a1b2c3d
schema_version:      trade_ledger/3
```

### 7.2 Output — exactly two canonical `Event` rows

Per §3.1 (spot buy → one bilateral `TRADE`, plus a standalone `FEE` for the
non-zero fee). Because the quote is NOK, `nok_value_out/in` is the NOK notional
`qty × price` directly (no FX applied); the fee is already NOK. The adapter performs
no tax math — only the quote-currency notional and a verbatim fee pass-through. The
four mandatory provenance keys (`parser`, `parser_version`, `source_type`,
`source_ref`) are populated on both rows; their `trade_ledger` values are fixed when
that mapper is built (the VARDE analogue is `varde_adapter` / `varde/1->event/1` /
`varde-fills` / `varde-fills.csv#{trade_id}`).

**Event 0 — TRADE**
```
event_id:          ledger:run_2026_03_02_001:trd_a12b:0
timestamp:         2026-03-02T10:15:30Z            # from exchange_ts (UTC); reported Europe/Oslo downstream
event_type:        TRADE
asset_out:         NOK
quantity_out:      30000.00000000                   # qty × price = 0.05 × 600000
asset_in:          BTC
quantity_in:       0.05000000                       # Decimal, positive
nok_value_out:     30000.00                          # advisory; quote=NOK → notional direct
nok_value_in:      30000.00
source_id:         trade_ledger:lab
source_row_index:  0                                 # stable sort key (exchange_ts, trade_id, leg)
notes:             write-only overflow, e.g. decision_id=dec_77c0;strategy_id=mm_v1;book=lab;mode=live
```

**Event 1 — FEE**
```
event_id:          ledger:run_2026_03_02_001:trd_a12b:1
timestamp:         2026-03-02T10:15:30Z
event_type:        FEE
fee_asset:         NOK
fee_quantity:      150.00                            # Decimal, positive
nok_value_out:     150.00                            # advisory; fee already in NOK
source_id:         trade_ledger:lab
source_row_index:  1
```

There is no separate "NOK disposal" row: the NOK out-leg is carried **inside** the
`TRADE`. NOK is home fiat, so the Taxes core will treat that leg as a non-taxable
home-fiat movement — but the adapter does not pre-decide that; it emits the full
two-leg event and lets the core rule (A4). The richer provenance chain
(`decision_id → order_id → trade_id`, `run_id`, `git_commit`, `fx_usdnok_at_fill`,
raw row) has no `events.csv` column and is currently only partially carried in
`notes` — see known gap 5 in §3.7.

### 7.3 Determinism & idempotency (per §4)

- `event_id` is `ledger:{run_id}:{trade_id}:{leg}` — re-importing this row emits
  byte-identical Events; a second import is a no-op.
- `source_row_index` comes from the stable sort `(exchange_ts, trade_id, leg)` —
  acquisition (leg 0) before fee (leg 1), reproducibly.
- No clock, no randomness, no network in the mapping.

### 7.4 Test (the first golden fixtures)

| fixture | owner | content |
|---|---|---|
| input ledger row | Trading | exists: `Trading/fixtures/trade_ledger/hp1_spot_buy.csv` (matches §7.1) |
| expected Events | Adapter | **not yet pinned** — the two §7.2 rows become `tests/fixtures/trade_ledger/…` when the mapper is built (the VARDE analogue is pinned: `tests/fixtures/varde/hp1_expected_events.csv`) |
| intake check | Taxes | the real `CanonicalEvent` accepts the shape — **proven for the VARDE pair** by `tests/test_events_conformance.py` (runs when Taxes is importable at its local path, else skips) |

Remaining gates for the `trade_ledger` path: the **transport** decision (hub
`GAPS.md` OPEN-3) and building the mapper. Build against real exported rows or
schema-faithful fixtures — never an imagined shape (GOTCHAS 11); re-verify when the
first live ledger lands.
