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
