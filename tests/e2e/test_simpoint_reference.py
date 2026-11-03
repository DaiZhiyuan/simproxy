from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import numpy as np
import pytest
from simproxy.cluster import cluster_reference
from simproxy.formats.bbv import BBV, parse_bbv, to_matrix, write_bbv

SIMPOINT_BIN = os.environ.get("SIMPOINT_BIN")
pytestmark = pytest.mark.skipif(
    not SIMPOINT_BIN or not Path(SIMPOINT_BIN).exists(),
    reason="set SIMPOINT_BIN to the reference SimPoint 3.2 binary",
)

_BIC_PATTERN = re.compile(r"BIC score:\s*([0-9.eE+-]+)")


def _phase_bbv(
    num_phases: int,
    blocks_per_phase: int,
    intervals_per_phase: int,
    seed: int,
    noise: float = 0.2,
) -> BBV:
    rng = np.random.default_rng(seed)
    phases = []
    for phase in range(num_phases):
        first = phase * blocks_per_phase + 1
        blocks = range(first, first + blocks_per_phase)
        phases.append((blocks, 1000.0 * (phase + 1)))

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


def _run_reference(bbv_path: Path, k: int, workdir: Path):
    simpoints_path = workdir / "reference.simpoints"
    weights_path = workdir / "reference.weights"
    completed = subprocess.run(
        [
            SIMPOINT_BIN,
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


@pytest.mark.parametrize(
    ("num_phases", "blocks", "per_phase", "seed"),
    [
        (3, 5, 12, 7),
        (4, 4, 10, 11),
        (2, 8, 16, 23),
    ],
)
def test_reference_backend_matches_simpoint(
    tmp_path, num_phases, blocks, per_phase, seed
):
    bbv = _phase_bbv(num_phases, blocks, per_phase, seed)
    bbv_path = tmp_path / "sample.bbv"
    write_bbv(bbv_path, bbv)

    reference_intervals, reference_weights, reference_bic = _run_reference(
        bbv_path, num_phases, tmp_path
    )

    parsed = parse_bbv(bbv_path)
    _, matrix = to_matrix(parsed, normalize=True)
    result = cluster_reference(matrix, num_phases)

    our_intervals = [parsed.interval_ids[index] for index in result.representatives]
    our_weights = [
        result.weights[cluster_id] for cluster_id in result.representative_clusters
    ]

    assert sorted(our_intervals) == sorted(reference_intervals)
    assert np.allclose(sorted(our_weights), sorted(reference_weights), atol=1e-9)
    assert result.bic == pytest.approx(reference_bic, abs=1e-2)
