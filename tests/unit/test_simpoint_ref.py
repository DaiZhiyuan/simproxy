from __future__ import annotations

import numpy as np
from simproxy.cluster import (
    Ran2,
    cluster_reference,
    dense_projection,
    projection_matrix,
    sample_init,
)


def test_ran2_is_deterministic_and_bounded():
    first = Ran2(2042712918)
    second = Ran2(2042712918)
    values = [float(first.rand_float()) for _ in range(100)]
    assert values == [float(second.rand_float()) for _ in range(100)]
    assert all(0.0 < value < 1.0 for value in values)


def test_projection_matrix_is_reproducible():
    first = projection_matrix(2042712918, 6, 4)
    second = projection_matrix(2042712918, 6, 4)
    assert np.array_equal(first, second)
    assert first.shape == (6, 4)
    assert np.all(first >= -1.0) and np.all(first <= 1.0)


def test_sample_init_uses_requested_rows():
    matrix = np.arange(60, dtype=np.float64).reshape(10, 6)
    centers = sample_init(matrix, 3, 493575226)
    assert centers.shape == (3, 6)
    assert np.array_equal(sample_init(matrix, 3, 493575226), centers)


def test_dense_projection_shape():
    matrix = np.ones((8, 5))
    projected = dense_projection(matrix, 3, 2042712918)
    assert projected.shape == (8, 3)


def test_cluster_reference_finds_three_blobs():
    rng = np.random.default_rng(0)
    centers = np.zeros((3, 12))
    centers[0, 0] = 10.0
    centers[1, 1] = 10.0
    centers[2, 2] = 10.0
    matrix = np.vstack(
        [center + rng.normal(scale=0.05, size=(20, 12)) for center in centers]
    )
    result = cluster_reference(matrix, 3)
    assert result.k == 3
    assert len(result.representatives) == 3
    assert len(result.representative_clusters) == 3
    assert np.allclose(sum(result.weights), 1.0)
