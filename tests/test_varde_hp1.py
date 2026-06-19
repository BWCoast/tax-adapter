from decimal import Decimal
from pathlib import Path

from tax_adapter.producers.varde import read_varde_fills, map_varde_fills

FIX = Path(__file__).parent / "fixtures" / "varde" / "hp1_nok_spot_buy.csv"


def _events():
    return map_varde_fills(read_varde_fills(FIX))


def test_hp1_emits_two_events_trade_then_fee():
    evs = _events()
    assert [e.event_type for e in evs] == ["TRADE", "FEE"]


def test_hp1_trade_leg_is_correct():
    trade = _events()[0]
    assert trade.event_id == "varde:varde-run-2026-03-02:varde-1:0"
    assert trade.source_id == "varde-fills:lab"
    assert trade.source_row_index == 0
    assert trade.asset_out == "NOK"
    assert trade.quantity_out == Decimal("30000.00000000")   # qty x price
    assert trade.asset_in == "BTC"
    assert trade.quantity_in == Decimal("0.05000000")
    assert trade.nok_value_out == Decimal("30000.00")
    assert trade.nok_value_in == Decimal("30000.00")
    assert trade.parser == "varde_adapter"
    assert trade.source_ref == "varde-fills.csv#varde-1"


def test_hp1_fee_leg_is_correct():
    fee = _events()[1]
    assert fee.event_id == "varde:varde-run-2026-03-02:varde-1:1"
    assert fee.source_row_index == 1
    assert fee.fee_asset == "NOK"
    assert fee.fee_quantity == Decimal("150.00000000")
    assert fee.nok_value_out == Decimal("150.00")
    assert fee.asset_out is None and fee.asset_in is None      # standalone FEE


def test_hp1_notes_is_present_but_non_canonical():
    # notes is write-only overflow; we assert it EXISTS, never parse it for logic.
    assert _events()[0].notes  # non-empty string


def test_hp1_sell_and_stablecoin_not_implemented_in_v1():
    import pytest
    rows = read_varde_fills(FIX)
    sell = dict(rows[0]); sell["side"] = "sell"
    with pytest.raises(NotImplementedError):
        map_varde_fills([sell])
    usdt = dict(rows[0]); usdt["quote"] = "USDT"; usdt["symbol"] = "BTC/USDT"
    with pytest.raises(NotImplementedError):
        map_varde_fills([usdt])


def test_hp1_output_byte_matches_frozen_golden(tmp_path):
    from tax_adapter.events import write_events_csv
    out = tmp_path / "events.csv"
    write_events_csv(_events(), out)
    expected = (FIX.parent / "hp1_expected_events.csv").read_text(encoding="utf-8")
    assert out.read_text(encoding="utf-8") == expected


def test_multi_row_source_row_index_increments_and_ids_distinct():
    rows = read_varde_fills(FIX)
    r0 = dict(rows[0])
    r1 = dict(rows[0]); r1["trade_id"] = "varde-2"
    evs = map_varde_fills([r0, r1])
    assert [e.event_type for e in evs] == ["TRADE", "FEE", "TRADE", "FEE"]
    assert [e.source_row_index for e in evs] == [0, 1, 2, 3]
    ids = [e.event_id for e in evs]
    assert len(set(ids)) == 4                      # all event_ids distinct
    assert ids[0] == "varde:varde-run-2026-03-02:varde-1:0"
    assert ids[2] == "varde:varde-run-2026-03-02:varde-2:0"
