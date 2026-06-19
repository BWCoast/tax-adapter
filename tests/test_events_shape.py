from datetime import datetime, timezone
from decimal import Decimal

import pytest

from tax_adapter.events import Event, EventShapeError, EVENTS_COLUMNS


def _prov():
    return dict(parser="varde_adapter", parser_version="varde/1->event/1",
                source_type="varde-fills", source_ref="varde-fills.csv#varde-1")


def _ts():
    return datetime(2026, 3, 2, 10, 15, 30, tzinfo=timezone.utc)


def _trade(**kw):
    base = dict(
        event_id="varde:r:t:0", timestamp=_ts(), event_type="TRADE",
        source_id="varde-fills:lab", source_row_index=0,
        asset_out="NOK", quantity_out=Decimal("30000.00000000"),
        asset_in="BTC", quantity_in=Decimal("0.05000000"),
        **_prov(),
    )
    base.update(kw)
    return Event(**base)


def test_valid_trade_constructs():
    e = _trade()
    assert e.event_type == "TRADE"


def test_valid_fee_constructs():
    e = Event(event_id="varde:r:t:1", timestamp=_ts(), event_type="FEE",
              source_id="varde-fills:lab", source_row_index=1,
              fee_asset="NOK", fee_quantity=Decimal("150.00000000"), **_prov())
    assert e.event_type == "FEE"


def test_unknown_event_type_rejected():
    with pytest.raises(EventShapeError):
        _trade(event_type="ACQUISITION")          # not in the enum — the §7 stale shape


def test_trade_requires_both_legs():
    with pytest.raises(EventShapeError):
        _trade(asset_in=None, quantity_in=None)   # one-sided TRADE is invalid


def test_fee_must_not_set_legs():
    with pytest.raises(EventShapeError):
        Event(event_id="x", timestamp=_ts(), event_type="FEE",
              source_id="s", source_row_index=0,
              fee_asset="NOK", fee_quantity=Decimal("1"),
              asset_out="NOK", quantity_out=Decimal("1"), **_prov())


def test_negative_quantity_rejected():
    with pytest.raises(EventShapeError):
        _trade(quantity_out=Decimal("-1"))


def test_missing_provenance_rejected():
    with pytest.raises(EventShapeError):
        _trade(parser="")


def test_naive_timestamp_rejected():
    with pytest.raises(EventShapeError):
        _trade(timestamp=datetime(2026, 3, 2, 10, 15, 30))  # no tzinfo


def test_to_row_has_all_columns_and_serializes():
    row = _trade().to_row()
    assert list(row.keys()) == EVENTS_COLUMNS
    assert row["quantity_out"] == "30000.00000000"
    assert row["asset_in"] == "BTC"
    assert row["quantity_in"] == "0.05000000"
    assert row["timestamp"] == "2026-03-02T10:15:30Z"   # UTC -> Z
    assert row["income_subtype"] == ""                   # None -> ""


def test_transfer_out_with_half_populated_in_leg_rejected():
    with pytest.raises(EventShapeError):
        Event(event_id="x", timestamp=_ts(), event_type="TRANSFER_OUT",
              source_id="s", source_row_index=0,
              asset_out="BTC", quantity_out=Decimal("0.05"),
              asset_in="NOK", quantity_in=None, **_prov())  # half-populated in-side


def test_income_with_half_populated_out_leg_rejected():
    with pytest.raises(EventShapeError):
        Event(event_id="x", timestamp=_ts(), event_type="INCOME",
              source_id="s", source_row_index=0,
              asset_in="BTC", quantity_in=Decimal("0.05"),
              asset_out="NOK", quantity_out=None, **_prov())  # half-populated out-side


def test_fee_with_half_populated_leg_rejected():
    with pytest.raises(EventShapeError):
        Event(event_id="x", timestamp=_ts(), event_type="FEE",
              source_id="s", source_row_index=0,
              fee_asset="NOK", fee_quantity=Decimal("1"),
              asset_out="NOK", quantity_out=None, **_prov())  # half-populated out leg on FEE


def test_valid_transfer_out_constructs():
    e = Event(event_id="x", timestamp=_ts(), event_type="TRANSFER_OUT",
              source_id="s", source_row_index=0,
              asset_out="BTC", quantity_out=Decimal("0.05"), **_prov())
    assert e.event_type == "TRANSFER_OUT"


def test_valid_income_with_subtype_constructs():
    e = Event(event_id="x", timestamp=_ts(), event_type="INCOME",
              source_id="s", source_row_index=0,
              asset_in="BTC", quantity_in=Decimal("0.05"),
              income_subtype="staking", **_prov())
    assert e.income_subtype == "staking"


def test_requires_review_is_unconstrained():
    e = Event(event_id="x", timestamp=_ts(), event_type="REQUIRES_REVIEW",
              source_id="s", source_row_index=0, **_prov())
    assert e.event_type == "REQUIRES_REVIEW"


def test_write_events_csv_round_trips(tmp_path):
    import csv as _csv
    from tax_adapter.events import write_events_csv
    out = tmp_path / "events.csv"
    write_events_csv([_trade()], out)
    with open(out, newline="", encoding="utf-8") as f:
        rows = list(_csv.DictReader(f))
    assert list(rows[0].keys()) == EVENTS_COLUMNS
    assert len(rows) == 1
    assert rows[0]["event_type"] == "TRADE"
    assert rows[0]["quantity_out"] == "30000.00000000"


def test_non_utc_timestamp_serializes_as_utc_z():
    from datetime import timedelta, timezone as _tz
    tz = _tz(timedelta(hours=2))
    e = _trade(timestamp=datetime(2026, 3, 2, 10, 15, 30, tzinfo=tz))
    assert e.to_row()["timestamp"] == "2026-03-02T08:15:30Z"
