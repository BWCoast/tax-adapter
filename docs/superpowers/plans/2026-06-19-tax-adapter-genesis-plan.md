# Tax Adapter Genesis — Implementation Plan (v1: VARDE HP-1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax. Design: `docs/superpowers/specs/2026-06-19-tax-adapter-genesis-design.md`.

**Goal:** Bootstrap the Tax Adapter's first code — map one VARDE `varde-fills.csv` row into the correct canonical `events.csv` rows (TRADE + FEE), validated against `event.py`'s shape rules and pinned by a golden HP-1 fixture.

**Architecture:** A tiny `uv` package. Producer facts → an internal frozen `Event` dataclass that mirrors the frozen 20-column `events.csv` contract AND replicates `event.py`'s construction-time invariants (fail-fast) → serialize to `events.csv`. No runtime import of the Taxes package (the seam is the CSV contract); an optional skip-if-unavailable conformance test proves CSV-compliance against the real `CanonicalEvent` when Taxes is present locally.

**Tech Stack:** Python 3.11+, stdlib + `Decimal` only, pytest, uv. Test runner: **`uv run pytest`** from the adapter repo root (`C:\Users\mrkro\Documents\Tax adapter`).

**No commits** unless the operator explicitly asks — leave the working tree changed.

---

## Binding rules (do not violate)

- **Facts → typed events → CSV. No tax math.** No FIFO, valuation, FX fetching, or characterization (A4/A9). The adapter never invents FX (A2): missing FX → `None`/UNRESOLVED, never fabricated.
- **`notes` is WRITE-ONLY metadata for v1** — a human-readable provenance overflow string. **No downstream logic may parse structured content from `notes`.** The four provenance keys (`parser`, `parser_version`, `source_type`, `source_ref`) are the only first-class provenance columns. If richer provenance becomes operationally needed it graduates to formal columns / a documented adjunct schema in a later slice — it must not stay a semi-structured parsing surface.
- **v1 scope is the NOK-quoted spot BUY only** (HP-1). Sell, USDC/USDT-quoted, and XRPL transfers are documented in SCHEMAS §3.7 but the v1 mapper raises a clear `NotImplementedError` for them — never a guess.
- **Decimal only**, quantities ≥ 0, sign in the type.

---

## File Map

| Action | Path | Task |
|--------|------|------|
| Create | `pyproject.toml` | 1 |
| Create | `src/tax_adapter/__init__.py` | 1 |
| Create | `tests/__init__.py` | 1 |
| Create | `tests/fixtures/varde/hp1_nok_spot_buy.csv` (vendored copy of VARDE's HP-1) | 1 |
| Create | `src/tax_adapter/events.py` | 2 |
| Create | `tests/test_events_shape.py` | 2 |
| Create | `src/tax_adapter/producers/__init__.py` | 3 |
| Create | `src/tax_adapter/producers/varde.py` | 3 |
| Create | `tests/test_varde_hp1.py` | 3 |
| Create | `tests/fixtures/varde/hp1_expected_events.csv` (generated then frozen) | 3 |
| Create | `src/tax_adapter/cli.py` | 4 |
| Create | `tests/test_cli.py` | 4 |
| Create | `tests/test_events_conformance.py` | 5 |
| Create | `tests/test_events_columns.py` (drift guard) | 5 |

---

## Task 1: Scaffold

**Files:** `pyproject.toml`, `src/tax_adapter/__init__.py`, `tests/__init__.py`, `tests/fixtures/varde/hp1_nok_spot_buy.csv`

- [ ] **Step 1: `pyproject.toml`** (non-package project so uv won't try to build/install; `src` on the pytest path)

```toml
[project]
name = "tax-adapter"
version = "0.1.0"
description = "Translation layer: producer facts -> canonical tax events.csv"
requires-python = ">=3.11"
dependencies = []

[tool.uv]
dev-dependencies = ["pytest>=8"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
addopts = "-q"
```

- [ ] **Step 2: package init files**

Create empty `src/tax_adapter/__init__.py` and empty `tests/__init__.py`.

- [ ] **Step 3: vendor the HP-1 fixture**

Copy VARDE's golden fixture verbatim. Source: `C:\Users\mrkro\Documents\Offshore trading\varde\fixtures\export\hp1_nok_spot_buy.csv`. Write it to `tests/fixtures/varde/hp1_nok_spot_buy.csv` with a header comment is NOT possible in CSV — instead, the content is the exact two lines (header + the HP-1 row):

```
source_row_id,exchange_ts,venue,symbol,product_type,base,quote,side,qty,price,fee,fee_asset,fill_kind,realized_pnl_quote,fx_usdnok_at_fill,order_id,trade_id,strategy_id,book,mode,run_id,schema_version,generated_at
1,2026-03-02T10:15:30Z,firi,BTC/NOK,spot,BTC,NOK,buy,0.05000000,600000.00000000,150.00000000,NOK,taker,0,"{""rate"":""10.7421"",""source"":""norgesbank.eod"",""as_of_ts"":""2026-03-02T00:00:00Z""}",varde-ord-1,varde-1,dca_v1,lab,live,varde-run-2026-03-02,varde/1,2026-03-02T10:15:31Z
```

(If the source file differs, copy the source byte-for-byte instead — it is the frozen golden input.)

- [ ] **Step 4: verify uv runs pytest with zero tests**

Run: `uv run pytest`
Expected: pytest runs (collected 0 items) with exit 0 — confirms the venv + config work.

---

## Task 2: `events.py` — the typed `Event` + validator + serialization

**Files:** Create `src/tax_adapter/events.py`, `tests/test_events_shape.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_events_shape.py`

```python
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
```

- [ ] **Step 2: Run to confirm failure** — `uv run pytest tests/test_events_shape.py` → ModuleNotFoundError.

- [ ] **Step 3: Implement `src/tax_adapter/events.py`**

```python
"""Internal canonical Event — mirrors the frozen 20-column events.csv contract
(CONTRACTS.md Seam B) and replicates Taxes event.py's construction-time shape
invariants so the adapter fails fast instead of emitting a row Taxes rejects.

No dependency on the Taxes package: the seam is the CSV, not the Python class.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

EVENT_TYPES = frozenset({
    "TRADE", "TRANSFER_IN", "TRANSFER_OUT", "INCOME",
    "FEE", "GIFT_IN", "GIFT_OUT", "REQUIRES_REVIEW",
})

REQUIRED_PROVENANCE_KEYS = ("parser", "parser_version", "source_type", "source_ref")

# Frozen 20-column events.csv order (Taxes ADR-0001 / CONTRACTS.md Seam B).
EVENTS_COLUMNS = [
    "event_id", "timestamp", "event_type", "source_id", "source_row_index",
    "asset_out", "quantity_out", "asset_in", "quantity_in",
    "fee_asset", "fee_quantity",
    "income_subtype", "label", "notes",
    "nok_value_out", "nok_value_in",
    "parser", "parser_version", "source_type", "source_ref",
]


class EventShapeError(ValueError):
    """Raised when an Event violates the canonical shape (mirrors event.py §7.2)."""


def _fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    return str(value)


@dataclass(frozen=True)
class Event:
    event_id: str
    timestamp: datetime
    event_type: str
    source_id: str
    source_row_index: int
    asset_out: str | None = None
    quantity_out: Decimal | None = None
    asset_in: str | None = None
    quantity_in: Decimal | None = None
    fee_asset: str | None = None
    fee_quantity: Decimal | None = None
    income_subtype: str | None = None
    label: str | None = None
    notes: str | None = None
    nok_value_out: Decimal | None = None
    nok_value_in: Decimal | None = None
    parser: str = ""
    parser_version: str = ""
    source_type: str = ""
    source_ref: str = ""

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.event_type not in EVENT_TYPES:
            raise EventShapeError(f"unknown event_type {self.event_type!r}")
        if not isinstance(self.timestamp, datetime) or self.timestamp.utcoffset() is None:
            raise EventShapeError("timestamp must be timezone-aware")
        for key in REQUIRED_PROVENANCE_KEYS:
            if not getattr(self, key):
                raise EventShapeError(f"provenance {key!r} is required")
        for name, qty in (("quantity_out", self.quantity_out),
                          ("quantity_in", self.quantity_in),
                          ("fee_quantity", self.fee_quantity)):
            if qty is not None and qty < 0:
                raise EventShapeError(f"{name} must be >= 0")

        out = self.asset_out is not None and self.quantity_out is not None
        inn = self.asset_in is not None and self.quantity_in is not None
        fee = self.fee_asset is not None and self.fee_quantity is not None
        t = self.event_type
        if t == "TRADE":
            if not (out and inn):
                raise EventShapeError("TRADE requires both out and in legs")
        elif t in ("TRANSFER_OUT", "GIFT_OUT"):
            if not out or inn:
                raise EventShapeError(f"{t} requires out leg only")
        elif t in ("TRANSFER_IN", "GIFT_IN", "INCOME"):
            if not inn or out:
                raise EventShapeError(f"{t} requires in leg only")
        elif t == "FEE":
            if not fee or out or inn:
                raise EventShapeError("standalone FEE requires fee fields and no legs")
        # REQUIRES_REVIEW: shape intentionally unconstrained.

    def to_row(self) -> dict[str, str]:
        return {col: _fmt(getattr(self, col)) for col in EVENTS_COLUMNS}


def write_events_csv(events: list[Event], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EVENTS_COLUMNS)
        writer.writeheader()
        for e in events:
            writer.writerow(e.to_row())
```

- [ ] **Step 4: Run to confirm pass** — `uv run pytest tests/test_events_shape.py` → all green.

---

## Task 3: `producers/varde.py` — the VARDE mapper (TDD against HP-1)

**Files:** Create `src/tax_adapter/producers/__init__.py`, `src/tax_adapter/producers/varde.py`, `tests/test_varde_hp1.py`, then generate-and-freeze `tests/fixtures/varde/hp1_expected_events.csv`.

- [ ] **Step 1: Write the golden test (semantic asserts first)** — `tests/test_varde_hp1.py`

```python
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
```

- [ ] **Step 2: Run to confirm failure** — `uv run pytest tests/test_varde_hp1.py` → import error.

- [ ] **Step 3: Implement `src/tax_adapter/producers/varde.py`**

Create empty `src/tax_adapter/producers/__init__.py` first, then:

```python
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


def _map_row(row: dict, *, _seen_trade_ids: set) -> list[Event]:
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
    notional = (qty * price)
    run_id, trade_id, book = row["run_id"], row["trade_id"], row["book"]
    source_id = f"varde-fills:{book}"
    prov = _provenance(row)
    notes = _notes(row)
    eid = lambda leg: f"varde:{run_id}:{trade_id}:{leg}"

    trade = Event(
        event_id=eid(0), timestamp=ts, event_type="TRADE",
        source_id=source_id, source_row_index=0,
        asset_out=quote, quantity_out=notional.quantize(_Q8),
        asset_in=base, quantity_in=qty,
        nok_value_out=notional.quantize(_Q2), nok_value_in=notional.quantize(_Q2),
        notes=notes, **prov,
    )
    fee_event = Event(
        event_id=eid(1), timestamp=ts, event_type="FEE",
        source_id=source_id, source_row_index=1,
        fee_asset=row["fee_asset"], fee_quantity=fee,
        nok_value_out=fee.quantize(_Q2),
        notes=notes, **prov,
    )
    return [trade, fee_event]


def map_varde_fills(rows: list[dict]) -> list[Event]:
    out: list[Event] = []
    seen: set = set()
    for row in rows:
        out.extend(_map_row(row, _seen_trade_ids=seen))
    return out
```

- [ ] **Step 4: Run the golden test** — `uv run pytest tests/test_varde_hp1.py` → all green (semantic asserts pass).

- [ ] **Step 5: Generate-and-freeze the byte-pinned expected events** + add a regression assert

Add a generator-and-freeze step. Run this one-off to produce the frozen file (then commit it as the golden):

```
uv run python -c "from pathlib import Path; from tax_adapter.producers.varde import read_varde_fills, map_varde_fills; from tax_adapter.events import write_events_csv; p=Path('tests/fixtures/varde'); write_events_csv(map_varde_fills(read_varde_fills(p/'hp1_nok_spot_buy.csv')), p/'hp1_expected_events.csv'); print(open(p/'hp1_expected_events.csv').read())"
```

Inspect the printed output — it MUST be a header + two rows: a TRADE (`asset_out=NOK, quantity_out=30000.00000000, asset_in=BTC, quantity_in=0.05000000, nok_value_out=30000.00, nok_value_in=30000.00`) and a FEE (`fee_asset=NOK, fee_quantity=150.00000000, nok_value_out=150.00`). If it matches, the file is frozen. Then add this regression test to `tests/test_varde_hp1.py`:

```python
def test_hp1_output_byte_matches_frozen_golden(tmp_path):
    from tax_adapter.events import write_events_csv
    out = tmp_path / "events.csv"
    write_events_csv(_events(), out)
    expected = (FIX.parent / "hp1_expected_events.csv").read_text(encoding="utf-8")
    assert out.read_text(encoding="utf-8") == expected
```

- [ ] **Step 6: Run** — `uv run pytest tests/test_varde_hp1.py` → all green (semantic + byte-pin).

---

## Task 4: `cli.py` — producer CSV → events.csv

**Files:** Create `src/tax_adapter/cli.py`, `tests/test_cli.py`

- [ ] **Step 1: Write the failing test** — `tests/test_cli.py`

```python
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
```

- [ ] **Step 2: Run to confirm failure** — import error.

- [ ] **Step 3: Implement `src/tax_adapter/cli.py`**

```python
"""CLI: map a producer's declared export CSV -> canonical events.csv.

Usage (PYTHONPATH=src):
    uv run python -m tax_adapter.cli --producer varde --in varde-fills.csv --out events.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

from tax_adapter.events import write_events_csv
from tax_adapter.producers import varde

_PRODUCERS = {"varde": (varde.read_varde_fills, varde.map_varde_fills)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Map producer fills -> canonical events.csv")
    ap.add_argument("--producer", required=True, choices=sorted(_PRODUCERS))
    ap.add_argument("--in", dest="in_path", required=True, type=Path)
    ap.add_argument("--out", dest="out_path", required=True, type=Path)
    args = ap.parse_args(argv)

    read, mapper = _PRODUCERS[args.producer]
    events = mapper(read(args.in_path))
    write_events_csv(events, args.out_path)
    print(f"{args.producer}: wrote {len(events)} event(s) -> {args.out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run** — `uv run pytest tests/test_cli.py` → green.

---

## Task 5: Optional conformance test + column drift guard

**Files:** Create `tests/test_events_conformance.py`, `tests/test_events_columns.py`

- [ ] **Step 1: Column drift guard** — `tests/test_events_columns.py`

```python
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
```

- [ ] **Step 2: Optional conformance test (skip-if-Taxes-unavailable)** — `tests/test_events_conformance.py`

This proves the emitted rows construct a REAL `CanonicalEvent` (ground truth) when the Taxes repo is importable locally. It is **best-effort** — skipped, never failed, when Taxes is absent.

```python
"""Optional: validate emitted events against the REAL Taxes CanonicalEvent.

Skipped unless the Taxes package is importable locally. This is a truth-check, not
a build dependency — the adapter's contract is the events.csv columns, not the
Taxes Python class.
"""
import sys
from pathlib import Path

import pytest

# Try to make the local Taxes package importable; skip cleanly if not present.
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
    # Adapt the adapter's string asset (qualified key) to Taxes' AssetIdentity.
    # IMPLEMENTER: read Taxes/src/tax_core/models/asset.py for the real constructor
    # / parser; this is the one place the test couples to Taxes internals.
    return AssetIdentity(sym) if sym is not None else None


def test_emitted_events_construct_real_canonical_event():
    for e in map_varde_fills(read_varde_fills(FIX)):
        CanonicalEvent(
            event_id=e.event_id, timestamp=e.timestamp, event_type=e.event_type,
            source_id=e.source_id, source_row_index=e.source_row_index,
            asset_out=_asset(e.asset_out), quantity_out=e.quantity_out,
            asset_in=_asset(e.asset_in), quantity_in=e.quantity_in,
            fee_asset=_asset(e.fee_asset), fee_quantity=e.fee_quantity,
            nok_value_out=e.nok_value_out, nok_value_in=e.nok_value_in,
            provenance={k: getattr(e, k) for k in
                        ("parser", "parser_version", "source_type", "source_ref")},
        )  # constructs without TaxError => our rows are shape-conformant
```

> **IMPLEMENTER NOTE:** `AssetIdentity(sym)` is a placeholder — read `Taxes/src/tax_core/models/asset.py` and use its real constructor/parser (it may be `AssetIdentity.parse(sym)` or require a kind). Adjust the `CanonicalEvent(...)` kwargs to match the real signature if it has diverged. Because the test is `skipif`-guarded, getting this exactly right is a nice-to-have, not a v1 gate — but wire it correctly if Taxes is present so the truth-check actually runs.

- [ ] **Step 3: Run the full suite** — `uv run pytest`
Expected: green. The conformance test either passes (Taxes present + wired) or is skipped (Taxes absent). Report which.

---

## Self-Review

**Spec coverage (design note):**
- ✅ Seam: internal typed `Event` mirroring 20-col events.csv + `event.py` invariants → `write_events_csv` (Task 2).
- ✅ No runtime Taxes import; optional skip-if-unavailable conformance test (Task 5).
- ✅ Tiny scaffold: one mapper, one CLI, one serialization layer (Tasks 1,3,4).
- ✅ HP-1 golden centerpiece — semantic asserts + byte-pin (Task 3); shape unit tests (Task 2); column drift guard (Task 5).
- ✅ v1 = NOK-quoted buy only; sell/USDT/transfer → `NotImplementedError` (Task 3, asserted).
- ✅ `notes` is write-only overflow, never parsed (rule stated; test asserts existence only, never parses).

**Acceptance (first slice):** `uv run pytest` green; `test_varde_hp1` semantic + byte-pin pass; CLI produces the 2-row deterministic CSV.

**Type/name consistency:** `Event`, `EVENTS_COLUMNS`, `EventShapeError`, `write_events_csv`, `read_varde_fills`, `map_varde_fills`, `cli.main` are defined once and used consistently across tasks. `_PARSER_VERSION="varde/1->event/1"` is used in both the mapper and the test provenance.

**Determinism:** no clock/randomness in the mapping; timestamps come from `exchange_ts`; the golden is generate-then-frozen with independent semantic asserts guarding correctness.

**Next slice (separate):** slice 2 extends the same `Event`/mapper to VARDE sell (TRADE base-out/quote-in), USDC/USDT-quoted (TRADE + `fx_usdnok_at_fill`; missing FX → `nok_value=None` UNRESOLVED), and XRPL transfers (linked TRANSFER_OUT/IN), each with unit tests — per SCHEMAS §3.7.
