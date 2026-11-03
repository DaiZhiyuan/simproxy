"""Phase-kernel planning: turn interval features into executable operation counts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

__all__ = [
    "CATEGORIES",
    "DEFAULT_MIX",
    "KernelPlan",
    "normalize_mix",
    "plan_kernel",
]

CATEGORIES = ("alu", "mul", "fp", "simd", "load", "store", "branch")

DEFAULT_MIX = {
    "alu": 0.45,
    "mul": 0.10,
    "fp": 0.05,
    "simd": 0.00,
    "load": 0.25,
    "store": 0.10,
    "branch": 0.05,
}

_ALIASES = {
    "alu": "alu",
    "int": "alu",
    "integer": "alu",
    "add": "alu",
    "sub": "alu",
    "logic": "alu",
    "shift": "alu",
    "mul": "mul",
    "multiply": "mul",
    "fp": "fp",
    "float": "fp",
    "fpu": "fp",
    "fp32": "fp",
    "fp64": "fp",
    "simd": "simd",
    "neon": "simd",
    "vector": "simd",
    "load": "load",
    "loads": "load",
    "ldr": "load",
    "read": "load",
    "mem_read": "load",
    "store": "store",
    "stores": "store",
    "str": "store",
    "write": "store",
    "mem_write": "store",
    "branch": "branch",
    "branches": "branch",
    "br": "branch",
    "jump": "branch",
    "cbz": "branch",
}


def normalize_mix(opcode_mix: dict[str, float] | None) -> dict[str, float] | None:
    if not opcode_mix:
        return None
    totals = dict.fromkeys(CATEGORIES, 0.0)
    for name, value in opcode_mix.items():
        category = _ALIASES.get(name.lower(), "alu")
        totals[category] += max(float(value), 0.0)
    total = sum(totals.values())
    if total <= 0.0:
        return None
    return {category: value / total for category, value in totals.items()}


@dataclass
class KernelPlan:
    phase: int
    budget: int
    counts: dict[str, int] = field(default_factory=dict)
    array_bytes: int = 1 << 20
    branch_taken_percent: int = 50
    seed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _allocate(mix: dict[str, float], budget: int) -> dict[str, int]:
    counts = {category: int(round(mix.get(category, 0.0) * budget)) for category in CATEGORIES}
    remainder = budget - sum(counts.values())
    if remainder:
        target = max(CATEGORIES, key=lambda category: counts[category])
        counts[target] += remainder
    for category, value in counts.items():
        if value < 0:
            counts[category] = 0
    drift = budget - sum(counts.values())
    if drift:
        counts["alu"] += drift
    return counts


def plan_kernel(phase: int, budget: int, features=None, seed: int = 0) -> KernelPlan:
    budget = max(int(budget), 0)
    mix = normalize_mix(getattr(features, "opcode_mix", None))

    measured_memory = (
        features is not None and (features.loads + features.stores) > 0
    )
    if mix is None and measured_memory and features.instructions > 0:
        loads = max(features.loads, 0) / features.instructions
        stores = max(features.stores, 0) / features.instructions
        memory = min(loads + stores, 0.9)
        branch = 0.1 if memory <= 0.9 else 0.0
        mix = {
            "load": loads,
            "store": stores,
            "branch": branch,
            "alu": max(0.0, 1.0 - memory - branch),
        }

    if mix is None:
        mix = DEFAULT_MIX

    array_bytes = getattr(features, "working_set_bytes", 0) if features else 0
    if not array_bytes or array_bytes <= 0:
        array_bytes = 1 << 20
    array_bytes = min(max(int(array_bytes), 1 << 12), 64 << 20)
    array_bytes = 1 << (array_bytes - 1).bit_length()

    taken = getattr(features, "branch_taken_rate", 0.0) if features else 0.0
    taken_percent = int(round(min(max(taken, 0.0), 1.0) * 100))
    if taken_percent == 0:
        taken_percent = 50

    return KernelPlan(
        phase=int(phase),
        budget=budget,
        counts=_allocate(mix, budget),
        array_bytes=array_bytes,
        branch_taken_percent=taken_percent,
        seed=int(seed),
    )
