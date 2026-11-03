"""JSON schemas exchanged between pipeline stages."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "Manifest",
    "PhaseSpec",
    "ProxySpec",
    "SimPoint",
    "SimPointResult",
]


@dataclass
class SimPoint:
    cluster: int
    interval: int
    weight: float
    start_pc: int | None = None


@dataclass
class SimPointResult:
    source: str
    interval_instructions: int
    num_intervals: int
    k: int
    bic: float
    simpoints: list[SimPoint] = field(default_factory=list)
    trials: list[dict[str, Any]] = field(default_factory=list)
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SimPointResult:
        return cls(
            source=data["source"],
            interval_instructions=int(data["interval_instructions"]),
            num_intervals=int(data["num_intervals"]),
            k=int(data["k"]),
            bic=float(data["bic"]),
            simpoints=[SimPoint(**sp) for sp in data.get("simpoints", [])],
            trials=list(data.get("trials", [])),
            version=int(data.get("version", 1)),
        )

    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def from_json(cls, path: str | Path) -> SimPointResult:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


@dataclass
class PhaseSpec:
    cluster: int
    interval: int
    weight: float
    instructions: int
    kernel: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProxySpec:
    source: str
    total_instructions: int
    interval_instructions: int
    phases: list[PhaseSpec] = field(default_factory=list)
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProxySpec:
        return cls(
            source=data["source"],
            total_instructions=int(data["total_instructions"]),
            interval_instructions=int(data["interval_instructions"]),
            phases=[PhaseSpec(**phase) for phase in data.get("phases", [])],
            version=int(data.get("version", 1)),
        )

    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def from_json(cls, path: str | Path) -> ProxySpec:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


@dataclass
class Manifest:
    proxy: str
    source: str
    total_instructions: int
    phases: list[PhaseSpec] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def from_json(cls, path: str | Path) -> Manifest:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            proxy=data["proxy"],
            source=data["source"],
            total_instructions=int(data["total_instructions"]),
            phases=[PhaseSpec(**phase) for phase in data.get("phases", [])],
            metrics=dict(data.get("metrics", {})),
            version=int(data.get("version", 1)),
        )
