"""Optional: validate emitted events against the REAL Taxes CanonicalEvent.

Skipped unless the Taxes package is importable locally. This is a truth-check, not
a build dependency -- the adapter's contract is the events.csv columns, not the
Taxes Python class.

Verified against the real signatures:
  - tax_core.models.asset.AssetIdentity(symbol, contract_address=None, ...):
    `symbol` is the first positional field, so AssetIdentity(sym) is correct for
    bare fiat/native symbols (NOK, BTC).
  - tax_core.models.event.CanonicalEvent: required positional-ish fields are
    event_id, timestamp, event_type, source_id, source_row_index; all bilateral,
    fee, income_subtype, label, notes, and provenance fields carry defaults.
    provenance is a dict[str, str] whose four keys (parser/parser_version/
    source_type/source_ref) must be non-empty. Construction enforces the same
    per-type shape rules the adapter's Event mirrors, so HP-1's TRADE + FEE
    construct cleanly.
"""
import sys
from pathlib import Path

import pytest

_TAXES_SRC = Path(r"C:\Users\mrkro\Documents\Taxes\src")
if _TAXES_SRC.is_dir() and str(_TAXES_SRC) not in sys.path:
    sys.path.insert(0, str(_TAXES_SRC))

CanonicalEvent = None
AssetIdentity = None
try:
    from tax_core.models.event import CanonicalEvent  # type: ignore
    from tax_core.models.asset import AssetIdentity   # type: ignore
except Exception:  # noqa: BLE001 - any import failure => skip
    pass

pytestmark = pytest.mark.skipif(
    CanonicalEvent is None or AssetIdentity is None,
    reason="Taxes package not importable locally; conformance check skipped",
)

from tax_adapter.producers.varde import read_varde_fills, map_varde_fills  # noqa: E402

FIX = Path(__file__).parent / "fixtures" / "varde" / "hp1_nok_spot_buy.csv"


def _asset(sym):
    # AssetIdentity's first field is `symbol`; bare fiat/native symbols need no
    # contract_address (qualified_key falls back to the bare symbol).
    return AssetIdentity(sym) if sym is not None else None


def test_emitted_events_construct_real_canonical_event():
    events = list(map_varde_fills(read_varde_fills(FIX)))
    # HP-1 emits exactly two events: the TRADE leg and the standalone FEE leg.
    assert [e.event_type for e in events] == ["TRADE", "FEE"]
    for e in events:
        CanonicalEvent(
            event_id=e.event_id, timestamp=e.timestamp, event_type=e.event_type,
            source_id=e.source_id, source_row_index=e.source_row_index,
            asset_out=_asset(e.asset_out), quantity_out=e.quantity_out,
            asset_in=_asset(e.asset_in), quantity_in=e.quantity_in,
            fee_asset=_asset(e.fee_asset), fee_quantity=e.fee_quantity,
            nok_value_out=e.nok_value_out, nok_value_in=e.nok_value_in,
            provenance={k: getattr(e, k) for k in
                        ("parser", "parser_version", "source_type", "source_ref")},
        )
