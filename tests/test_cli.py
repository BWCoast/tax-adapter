from pathlib import Path

from tax_adapter.cli import main

FIX = Path(__file__).parent / "fixtures" / "varde" / "hp1_nok_spot_buy.csv"


def test_cli_maps_varde_fills_to_events(tmp_path):
    out = tmp_path / "events.csv"
    rc = main(["--producer", "varde", "--in", str(FIX), "--out", str(out)])
    assert rc == 0
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("event_id,timestamp,event_type")
    assert len(lines) == 3                       # header + TRADE + FEE
    assert ",TRADE," in lines[1] and ",FEE," in lines[2]


def test_cli_rejects_unknown_producer(tmp_path):
    import pytest
    with pytest.raises(SystemExit):
        main(["--producer", "nope", "--in", str(FIX), "--out", str(tmp_path / "x.csv")])
