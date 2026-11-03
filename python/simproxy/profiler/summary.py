"""Adapters for per-interval summary streams produced by profilers.

The canonical summary is JSON Lines, one object per interval::

    {"interval": 0, "loads": 1200, "stores": 400, "opcode_mix": {"alu": 0.7}}

A simple CSV opcode-mix form is also supported::

    interval,opcode_class,count
    0,alu,7000
    0,load,2000
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

__all__ = [
    "read_jsonl",
    "read_opcode_mix_csv",
    "merge_summaries",
]


def read_jsonl(path: str | Path) -> dict[int, dict[str, Any]]:
    summary: dict[int, dict[str, Any]] = {}
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if "interval" not in record:
                raise ValueError("summary record is missing 'interval'")
            summary[int(record["interval"])] = record
    return summary


def read_opcode_mix_csv(path: str | Path) -> dict[int, dict[str, Any]]:
    counts: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"interval", "opcode_class", "count"}
        if not required.issubset(reader.fieldnames or set()):
            raise ValueError(f"opcode mix CSV must have columns {sorted(required)}")
        for row in reader:
            interval = int(row["interval"])
            counts[interval][row["opcode_class"]] += float(row["count"])

    summary: dict[int, dict[str, Any]] = {}
    for interval, mix in counts.items():
        total = sum(mix.values())
        if total <= 0.0:
            continue
        summary[interval] = {
            "interval": interval,
            "opcode_mix": {name: value / total for name, value in mix.items()},
        }
    return summary


def merge_summaries(
    *summaries: dict[int, dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    merged: dict[int, dict[str, Any]] = {}
    for summary in summaries:
        for interval, values in summary.items():
            merged.setdefault(interval, {"interval": interval}).update(values)
    return merged
