"""SimPoint Basic Block Vector (``.bbv``) parsing, writing and matrix conversion.

Two textual dialects are accepted:

* SimPoint 3.x::

      T0: 1:12 3:7 8:1
      T1: 2:5 3:9

* DynamoRIO ``drpoints``::

      T:1:12 :3:7 :8:1
      T:2:5 :3:9

Counts are already weighted by the number of instructions in the basic block, so the
sum of a vector is the number of instructions executed in that interval.
"""

from __future__ import annotations

import gzip
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

Counts = dict[int, float]

__all__ = [
    "BBV",
    "concat_bbv",
    "normalize_counts",
    "parse_bbv",
    "to_matrix",
    "write_bbv",
]


@dataclass
class BBV:
    """A sequence of per-interval basic block frequency vectors."""

    intervals: list[Counts] = field(default_factory=list)
    interval_ids: list[int] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.intervals)

    def __iter__(self) -> Iterator[Counts]:
        return iter(self.intervals)

    def append(self, counts: Counts, interval_id: int | None = None) -> None:
        if interval_id is None:
            interval_id = self.interval_ids[-1] + 1 if self.interval_ids else 0
        self.intervals.append(dict(counts))
        self.interval_ids.append(interval_id)

    @property
    def bbids(self) -> list[int]:
        ids: set[int] = set()
        for counts in self.intervals:
            ids.update(counts)
        return sorted(ids)

    def total_instructions(self) -> float:
        return float(sum(sum(counts.values()) for counts in self.intervals))

    def normalize(self) -> BBV:
        return BBV(
            intervals=[normalize_counts(counts) for counts in self.intervals],
            interval_ids=list(self.interval_ids),
        )


def _fmt_count(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return repr(float(value))


def _parse_line(line: str, sequence: int) -> tuple[int, Counts] | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    if line.startswith("T:"):
        # drpoints dialect: interval id is implicit (line order).
        interval_id = sequence
        body = line[2:]
    else:
        head, sep, body = line.partition(":")
        if not sep or not head.startswith("T") or not head[1:].isdigit():
            raise ValueError(f"malformed BBV line: {line!r}")
        interval_id = int(head[1:])

    tokens = body.replace(":", " ").split()
    if len(tokens) % 2 != 0:
        raise ValueError(f"malformed BBV line (odd token count): {line!r}")

    counts: Counts = {}
    for i in range(0, len(tokens), 2):
        bbid = int(tokens[i])
        count = float(tokens[i + 1])
        counts[bbid] = counts.get(bbid, 0.0) + count
    return interval_id, counts


def _open_text(path: Path, mode: str):
    if path.suffix == ".gz":
        return gzip.open(path, mode, encoding="utf-8")
    return open(path, mode, encoding="utf-8")


def parse_bbv(path: str | Path) -> BBV:
    """Parse a ``.bbv`` file (optionally gzip-compressed)."""
    path = Path(path)
    bbv = BBV()
    with _open_text(path, "rt") as fh:
        for sequence, line in enumerate(fh):
            parsed = _parse_line(line, sequence)
            if parsed is None:
                continue
            interval_id, counts = parsed
            bbv.intervals.append(counts)
            bbv.interval_ids.append(interval_id)
    return bbv


def write_bbv(path: str | Path, bbv: BBV) -> None:
    """Write a ``.bbv`` file in SimPoint 3.x dialect."""
    path = Path(path)
    with _open_text(path, "wt") as fh:
        for interval_id, counts in zip(bbv.interval_ids, bbv.intervals, strict=True):
            pairs = " ".join(
                f"{bbid}:{_fmt_count(count)}"
                for bbid, count in sorted(counts.items())
                if count != 0
            )
            fh.write(f"T{interval_id}: {pairs}\n")


def normalize_counts(counts: Counts) -> Counts:
    """Normalize a frequency vector so that it sums to one."""
    total = float(sum(counts.values()))
    if total == 0.0:
        return {bbid: 0.0 for bbid in counts}
    return {bbid: float(value) / total for bbid, value in counts.items()}


def to_matrix(
    bbv: BBV, normalize: bool = True
) -> tuple[np.ndarray, np.ndarray]:
    """Convert a :class:`BBV` to a dense ``(num_intervals, num_blocks)`` matrix.

    Returns the sorted basic block ids alongside the matrix. Zero intervals are left
    as all-zero rows (or normalized to zeros) so that row indices keep matching
    ``bbv.intervals``.
    """
    bbids = bbv.bbids
    index = {bbid: i for i, bbid in enumerate(bbids)}
    matrix = np.zeros((len(bbv), len(bbids)), dtype=np.float64)
    for row, counts in enumerate(bbv.intervals):
        for bbid, count in counts.items():
            matrix[row, index[bbid]] = count
    if normalize and matrix.size:
        totals = matrix.sum(axis=1, keepdims=True)
        totals[totals == 0.0] = 1.0
        matrix /= totals
    return np.asarray(bbids, dtype=np.int64), matrix


def concat_bbv(bbvs: Sequence[BBV]) -> BBV:
    """Concatenate several BBV files in execution order."""
    out = BBV()
    for bbv in bbvs:
        out.intervals.extend(dict(c) for c in bbv.intervals)
        out.interval_ids.extend(bbv.interval_ids)
    return out
