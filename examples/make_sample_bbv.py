#!/usr/bin/env python3
"""Create a small three-phase BBV for the quickstart."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from simproxy.formats.bbv import BBV, write_bbv


def make_sample(path: Path, intervals_per_phase: int = 30, seed: int = 7) -> BBV:
    rng = np.random.default_rng(seed)
    phases = [
        (range(1, 6), 1000),
        (range(6, 11), 2000),
        (range(11, 16), 3000),
    ]
    order = [
        phase for phase in range(len(phases)) for _ in range(intervals_per_phase)
    ]
    rng.shuffle(order)

    bbv = BBV()
    for interval, phase in enumerate(order):
        blocks, base = phases[phase]
        bbv.append(
            {block: int(rng.integers(base // 2, base * 2)) for block in blocks},
            interval_id=interval,
        )
    write_bbv(path, bbv)
    return bbv


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, nargs="?", default=Path("phase_sample.bbv"))
    parser.add_argument("--intervals-per-phase", type=int, default=30)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    bbv = make_sample(args.output, args.intervals_per_phase, args.seed)
    print(f"wrote {len(bbv)} intervals to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
