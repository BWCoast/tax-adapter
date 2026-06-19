from tax_adapter.events import EVENTS_COLUMNS

# The frozen 20-column events.csv contract (Taxes ADR-0001 / CONTRACTS.md Seam B).
CANONICAL_20 = [
    "event_id", "timestamp", "event_type", "source_id", "source_row_index",
    "asset_out", "quantity_out", "asset_in", "quantity_in",
    "fee_asset", "fee_quantity", "income_subtype", "label", "notes",
    "nok_value_out", "nok_value_in",
    "parser", "parser_version", "source_type", "source_ref",
]


def test_events_columns_match_canonical_contract():
    assert EVENTS_COLUMNS == CANONICAL_20
    assert len(EVENTS_COLUMNS) == 20
