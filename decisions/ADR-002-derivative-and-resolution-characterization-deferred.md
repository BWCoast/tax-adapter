# ADR-002 — Derivative & prediction-market realized PnL: emit faithfully, defer characterization

Date: 2026-06-14 · Status: accepted (policy; revisited when the tax core gains
an explicit derivative/contract rule)

## Context
Spot fills map cleanly to ACQUISITION / DISPOSAL / SWAP because they transfer
asset ownership. Two important classes do not:

1. **Derivative fills** (linear/inverse perps from the lab). A perp open/close
   transfers no underlying; the tax-relevant facts are *realized PnL* (in the
   settle asset) and *funding* (periodic carry). Whether realized derivative
   PnL is taxed as a capital gain, as income, per-fill or netted per-period,
   is jurisdiction-specific (Norway vs UK diverge — Taxes ADR-0020) and not yet
   encoded in the tax core's classification.
2. **Prediction-market resolutions** (PM algo). A binary-contract payout is
   realized PnL, not a fungible-asset transfer; its characterization is
   similarly jurisdiction-specific and unsettled.

The adapter must not invent a tax characterization for these (law A4), but it
also must not drop them.

## Decision
The adapter **emits a faithful, typed economic event with full provenance** and
**defers the tax characterization to the tax core**:

- Derivative close/liquidation/settlement fills → one realized-PnL event in the
  settle asset, sign from `realized_pnl_quote`, full `decision_id` provenance.
- Derivative opening fills (no realized PnL) → no tax event (position change
  only); optional provenance row.
- Funding → INCOME (received) or FEE (paid) by sign.
- Prediction-market resolutions/payouts → realized-PnL/INCOME event in quote.

Until the `Taxes` core publishes an explicit rule for derivative / contract
realized PnL, these events MAY be routed as `REQUIRES_REVIEW` (law A3) so the
user/tax core makes the call — never a silent capital-vs-income guess in the
adapter.

## Why defer rather than decide
- Characterization is tax law, jurisdiction-specific, and belongs in the
  deterministic core where it can be tested and audited (Taxes Rule 1, A4).
- Emitting the faithful economic event now keeps the data complete and
  provenance intact; the core (or an override, Taxes ADR-0019) can classify it
  later without re-translation.
- A wrong characterization baked into the adapter would be invisible in clean-
  looking output and hard to unwind across a filing — exactly the A2/A3 hazard.

## Trigger to revisit
When the `Taxes` core adds a derivative/contract realized-PnL classification
(a new Taxes ADR), update SCHEMAS.md §3.2/§3.4 to map directly to the settled
type and drop the `REQUIRES_REVIEW` fallback for the covered cases.

## Related
SCHEMAS.md §3.2 (derivatives), §3.4 (prediction market); laws A3, A4; Taxes
ADR-0011 (income classification mapping), ADR-0020 (multi-jurisdiction).
