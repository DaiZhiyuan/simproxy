from __future__ import annotations

import os
import subprocess
from pathlib import Path

import numpy as np
import pytest
from simproxy.cluster import cluster, select_representatives
from simproxy.formats.bbv import BBV, parse_bbv, to_matrix, write_bbv

SIMPOINT_BIN = os.environ.get("SIMPOINT_BIN")
pytestmark = pytest.mark.skipif(
    not SIMPOINT_BIN or not Path(SIMPOINT_BIN).exists(),
    reason="set SIMPOINT_BIN to the reference SimPoint 3.2 binary",
)


def _three_phase_bbv(seed: int = 7) -> BBV:
    rng = np.random.default_rng(seed)
    bbv = BBV()
    phases = [(range(1, 6), 1000), (range(6, 11), 1000), (range(11, 16), 1000)]
    order = [index % 3 for index in range(90)]
    rng.shuffle(order)
    for interval, phase in enumerate(order):
        blocks, base = phases[phase]
        bbv.append(
            {block: int(rng.integers(base // 2, base * 2)) for block in blocks},
            interval_id=interval,
        )
    return bbv


def test_matches_reference_simpoint(tmp_path):
    bbv = _three_phase_bbv()
    bbv_path = tmp_path / "sample.bbv"
    write_bbv(bbv_path, bbv)

    simpoints_path = tmp_path / "ref.simpoints"
    weights_path = tmp_path / "ref.weights"
    subprocess.run(
        [
            SIMPOINT_BIN,
            "-loadFVFile",
            str(bbv_path),
            "-k",
            "3",
            "-saveSimpoints",
            str(simpoints_path),
            "-saveSimpointWeights",
            str(weights_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    reference_intervals = {
        int(line.split()[0])
        for line in simpoints_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    reference_weights = sorted(
        float(line.split()[0])
        for line in weights_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )

    parsed = parse_bbv(bbv_path)
    _, matrix = to_matrix(parsed, normalize=True)
    result = cluster(
        matrix, k_min=3, k_max=3, seed=0, projection_dim=10, bic_tolerance=1.0
    )
    representatives = select_representatives(
        result.projected, result.labels, result.centers
    )
    our_intervals = {parsed.interval_ids[index] for index in representatives}
    our_weights = sorted(
        (np.bincount(result.labels, minlength=result.k) / len(matrix)).tolist()
    )

    assert our_intervals == reference_intervals
    assert np.allclose(our_weights, reference_weights, atol=1e-6)
