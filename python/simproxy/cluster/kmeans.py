"""Clean-room SimPoint clustering core.

The algorithm follows the SimPoint methodology:

1. Optionally reduce dimensionality with a sparse random projection
   (Achlioptas-style).
2. Run k-means (k-means++ seeding) for a range of ``k`` values.
3. Score each clustering with BIC and pick the smallest ``k`` whose score is at
   least ``min_bic + bic_tolerance * (max_bic - min_bic)``, matching the
   reference SimPoint threshold rule.
4. For each cluster, pick the interval closest to its centroid as the
   representative simulation point; the cluster's weight is its share of
   intervals.

The BIC convention here is **higher is better** (the classic k-means BIC is
negated); this keeps the "within 90% of the best" selection rule intuitive.
It is validated against the reference SimPoint 3.2 binary in M2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

__all__ = [
    "ClusterResult",
    "bic_score",
    "cluster",
    "lloyd",
    "random_projection",
    "select_representatives",
]


@dataclass
class ClusterResult:
    k: int
    labels: np.ndarray
    centers: np.ndarray
    inertia: float
    bic: float
    projected: np.ndarray
    trials: list[dict[str, Any]] = field(default_factory=list)


def random_projection(matrix: np.ndarray, out_dim: int, seed: int = 0) -> np.ndarray:
    """Sparse Achlioptas random projection to ``out_dim`` dimensions."""
    if matrix.ndim != 2:
        raise ValueError("matrix must be two-dimensional")
    if out_dim <= 0 or out_dim >= matrix.shape[1]:
        return matrix.copy()

    rng = np.random.default_rng(seed)
    scale = np.sqrt(3.0)
    projection = rng.choice(
        [-scale, 0.0, scale],
        size=(matrix.shape[1], out_dim),
        p=[1.0 / 6.0, 2.0 / 3.0, 1.0 / 6.0],
    )
    return matrix @ projection


def _kmeans_pp(matrix: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    n = matrix.shape[0]
    centers = [matrix[int(rng.integers(n))].copy()]
    closest = ((matrix - centers[0]) ** 2).sum(axis=1)
    for _ in range(1, k):
        total = float(closest.sum())
        if total <= 0.0:
            centers.append(matrix[int(rng.integers(n))].copy())
        else:
            centers.append(matrix[int(rng.choice(n, p=closest / total))].copy())
        new_dist = ((matrix - centers[-1]) ** 2).sum(axis=1)
        closest = np.minimum(closest, new_dist)
    return np.vstack(centers)


def _assign(matrix: np.ndarray, centers: np.ndarray) -> tuple[np.ndarray, float]:
    diff = matrix[:, None, :] - centers[None, :, :]
    distances = np.einsum("nkd,nkd->nk", diff, diff)
    labels = distances.argmin(axis=1)
    inertia = float(distances[np.arange(matrix.shape[0]), labels].sum())
    return labels, inertia


def lloyd(
    matrix: np.ndarray,
    centers: np.ndarray,
    max_iter: int = 100,
    tol: float = 1e-6,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Lloyd's algorithm. Returns ``(labels, centers, inertia)``."""
    labels, inertia = _assign(matrix, centers)
    centers = centers.copy()
    for _ in range(max_iter):
        for cluster_id in range(centers.shape[0]):
            mask = labels == cluster_id
            if mask.any():
                centers[cluster_id] = matrix[mask].mean(axis=0)
        new_labels, new_inertia = _assign(matrix, centers)
        converged = abs(inertia - new_inertia) <= tol * max(inertia, 1.0)
        labels, inertia = new_labels, new_inertia
        if converged or inertia == 0.0:
            break
    return labels, centers, inertia


def _distortion(matrix: np.ndarray, labels: np.ndarray, centers: np.ndarray) -> float:
    diff = matrix - centers[labels]
    return float(np.einsum("nd,nd->", diff, diff))


def bic_score(
    matrix: np.ndarray,
    labels: np.ndarray,
    centers: np.ndarray,
    weights: np.ndarray | None = None,
) -> float:
    """SimPoint-compatible BIC score (higher is better).

    Mirrors ``KMeans::bicScore`` from the reference SimPoint toolkit, including
    the cluster-probability term and the ``(k-1) + k*dim + 1`` parameter count.
    """
    n, dim = matrix.shape
    k = centers.shape[0]
    if weights is None:
        weights = np.ones(n, dtype=np.float64)
    total_weight = float(weights.sum())
    if total_weight <= 0.0:
        return float("-inf")

    distortion = _distortion(matrix, labels, centers)
    sigma2 = max(distortion / (dim * n), 1e-300)
    likelihood = -dim * (np.log(2.0 * np.pi * sigma2) + 1.0) / 2.0 - np.log(
        total_weight
    )

    cluster_weights = np.bincount(labels, weights=weights, minlength=k)
    for row in range(n):
        cluster_weight = cluster_weights[labels[row]]
        if cluster_weight > 0.0:
            likelihood += np.log(cluster_weight) * weights[row] / total_weight
    likelihood *= n

    num_parameters = (k - 1) + k * dim + 1
    penalty = num_parameters / 2.0 * np.log(n)
    return float(likelihood - penalty)


def cluster(
    matrix: np.ndarray,
    k_min: int = 1,
    k_max: int = 10,
    seed: int = 0,
    projection_dim: int = 10,
    max_iter: int = 100,
    bic_tolerance: float = 0.9,
) -> ClusterResult:
    """Run SimPoint-style clustering over ``k_min..k_max`` and pick a ``k``."""
    if matrix.ndim != 2:
        raise ValueError("matrix must be two-dimensional")
    if matrix.shape[0] == 0:
        raise ValueError("cannot cluster an empty matrix")

    n = matrix.shape[0]
    k_min = max(1, int(k_min))
    k_max = min(int(k_max), n)
    if k_max < k_min:
        k_max = k_min

    projected = random_projection(matrix, projection_dim, seed)

    full_trials: list[dict[str, Any]] = []
    summary: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    for k in range(k_min, k_max + 1):
        rng = np.random.default_rng(seed + k)
        centers = _kmeans_pp(projected, k, rng)
        labels, centers, inertia = lloyd(projected, centers, max_iter=max_iter)
        score = bic_score(projected, labels, centers)
        trial = {
            "k": k,
            "inertia": inertia,
            "bic": score,
            "labels": labels,
            "centers": centers,
        }
        full_trials.append(trial)
        summary.append({"k": k, "inertia": inertia, "bic": score})
        if best is None or score > best["bic"]:
            best = trial

    assert best is not None
    min_bic = min(trial["bic"] for trial in full_trials)
    threshold = (best["bic"] - min_bic) * bic_tolerance + min_bic
    chosen = next(trial for trial in full_trials if trial["bic"] >= threshold)

    return ClusterResult(
        k=chosen["k"],
        labels=chosen["labels"],
        centers=chosen["centers"],
        inertia=chosen["inertia"],
        bic=chosen["bic"],
        projected=projected,
        trials=summary,
    )


def select_representatives(
    projected: np.ndarray, labels: np.ndarray, centers: np.ndarray
) -> list[int]:
    """Return the row index closest to each non-empty cluster centroid."""
    representatives: list[int] = []
    for cluster_id in range(centers.shape[0]):
        members = np.flatnonzero(labels == cluster_id)
        if members.size == 0:
            continue
        distances = ((projected[members] - centers[cluster_id]) ** 2).sum(axis=1)
        representatives.append(int(members[int(distances.argmin())]))
    return representatives
