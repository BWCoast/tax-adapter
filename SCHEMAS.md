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
