#!/usr/bin/env python3
"""Randomized equivalence benchmark against the reference SimPoint 3.2 binary.

Each case synthesizes a well-separated multi-phase BBV, runs both the reference
binary and SimProxy's reference-compatible backend, and reports whether the
selected intervals and weights agree.

Example:
    SIMPOINT_BIN=/path/to/simpoint python scripts/benchmark_simpoint.py --cases 20
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from simproxy.cluster import cluster_reference
from simproxy.formats.bbv import BBV, parse_bbv, to_matrix, write_bbv

_BIC_PATTERN = re.compile(r"BIC score:\s*([0-9.eE+-]+)")


def make_bbv(num_phases, blocks_per_phase, intervals_per_phase, noise, seed) -> BBV:
    rng = np.random.default_rng(seed)
    phases = []
    for phase in range(num_phases):
        first = phase * blocks_per_phase + 1
        phases.append((range(first, first + blocks_per_phase), 1000.0 * (phase + 1)))

    order = [phase for phase in range(num_phases) for _ in range(intervals_per_phase)]
    rng.shuffle(order)

    bbv = BBV()
    for interval, phase in enumerate(order):
        blocks, base = phases[phase]
        bbv.append(
            {
                block: int(base * rng.uniform(1.0 - noise, 1.0 + noise))
                for block in blocks
            },
            interval_id=interval,
        )
    return bbv


def run_reference(binary: Path, bbv_path: Path, k: int, workdir: Path):
    simpoints_path = workdir / "ref.simpoints"
    weights_path = workdir / "ref.weights"
    completed = subprocess.run(
        [
            str(binary),
            "-loadFVFile",
            str(bbv_path),
            "-k",
            str(k),
            "-saveSimpoints",
            str(simpoints_path),
            "-saveSimpointWeights",
            str(weights_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    intervals = [
        int(line.split()[0])
        for line in simpoints_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    weights = [
        float(line.split()[0])
        for line in weights_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    scores = [float(match) for match in _BIC_PATTERN.findall(completed.stdout)]
    return intervals, weights, max(scores)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=int, default=20)
    parser.add_argument("--simpoint-bin", type=Path, default=None)
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("--weight-tolerance", type=float, default=1e-6)
    args = parser.parse_args(argv)

    binary = args.simpoint_bin or (
        Path(os.environ["SIMPOINT_BIN"]) if "SIMPOINT_BIN" in os.environ else None
    )
    if binary is None or not binary.exists():
        parser.error("set SIMPOINT_BIN or pass --simpoint-bin")

    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        for case in range(args.cases):
            rng = np.random.default_rng(1000 + case)
            num_phases = int(rng.integers(2, 6))
            blocks = int(rng.integers(3, 9))
            per_phase = int(rng.integers(8, 21))
            noise = float(rng.uniform(0.0, 0.4))
            bbv = make_bbv(num_phases, blocks, per_phase, noise, 1000 + case)
            bbv_path = workdir / f"case{case}.bbv"
            write_bbv(bbv_path, bbv)

            ref_intervals, ref_weights, ref_bic = run_reference(
                binary, bbv_path, num_phases, workdir
            )
            parsed = parse_bbv(bbv_path)
            _, matrix = to_matrix(parsed, normalize=True)
            result = cluster_reference(matrix, num_phases)
            our_intervals = [
                parsed.interval_ids[index] for index in result.representatives
            ]

            intervals_match = sorted(our_intervals) == sorted(ref_intervals)
            our_weights = [
                result.weights[cluster_id]
                for cluster_id in result.representative_clusters
            ]
            if len(our_weights) != len(ref_weights):
                weight_error = float("inf")
            else:
                weight_error = max(
                    abs(a - b)
                    for a, b in zip(
                        sorted(ref_weights), sorted(our_weights), strict=True
                    )
                )
            passed = intervals_match and weight_error <= args.weight_tolerance
            rows.append(
                {
                    "case": case,
                    "num_phases": num_phases,
                    "blocks": blocks,
                    "intervals_per_phase": per_phase,
                    "noise": round(noise, 4),
                    "intervals_match": intervals_match,
                    "weight_max_abs_error": weight_error,
                    "bic_delta": abs(result.bic - ref_bic),
                    "passed": passed,
                }
            )
            print(
                f"case {case:2d}: phases={num_phases} blocks={blocks} "
                f"per_phase={per_phase} noise={noise:.2f} "
                f"intervals={'ok' if intervals_match else 'DIFF'} "
                f"weight_err={weight_error:.2e} bic_delta={abs(result.bic - ref_bic):.2e}"
            )

    failures = sum(not row["passed"] for row in rows)
    print(
        f"\n{len(rows) - failures}/{len(rows)} cases matched "
        f"(intervals exact, weight error <= {args.weight_tolerance})"
    )
    if args.json:
        args.json.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
