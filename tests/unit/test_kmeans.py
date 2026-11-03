from __future__ import annotations

import numpy as np
from simproxy.cluster import (
    bic_score,
    cluster,
    lloyd,
    random_projection,
    select_representatives,
)


def _blobs(seed: int = 0):
    rng = np.random.default_rng(seed)
    centers = np.zeros((3, 12))
    centers[0, 0] = 10.0
    centers[1, 1] = 10.0
    centers[2, 2] = 10.0
    return np.vstack(
        [center + rng.normal(scale=0.05, size=(30, 12)) for center in centers]
    )


def test_random_projection_shape():
    matrix = _blobs()
    projected = random_projection(matrix, 5, seed=1)
    assert projected.shape == (matrix.shape[0], 5)
    assert random_projection(matrix, 12, seed=1).shape == matrix.shape


def test_lloyd_converges_on_separated_blobs():
    matrix = _blobs()
    centers = matrix[[0, 30, 60]].copy()
    labels, centers, inertia = lloyd(matrix, centers)
    assert inertia >= 0.0
    assert len(np.unique(labels)) == 3
    for cluster_id in range(3):
        members = labels == cluster_id
        assert members.sum() == 30


def test_cluster_picks_three_phases():
    matrix = _blobs()
    result = cluster(
        matrix, k_min=2, k_max=6, seed=0, projection_dim=6, bic_tolerance=1.0
    )
    assert result.k == 3
    assert len(result.trials) == 5
    assert result.trials[-1]["k"] == 6


def test_select_representatives_one_per_cluster():
    matrix = _blobs()
    result = cluster(
        matrix, k_min=2, k_max=6, seed=0, projection_dim=6, bic_tolerance=1.0
    )
    representatives = select_representatives(
        result.projected, result.labels, result.centers
    )
    assert len(representatives) == result.k
    for cluster_id, representative in enumerate(representatives):
        assert result.labels[representative] == cluster_id


def test_bic_prefers_correct_assignment():
    matrix = _blobs()
    good_labels = np.repeat([0, 1, 2], 30)
    good_centers = np.vstack(
        [matrix[good_labels == cluster_id].mean(axis=0) for cluster_id in range(3)]
    )
    bad_labels = np.zeros(matrix.shape[0], dtype=np.int64)
    bad_centers = matrix.mean(axis=0, keepdims=True)
    assert bic_score(matrix, good_labels, good_centers) > bic_score(
        matrix, bad_labels, bad_centers
    )
