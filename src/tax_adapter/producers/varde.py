"""VARDE producer mapping: varde-fills.csv -> canonical Event list (SCHEMAS.md §3.7).

v1 implements the NOK-quoted spot BUY (HP-1). Sell / stablecoin-quoted / XRPL
transfers are documented in SCHEMAS §3.7 but raise NotImplementedError here — the
adapter never guesses an unmapped shape (A3).
"""
from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from tax_adapter.events import Event

_PARSER = "varde_adapter"
_PARSER_VERSION = "varde/1->event/1"
_SOURCE_TYPE = "varde-fills"
_Q8 = Decimal("1.00000000")   # 8 dp for quantities
_Q2 = Decimal("1.00")         # 2 dp for NOK values
_FIAT = frozenset({"NOK"})    # home fiat (quote needs no FX for nok_value)


def read_varde_fills(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _ts(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _provenance(row: dict) -> dict[str, str]:
    return dict(parser=_PARSER, parser_version=_PARSER_VERSION,
                source_type=_SOURCE_TYPE, source_ref=f"varde-fills.csv#{row['trade_id']}")


def _notes(row: dict) -> str:
    # WRITE-ONLY overflow metadata. Flat, human-readable. NEVER a parsing surface.
    return (f"venue={row['venue']};strategy_id={row['strategy_id']};"
            f"mode={row['mode']};book={row['book']};fill_kind={row['fill_kind']}")


def _map_row(row: dict, start_index: int) -> list[Event]:
    if row["product_type"] != "spot":
        raise NotImplementedError(f"v1: non-spot product_type {row['product_type']!r}")
    quote = row["quote"]
    if row["side"] != "buy" or quote not in _FIAT:
        # sell, stablecoin-quoted (TRADE w/ FX), and transfers are slice-2 work.
        raise NotImplementedError(
            f"v1 maps only NOK-quoted spot buys; got side={row['side']!r} quote={quote!r}")

    ts = _ts(row["exchange_ts"])
    base = row["base"]
    qty = Decimal(row["qty"])
    price = Decimal(row["price"])
    fee = Decimal(row["fee"])
    # Derived values are quantized to the canonical scale (8 dp for quantities, 2 dp
    # for NOK values) using the Decimal context default (ROUND_HALF_EVEN). Verbatim
    # source values that already arrive as decimal strings (e.g. quantity_in = qty,
    # fee_quantity = fee) are passed through unrounded to preserve producer precision.
    notional = (qty * price)
    run_id, trade_id, book = row["run_id"], row["trade_id"], row["book"]
    source_id = f"varde-fills:{book}"
    prov = _provenance(row)
    notes = _notes(row)

    def eid(leg: int) -> str:
        return f"varde:{run_id}:{trade_id}:{leg}"

    trade = Event(
        event_id=eid(0), timestamp=ts, event_type="TRADE",
        source_id=source_id, source_row_index=start_index,
        asset_out=quote, quantity_out=notional.quantize(_Q8),
        asset_in=base, quantity_in=qty,
        nok_value_out=notional.quantize(_Q2), nok_value_in=notional.quantize(_Q2),
        notes=notes, **prov,
    )
    fee_event = Event(
        event_id=eid(1), timestamp=ts, event_type="FEE",
        source_id=source_id, source_row_index=start_index + 1,
        fee_asset=row["fee_asset"], fee_quantity=fee,
        nok_value_out=fee.quantize(_Q2),
        notes=notes, **prov,
    )
    return [trade, fee_event]


def map_varde_fills(rows: list[dict]) -> list[Event]:
    # source_row_index is a running counter over emitted events, so multiple fills
    # do not collide (HP-1's single row still yields indices 0, 1). Canonical
    # (exchange_ts, trade_id, leg) sorting is slice-2 work; v1 preserves input order.
    out: list[Event] = []
    for row in rows:
        out.extend(_map_row(row, len(out)))
    return out
