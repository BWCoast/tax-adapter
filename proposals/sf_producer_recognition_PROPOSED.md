# PROPOSED — Tax Adapter changes to recognize SovereignForge as a second producer

> **Status:** PROPOSED — not yet applied to `Documents/Tax adapter/`
> **Owner of decision:** Tax Adapter session (applies in its own repo)
> **Proposed by:** SovereignForge Norway producer seam (`claude/norway-producer-seam`)
> **Audit signoff:** Perplexity, 2026-06-14 — "Adapter must confirm SF's trade_ledger v3 passes its validation and document SF as a producer"
> **Authority:** This memo proposes; the Tax Adapter session decides. Per ECOSYSTEM.md §5 ownership rule, the Tax Adapter owns the producer→Event mapping.

---

## How to use this file

This is a **drafted proposal** for the Tax Adapter session to apply in its
own repository. Operator workflow:

1. Read each section below.
2. Apply each subsection's changes to the named target docs/files in
   `Documents/Tax adapter/`.
3. When applied, drop the `PROPOSED` qualifier on any references to this
   doc and remove the `blocks_first_push: yes` flag on the SovereignForge
   handoff §5 Priority 1.

The Taxes ADR-0001 addendum (companion proposal at
`docs/cross_session_proposals/taxes_adr_0001_addendum_sf_ofg_prefix.md`)
should land first or in parallel — it reserves the `sf:` / `sf:ofg:`
prefix that this memo references.

---

## 1. Register SovereignForge as a producer

### 1.1 `Documents/Tax adapter/SOURCES.md`

Add a new section after §3 (PM algo):

> **§3.5 — SovereignForge (Belgium-built bot, fork runs for the Norwegian operator)**
>
> **Repo path:** the operator's SovereignForge fork (path TBD by operator).
> Branch in scope: `claude/norway-producer-seam` (first pass).
>
> **Producer role:** SovereignForge runs an OFG-DCA (Operator Fib-Grid DCA)
> strategy on Bybit-EU USDC. Each fill is recorded into SovereignForge's
> existing DAC8 HMAC chain (`data/dac8_fills.jsonl`) for Belgian
> compliance reasons; for the Norwegian operator, an additional thin
> translator (`src/exports/trade_ledger_export.py`) reads that chain and
> emits canonical `trade_ledger` v3 CSV rows that this Adapter consumes.
>
> **Export contract:** trade_ledger v3 (Trading ADR-007), byte-faithful
> against `Documents/Trading/src/mm_collector/export/trade_ledger_csv.py`
> — same 30 columns, same `serialize`/`validate_row` semantics.
>
> **Producer identity in exported rows:** `account="sf_personal_main"`
> (operator-overridable), `strategy_id="ofg_dca"`, `book="accrual"` (OFG-DCA
> IS the accrual book per Trading ADR-006).
>
> **Reserved event_id prefix:** `sf:ofg:` (per Taxes ADR-0001 addendum).
>
> **Authority rule:** SovereignForge owns its own DAC8 chain shape (Belgian
> operator's contract); SovereignForge's trade_ledger export conforms to
> Trading's v3 contract read-only. SovereignForge does NOT own tax
> semantics — those remain in this Adapter and the Taxes core (LAWS A4).
>
> **Live-rows status:** SovereignForge's DAC8 chain exists today and
> contains real fills (Belgian operator). The Norwegian operator's fork
> can emit `trade_ledger` rows from this chain via the CLI immediately —
> independent of MM/Trading lab's HP-1 progression. SovereignForge is
> the second producer to come online for the Adapter.

### 1.2 `Documents/Tax adapter/alignment/ECOSYSTEM.md`

Add a row to §4's topology table (alongside MM/Trading lab, PM algo,
Arbitrage, VARDE):

```
| **SovereignForge** | <operator's fork path> | Producer. Belgium-built bot, fork runs for Norwegian operator. Emits canonical trade_ledger v3 rows via a thin translator over its existing DAC8 chain. Live and ready to consume. |
```

Update §4's ASCII topology diagram to include SovereignForge as a producer
line above or below the MM/Trading lab line — same arrow target (the
Adapter), same shape.

### 1.3 `Documents/Tax adapter/SCHEMAS.md` §3

Add a note at the top of §3 (or §3.1):

> The adapter recognizes the following producers as `trade_ledger` v3
> sources: **MM/Trading lab** (book=lab|accrual), **SovereignForge**
> (book=accrual, strategy_id=ofg_dca), and any future producer that
> conforms to the v3 contract byte-for-byte. PM algo conforms to its
> own §3.4 export contract, not trade_ledger.

---

## 2. Validation contract test (SovereignForge ↔ Adapter)

Add a pact-style golden fixture under
`Documents/Tax adapter/tests/integration/fixtures/sf_producer/`:

```
fixtures/sf_producer/
├── hp_sf_001_xrp_buy.csv          # one synthetic SF row, byte-faithful to v3
├── hp_sf_001_expected_events.json # expected canonical Events the adapter emits
└── README.md                       # what the fixture proves
```

**`hp_sf_001_xrp_buy.csv`** is a single XRP/USDC buy emitted by
SovereignForge in NO mode with Norges Bank FX populated. The fixture is
literally the output of running `python scripts/export_trade_ledger.py
--jurisdiction NO` against a known synthetic DAC8 fill (the test in
SovereignForge's `tests/exports/test_trade_ledger_export.py
::test_validate_row_passes_no_row_with_fx` produces exactly this row).

The Adapter test confirms two things:

1. **Validation pass** — `validate_row(parsed_csv_row)` returns `[]` (no
   reasons). This is the structural contract.
2. **Mapping output** — the Adapter's `map_fill_to_event(row)` produces
   exactly the canonical Event(s) in `hp_sf_001_expected_events.json`,
   byte-identical via the existing golden-fixture protocol.

Future SovereignForge contributions land additional fixtures alongside
(`hp_sf_002_xrp_sell.csv`, etc.) following the same pattern.

---

## 3. fill_kind soft REQUIRES_REVIEW recognition

SovereignForge cannot capture maker vs taker per fill. It emits
`fill_kind="taker"` with the counted reason
`fill_kind_defaulted_to_taker_sf_does_not_capture`.

**Adapter change** (per Perplexity audit Priority 3): in the mapping
function, when the source row carries this exact counted-reason string in
its companion reasons list (or when the row passes through
`validate_row` clean but originates from a producer with this known
limitation), surface a **soft `REQUIRES_REVIEW` flag** on the emitted
Event — DO NOT block ingestion and DO NOT mark the entire fill as
`REQUIRES_REVIEW`.

**Concrete shape:**

- The emitted Event's `provenance` dict carries `fill_kind_resolution: "defaulted_taker_producer_does_not_capture"`.
- The emitted Event's `event_type` is the normal classification (`ACQUISITION`,
  `DISPOSAL`, `SWAP`, `FEE` per §3.1).
- The Tax core can decide whether to escalate to a hard
  `REQUIRES_REVIEW` later if maker/taker distinction matters for the
  jurisdiction's fee classification. By default it's informational.

**Where this lives:** new branch in the mapping table at SCHEMAS.md §3.1
"Spot fills" — a note column or footnote referencing this proposal.

If a later SovereignForge wave adds maker/taker capture to FillRecord,
SF drops the counted reason and the Adapter treats those rows as fully
resolved (no provenance soft-flag).

---

## 4. recv_ts == exchange_ts acceptance

SovereignForge doesn't track a distinct `recv_ts` separately from
`exchange_ts`. It emits both columns equal (and notes the equality in
provenance — see SF handoff §3 row 26).

**Adapter change** (per Perplexity audit RESOLVED row): accept
`recv_ts == exchange_ts` from SovereignForge as "no extra latency info
available." Do NOT mark as UNRESOLVED. Do NOT use the equality as a
signal of producer error.

**Where this lives:** a clarifying note in SCHEMAS.md §3.1 or a footnote
to the canonical column-shape table. No structural code change required
— `validate_row` already passes equal timestamps because neither column
is empty.

---

## 5. FX provenance: `derived_at_export` treatment

SovereignForge populates `fx_rate` / `fx_source` / `fx_as_of_ts` for NO
operator fills by looking up the Norges Bank EOD rate at export time
(provenance label `"derived_at_export"`). This is not fill-time captured.

**Adapter change** (per Perplexity audit Priority 4): for now, treat
`fx_source="norgesbank.eod"` with provenance label `"derived_at_export"`
as **tier-1 valuation** (above the Taxes ADR-0010 warned fallback), but
attach an audit note in the Event's `provenance` field:

```
provenance.fx_resolution: "derived_at_export_norgesbank_eod_pending_fill_time_upgrade"
```

This is honest — the auditor sees that the FX was looked up by date
rather than captured at fill — but it doesn't downgrade the valuation
tier prematurely. When SovereignForge ships fill-time NOK capture (a
future wave; see SF handoff §5 Priority 7), the provenance label flips
to `"fill_time"` and the audit note drops.

**If the Taxes core decides this should be the ADR-0010 warned fallback
instead**, the Adapter updates this rule in one place. Either way, the
classification is OWNED by Taxes (ADR-0006/0010), not SovereignForge.

---

## 6. Where these changes land (file checklist)

| File | Change | Section |
|---|---|---|
| `Documents/Tax adapter/SOURCES.md` | Add §3.5 SovereignForge producer block | §1.1 above |
| `Documents/Tax adapter/alignment/ECOSYSTEM.md` | Add SF row to §4 topology + ASCII diagram | §1.2 above |
| `Documents/Tax adapter/SCHEMAS.md` | Note SF as a v3 producer in §3 + footnotes for fill_kind / recv_ts handling | §1.3, §3, §4 above |
| `Documents/Tax adapter/tests/integration/fixtures/sf_producer/` | Add HP-SF-001 golden fixture | §2 above |
| `Documents/Tax adapter/decisions/` (new ADR) | `ADR-00X-sf-producer-fill-semantics.md` capturing the fill_kind + FX rulings | §3, §5 above |

---

## 7. What does NOT need to change

- **Adapter's existing `ledger:` event_id prefix reservation** — unchanged.
  SF's `sf:ofg:` reservation is at the producer-identity layer, not the
  Adapter-output layer. The Adapter can continue to use
  `ledger:{run_id}:{trade_id}:{leg}` as today; SF's `decision_id` flows
  into `provenance` as one of the upstream IDs.
- **Adapter LAWS A1–A10** — no changes. SF conforms to all of them as a
  producer-on-the-other-side-of-the-boundary.
- **Adapter mapping spec for derivative fills / book transfers** — no
  changes. SF is spot-only OFG-DCA; if SF later adds derivatives, those
  become new fixture additions, not contract changes.

---

## 8. Test plan (after applying)

1. Apply §1 documentation updates.
2. Add §2 golden fixture from a real SovereignForge export.
3. Run the existing Adapter golden-fixture test suite — SF fixture
   should pass.
4. Confirm `validate_row` returns `[]` for the SF fixture row.
5. Confirm the emitted Event(s) match the expected JSON byte-faithfully.
6. Update the Adapter's PROGRESS.md / HANDOFF.md to mark "SF as second
   producer" OPEN item as resolved.

---

## 9. Open question to the Tax Adapter session

Perplexity's audit closed with: *"Is there any part of the Adapter side
you'd like me to sketch next (e.g., the Event-mapping for SF rows or the
pact/contract tests you'll want between SF and the Adapter)?"*

The operator should decide whether to ask Perplexity to sketch:

(a) the SF-row → canonical Event mapping table specifically (§3.1
expansion), OR

(b) the contract/pact test scaffolding for the SF↔Adapter boundary
(§2 expansion with a CI integration sketch).

Either is a productive next step. This memo is the "what changes"; (a)
or (b) would be the "how exactly."

---

## Related

- Taxes ADR-0001 addendum (companion proposal):
  `docs/cross_session_proposals/taxes_adr_0001_addendum_sf_ofg_prefix.md`
- SovereignForge handoff doc:
  `docs/norway_producer_seam_handoff.md`
- Adapter ECOSYSTEM.md §5 (ownership) + §8 (OPEN-item protocol)
- Trading ADR-007 (trade_ledger v3 transport)
