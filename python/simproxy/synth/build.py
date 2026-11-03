"""Compile generated kernels into a native (cross-)target executable."""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

__all__ = ["BuildError", "BuildResult", "build_proxy"]


class BuildError(RuntimeError):
    pass


@dataclass
class BuildResult:
    elf: Path
    source: Path
    compiler: str
    elf_sha256: str
    source_sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_proxy(
    c_source: str,
    output: str | Path,
    compiler: str = "aarch64-linux-gnu-gcc",
    keep_source: bool = False,
) -> BuildResult:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    if keep_source:
        source = output.with_suffix(".c")
        source.write_text(c_source, encoding="utf-8")
        temp = None
    else:
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".c", delete=False, encoding="utf-8"
        )
        handle.write(c_source)
        handle.close()
        source = Path(handle.name)
        temp = source

    try:
        command = [
            compiler,
            "-O2",
            "-static",
            "-std=c11",
            "-o",
            str(output),
            str(source),
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            raise BuildError(
                f"compiler failed ({completed.returncode}):\n{completed.stderr.strip()}"
            )
        result = BuildResult(
            elf=output,
            source=source,
            compiler=compiler,
            elf_sha256=_sha256(output),
            source_sha256=hashlib.sha256(c_source.encode("utf-8")).hexdigest(),
        )
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)

    return result
