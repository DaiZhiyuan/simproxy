#!/usr/bin/env python3
"""Compare SimProxy clustering against the reference SimPoint 3.2 binary.

Example:
    SIMPOINT_BIN=/path/to/SimPoint.3.2/bin/simpoint \
      python scripts/validate_simpoint.py prog.bbv --k 3 --strict

The reference binary is only used as a test oracle; SimProxy never links against
it and ships no SimPoint code.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from simproxy.cluster import cluster, select_representatives
from simproxy.formats.bbv import parse_bbv, to_matrix


def run_reference(binary: Path, bbv_path: Path, k: int, workdir: Path):
    simpoints_path = workdir / "reference.simpoints"
    weights_path = workdir / "reference.weights"
    command = [
        str(binary),
        "-loadFVFile",
        str(bbv_path),
        "-k",
        str(k),
        "-saveSimpoints",
        str(simpoints_path),
        "-saveSimpointWeights",
        str(weights_path),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
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
    return intervals, weights


def run_simproxy(bbv_path: Path, k: int, projection_dim: int):
    bbv = parse_bbv(bbv_path)
    _, matrix = to_matrix(bbv, normalize=True)
    result = cluster(
        matrix,
        k_min=k,
        k_max=k,
        seed=0,
        projection_dim=projection_dim,
        bic_tolerance=1.0,
    )
    representatives = select_representatives(
        result.projected, result.labels, result.centers
    )
    weights = np.bincount(result.labels, minlength=result.k) / len(matrix)
    intervals = [bbv.interval_ids[index] for index in representatives]
    return intervals, weights.tolist()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bbv", type=Path)
    parser.add_argument("--k", type=int, required=True)
    parser.add_argument("--simpoint-bin", type=Path, default=None)
    parser.add_argument("--projection-dim", type=int, default=10)
    parser.add_argument("--tolerance", type=float, default=1e-6)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="require the exact same representative intervals",
    )
    args = parser.parse_args(argv)

    binary = args.simpoint_bin
    if binary is None:
        import os

        env = os.environ.get("SIMPOINT_BIN")
        if not env:
            parser.error("set SIMPOINT_BIN or pass --simpoint-bin")
        binary = Path(env)
    if not binary.exists():
        parser.error(f"reference binary not found: {binary}")

    with tempfile.TemporaryDirectory() as tmp:
        reference_intervals, reference_weights = run_reference(
            binary, args.bbv, args.k, Path(tmp)
        )
    our_intervals, our_weights = run_simproxy(
        args.bbv, args.k, args.projection_dim
    )

    print(f"reference intervals: {sorted(reference_intervals)}")
    print(f"simproxy  intervals: {sorted(our_intervals)}")
    print(f"reference weights:   {sorted(reference_weights)}")
    print(f"simproxy  weights:   {sorted(our_weights)}")

    failures = []
    if len(reference_intervals) != len(our_intervals):
        failures.append("different number of simulation points")
    if not np.allclose(
        sorted(reference_weights), sorted(our_weights), atol=args.tolerance
    ):
        failures.append("weights differ beyond tolerance")
    if args.strict and sorted(reference_intervals) != sorted(our_intervals):
        failures.append("representative intervals differ (strict mode)")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
