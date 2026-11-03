"""Per-interval feature schema (M1).

The feature table is the contract between the profiler and the synthesizer. It is
versioned via :data:`FEATURE_SCHEMA_VERSION`; any incompatible change must bump it
and update ``docs/data-format.md``.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "FEATURE_SCHEMA_VERSION",
    "FeatureTable",
    "IntervalFeatures",
]

FEATURE_SCHEMA_VERSION = 1


@dataclass
class IntervalFeatures:
    interval: int
    instructions: int
    num_blocks: int = 0
    bbv_entropy: float = 0.0
    top_block_share: float = 0.0
    opcode_mix: dict[str, float] = field(default_factory=dict)
    loads: int = 0
    stores: int = 0
    distinct_lines: int = 0
    stride_hist: dict[str, int] = field(default_factory=dict)
    read_write_ratio: float = 0.0
    branch_taken_rate: float = 0.0
    branch_entropy: float = 0.0
    dep_chain_len: float = 0.0
    working_set_bytes: int = 0
    extras: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IntervalFeatures:
        known = {field_name for field_name in cls.__dataclass_fields__}
        payload = {key: value for key, value in data.items() if key in known}
        return cls(**payload)


def _entropy(counts: dict[int, float]) -> tuple[float, float]:
    total = float(sum(counts.values()))
    if total <= 0.0 or not counts:
        return 0.0, 0.0
    probabilities = [value / total for value in counts.values() if value > 0.0]
    entropy = -sum(p * math.log2(p) for p in probabilities)
    return entropy, max(probabilities)


@dataclass
class FeatureTable:
    rows: list[IntervalFeatures] = field(default_factory=list)
    schema_version: int = FEATURE_SCHEMA_VERSION

    def __len__(self) -> int:
        return len(self.rows)

    def __iter__(self):
        return iter(self.rows)

    @classmethod
    def from_bbv(cls, bbv) -> FeatureTable:
        rows = []
        for interval_id, counts in zip(bbv.interval_ids, bbv.intervals, strict=True):
            entropy, top_share = _entropy(counts)
            rows.append(
                IntervalFeatures(
                    interval=int(interval_id),
                    instructions=int(round(float(sum(counts.values())))),
                    num_blocks=len(counts),
                    bbv_entropy=entropy,
                    top_block_share=top_share,
                )
            )
        return cls(rows=rows)

    def merge_summary(self, summary: dict[int, dict[str, Any]]) -> FeatureTable:
        """Merge per-interval summary fields keyed by interval id.

        Unknown intervals raise ``KeyError`` so that misaligned profilers fail
        loudly instead of silently producing a corrupt feature table.
        """
        index = {row.interval: row for row in self.rows}
        for interval, values in summary.items():
            if interval not in index:
                raise KeyError(f"summary interval {interval} not present in BBV")
            row = index[interval]
            for key, value in values.items():
                if key == "interval":
                    continue
                if not hasattr(row, key):
                    row.extras[key] = float(value)
                else:
                    setattr(row, key, value)
        return self

    def validate(self) -> None:
        previous = None
        for row in self.rows:
            if previous is not None and row.interval <= previous:
                raise ValueError(
                    f"intervals must be strictly increasing: {previous} -> {row.interval}"
                )
            previous = row.interval
            if row.instructions < 0:
                raise ValueError(f"negative instruction count at interval {row.interval}")
            if row.num_blocks < 0:
                raise ValueError(f"negative block count at interval {row.interval}")
            if row.bbv_entropy < 0.0:
                raise ValueError(f"negative entropy at interval {row.interval}")
            if not 0.0 <= row.top_block_share <= 1.0:
                raise ValueError(f"top_block_share out of range at {row.interval}")
            if row.opcode_mix:
                if any(value < 0.0 for value in row.opcode_mix.values()):
                    raise ValueError(f"negative opcode share at {row.interval}")
                total = sum(row.opcode_mix.values())
                if abs(total - 1.0) > 1e-3:
                    raise ValueError(
                        f"opcode_mix must sum to 1 at interval {row.interval}: {total}"
                    )
            if row.loads < 0 or row.stores < 0:
                raise ValueError(f"negative memory count at {row.interval}")

    def to_jsonl(self, path: str | Path) -> None:
        self.validate()
        with Path(path).open("w", encoding="utf-8") as handle:
            for row in self.rows:
                handle.write(json.dumps(row.to_dict(), sort_keys=True) + "\n")

    @classmethod
    def from_jsonl(cls, path: str | Path) -> FeatureTable:
        rows = []
        with Path(path).open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    rows.append(IntervalFeatures.from_dict(json.loads(line)))
        table = cls(rows=rows)
        table.validate()
        return table

    def to_parquet(self, path: str | Path) -> None:
        import pyarrow as pa
        import pyarrow.parquet as pq

        self.validate()
        records = [_flatten_row(row) for row in self.rows]
        pq.write_table(pa.Table.from_pylist(records), path)

    @classmethod
    def from_parquet(cls, path: str | Path) -> FeatureTable:
        import pyarrow.parquet as pq

        table = pq.read_table(path)
        rows = [IntervalFeatures.from_dict(_unflatten_row(record)) for record in table.to_pylist()]
        result = cls(rows=rows)
        result.validate()
        return result


def _flatten_row(row: IntervalFeatures) -> dict[str, Any]:
    record = row.to_dict()
    for key in ("opcode_mix", "stride_hist", "extras"):
        record[key] = json.dumps(record[key], sort_keys=True)
    return record


def _unflatten_row(record: dict[str, Any]) -> dict[str, Any]:
    record = dict(record)
    for key in ("opcode_mix", "stride_hist", "extras"):
        value = record.get(key)
        if isinstance(value, str):
            record[key] = json.loads(value) if value else {}
    return record
