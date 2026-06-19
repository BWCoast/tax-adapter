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
