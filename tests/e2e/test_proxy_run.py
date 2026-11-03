from __future__ import annotations

import json
import shutil
import subprocess

import pytest
from simproxy.cli import main
from simproxy.formats.schema import SimPoint, SimPointResult
from simproxy.profiler import FeatureTable, IntervalFeatures
from simproxy.synth import build_proxy, emit_c, plan_kernel

CC = shutil.which("aarch64-linux-gnu-gcc")
QEMU = shutil.which("qemu-aarch64-static")

pytestmark = pytest.mark.skipif(
    not CC or not QEMU,
    reason="requires aarch64-linux-gnu-gcc and qemu-aarch64-static",
)


def test_emit_build_and_run(tmp_path):
    features = FeatureTable(
        rows=[
            IntervalFeatures(
                interval=0,
                instructions=1000,
                loads=250,
                stores=100,
                working_set_bytes=1 << 16,
            )
        ]
    )
    plans = [plan_kernel(0, 1000, features.rows[0])]
    source = emit_c(plans, 1000, "synthetic")
    build = build_proxy(source, tmp_path / "proxy.elf", compiler=CC, keep_source=True)

    completed = subprocess.run(
        [QEMU, str(build.elf)], capture_output=True, text=True
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["logical_instructions"] == 1000
    assert payload["phases"] == 1


def test_cli_synth_emits_manifest(tmp_path):
    simpoints = SimPointResult(
        source="synthetic",
        interval_instructions=1000,
        num_intervals=4,
        k=2,
        bic=1.0,
        simpoints=[
            SimPoint(cluster=0, interval=0, weight=0.5),
            SimPoint(cluster=1, interval=2, weight=0.5),
        ],
    )
    simpoints_path = tmp_path / "simpoints.json"
    simpoints.to_json(simpoints_path)

    features = FeatureTable(
        rows=[
            IntervalFeatures(interval=0, instructions=1000, loads=250),
            IntervalFeatures(interval=2, instructions=1000, stores=300),
        ]
    )
    features_path = tmp_path / "features.jsonl"
    features.to_jsonl(features_path)

    elf_path = tmp_path / "proxy.elf"
    spec_path = tmp_path / "proxy_spec.json"
    manifest_path = tmp_path / "manifest.json"
    assert (
        main(
            [
                "synth",
                "-i",
                str(simpoints_path),
                "-o",
                str(spec_path),
                "--features",
                str(features_path),
                "--emit-elf",
                str(elf_path),
                "--manifest",
                str(manifest_path),
                "--cc",
                CC,
            ]
        )
        == 0
    )
    assert elf_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["metrics"]["backend"] == "statistical-kernel"
    assert len(manifest["phases"]) == 2
