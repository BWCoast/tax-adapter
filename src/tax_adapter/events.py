"""Internal canonical Event — mirrors the frozen 20-column events.csv contract
(CONTRACTS.md Seam B) and replicates Taxes event.py's construction-time shape
invariants so the adapter fails fast instead of emitting a row Taxes rejects.

No dependency on the Taxes package: the seam is the CSV, not the Python class.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
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
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
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
        if not isinstance(self.timestamp, datetime):
            raise EventShapeError("timestamp is required and must be a datetime")
        if self.timestamp.utcoffset() is None:
            raise EventShapeError("timestamp must be timezone-aware")
        for key in REQUIRED_PROVENANCE_KEYS:
            if not getattr(self, key):
                raise EventShapeError(f"provenance {key!r} is required")
        for name, qty in (("quantity_out", self.quantity_out),
                          ("quantity_in", self.quantity_in),
                          ("fee_quantity", self.fee_quantity)):
            if qty is not None and qty < 0:
                raise EventShapeError(f"{name} must be >= 0")

        out_present = self.asset_out is not None and self.quantity_out is not None
        in_present = self.asset_in is not None and self.quantity_in is not None
        out_absent = self.asset_out is None and self.quantity_out is None
        in_absent = self.asset_in is None and self.quantity_in is None
        fee_present = self.fee_asset is not None and self.fee_quantity is not None
        t = self.event_type
        if t == "TRADE":
            if not (out_present and in_present):
                raise EventShapeError("TRADE requires both out and in legs")
        elif t in ("TRANSFER_OUT", "GIFT_OUT"):
            if not out_present:
                raise EventShapeError(f"{t} requires out leg")
            if not in_absent:
                raise EventShapeError(f"{t} must not set the in-side")
        elif t in ("TRANSFER_IN", "GIFT_IN", "INCOME"):
            if not in_present:
                raise EventShapeError(f"{t} requires in leg")
            if not out_absent:
                raise EventShapeError(f"{t} must not set the out-side")
        elif t == "FEE":
            if not fee_present:
                raise EventShapeError("standalone FEE requires fee fields")
            if not (out_absent and in_absent):
                raise EventShapeError("standalone FEE must not set in/out sides")
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
