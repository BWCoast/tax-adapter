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

---

## 1. Downstream target — canonical tax Event (Taxes ADR-0001)

Every emitted row MUST carry:

| field | req | notes |
|---|---|---|
| `event_id` | R | stable across re-imports, deterministic from source (A5). Format reserved here: `ledger:{run_id}:{trade_id}:{leg}` — verified NOT to collide with Taxes reserved prefixes (`inflow_group:`, `xrpl:`, `csv:`) per ADR-0001 addendum |
| `timestamp` | R | ISO-8601 + tz; from ledger `exchange_ts` (UTC), reported Europe/Oslo downstream |
| `event_type` | R | one of DISPOSAL, ACQUISITION, INCOME, FEE, TRANSFER_IN, TRANSFER_OUT, SWAP, REQUIRES_REVIEW |
| `asset` | R | qualified key (Taxes ADR-0021): `XRP`/`BTC` native, `USDC.0x…` ERC-20, `USD.rIssuer` XRPL IOU, `NFT:…` |
| `quantity` | R | `Decimal`, always positive (A7) |
| `nok_value` | R/None | `None` = UNRESOLVED, NEVER fabricated (A2). The adapter passes through `fx_usdnok_at_fill` where the ledger captured it; it does not invent FX |
| `source_id` | R | e.g. `trade_ledger:lab`, `trade_ledger:accrual`, `pm-algo:kalshi`, `csv:firi_2025.csv` |
| `source_row_index` | R | deterministic tie-breaker — preserves FIFO ordering (Taxes ADR-0002) |
| `provenance` | R | parser/adapter version, raw `decision_id`, `order_id`, `trade_id`, `experiment_hash`, `git_commit`, original ledger row |

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

A spot trade is two legs. The adapter emits per leg by what the quote asset is:

| ledger row | quote asset | emitted events |
|---|---|---|
| `side=buy` | fiat (NOK/EUR) | `ACQUISITION` of base |
| `side=buy` | crypto/stablecoin | `SWAP` (disposal of quote + acquisition of base) — Norwegian tax treats stablecoin→crypto as a disposal |
| `side=sell` | fiat | `DISPOSAL` of base |
| `side=sell` | crypto/stablecoin | `SWAP` (disposal of base + acquisition of quote) |
| any | — | `FEE` event for `fee`/`fee_asset` when fee > 0 |

`book=accrual` spot buys (DCA/conviction, Trading ADR-006) map identically —
the adapter does not special-case books for *type*; `book` is carried into
`source_id`/provenance so downstream can separate lab vs accrual lots cleanly.

#### Worked example: HP-SF-001 — OFG XRP/USDC buy (NO, live, FX populated)

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
separate ACQUISITION per §3.1.

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

## 4. Determinism & idempotency (A5)

- `event_id` is a pure function of upstream identifiers (`run_id`, `trade_id`,
  `leg`) — re-importing the same ledger produces byte-identical events.
- `source_row_index` is assigned by a stable sort of upstream rows
  (`(exchange_ts, trade_id, leg)`) so FIFO ordering downstream is reproducible
  (Taxes ADR-0002).
- The mapping has no clock, no randomness, no network call. Same input → same
  events, always (mirrors Taxes deterministic-core principle).

## 5. Validation (what the adapter refuses)

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

The first path to be wired end-to-end (ADR-003): **MM Strategy Bot / Trading
lab → adapter → Taxes intake**, deliberately the simplest scenario — one vanilla
**fiat-quoted spot buy**, one venue, `book=lab`, no derivative, no swap, no
transfer. It is the only fully one-sided spot case (§3.1 row 1): a single
`ACQUISITION` plus a `FEE`, no SWAP disposal leg, and — because the quote is NOK
— no FX tier needed for `nok_value`. This worked example is the contract the
first golden fixture is pinned against.

> Later happy paths extend this spine, not replace it: **HP-2** adds a
> stablecoin-quoted buy (a two-leg SWAP, §3.1); **HP-3** adds a derivative
> realized-PnL fill (§3.2, characterization per ADR-002). Spot-only first.

### 7.1 Input — one `trade_ledger` row (the only consumed fields shown)

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

Per §3.1 (fiat-quoted buy → `ACQUISITION` of base; plus a `FEE` leg for the
non-zero fee). `nok_value` for the acquisition is the NOK notional `qty × price`
(quote already NOK, no FX applied); the fee is already NOK. The adapter performs
no tax math — only the quote-currency notional and a verbatim fee pass-through.

**Event 0 — ACQUISITION**
```
event_id:          ledger:run_2026_03_02_001:trd_a12b:0
timestamp:         2026-03-02T10:15:30Z            # from exchange_ts (UTC); reported Europe/Oslo downstream
event_type:        ACQUISITION
asset:             BTC
quantity:          0.05000000                       # Decimal, positive
nok_value:         30000.00                          # 0.05 × 600000, quote=NOK
source_id:         trade_ledger:lab
source_row_index:  0                                 # stable sort key (exchange_ts, trade_id, leg)
provenance:        {adapter_schema_version, decision_id: dec_77c0, order_id: ord_8f31,
                    trade_id: trd_a12b, strategy_id: mm_v1, experiment_hash, book: lab,
                    mode: live, run_id: run_2026_03_02_001, git_commit: a1b2c3d,
                    fx_usdnok_at_fill: {rate, source, as_of_ts}, raw_row: {…}}
```

**Event 1 — FEE**
```
event_id:          ledger:run_2026_03_02_001:trd_a12b:1
timestamp:         2026-03-02T10:15:30Z
event_type:        FEE
asset:             NOK
quantity:          150.00                            # Decimal, positive
nok_value:         150.00                            # fee already in NOK
source_id:         trade_ledger:lab
source_row_index:  1
provenance:        {… same chain as Event 0, leg: 1 …}
```

No NOK disposal event is emitted: NOK is home fiat, not a taxable asset disposal
in Norway — which is exactly why a fiat-quoted buy is one-sided (contrast the
stablecoin-quoted SWAP of §3.1 / HP-2).

### 7.3 Determinism & idempotency (per §4)

- `event_id` is `ledger:{run_id}:{trade_id}:{leg}` — re-importing this row emits
  byte-identical Events; a second import is a no-op.
- `source_row_index` comes from the stable sort `(exchange_ts, trade_id, leg)` —
  acquisition (leg 0) before fee (leg 1), reproducibly.
- No clock, no randomness, no network in the mapping.

### 7.4 Test (the first golden fixtures)

| fixture | owner | content |
|---|---|---|
| input ledger row | Trading (schema-faithful until live) | the §7.1 row, byte-pinned |
| expected Events | Adapter | the two §7.2 rows, byte-pinned |
| intake check | Taxes | `Taxes/` ingests the two rows without error (20-column `events.csv`) |

Gate to run it for real: the **`trade_ledger` → adapter transport** decision
(§3 SOURCES / PROGRESS open item 2) and the first live (or schema-faithful) lab
row. Build against real exported rows or schema-faithful fixtures — never an
imagined shape (GOTCHAS 11); re-verify when the first live ledger lands.
