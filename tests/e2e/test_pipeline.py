from __future__ import annotations

import json

from simproxy.cli import main
from simproxy.formats.bbv import parse_bbv

SAMPLE = """\
T0: 1:100 2:50 3:20
T1: 1:95 2:55 3:18
T2: 4:200 5:100
T3: 4:190 5:110
T4: 1:90 2:60 3:22
T5: 4:210 5:95
"""


def test_simpoint_then_synth(tmp_path):
    bbv_path = tmp_path / "prog.bbv"
    bbv_path.write_text(SAMPLE, encoding="utf-8")
    simpoints_path = tmp_path / "simpoints.json"
    spec_path = tmp_path / "proxy_spec.json"

    assert (
        main(
            [
                "simpoint",
                "-i",
                str(bbv_path),
                "-o",
                str(simpoints_path),
                "--interval-instructions",
                "100000000",
                "--k-min",
                "1",
                "--k-max",
                "4",
                "--projection-dim",
                "3",
            ]
        )
        == 0
    )

    simpoints = json.loads(simpoints_path.read_text(encoding="utf-8"))
    assert simpoints["num_intervals"] == len(parse_bbv(bbv_path))
    assert sum(point["weight"] for point in simpoints["simpoints"]) == 1.0
    assert len(simpoints["simpoints"]) == simpoints["k"]

    assert main(["synth", "-i", str(simpoints_path), "-o", str(spec_path)]) == 0
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    assert spec["total_instructions"] == 600_000_000
    assert sum(phase["instructions"] for phase in spec["phases"]) == 600_000_000


def test_profile_and_validate(tmp_path):
    bbv_path = tmp_path / "prog.bbv"
    bbv_path.write_text(SAMPLE, encoding="utf-8")
    features_path = tmp_path / "features.jsonl"
    mix_path = tmp_path / "mix.csv"
    mix_path.write_text(
        "interval,opcode_class,count\n0,alu,3\n0,load,1\n", encoding="utf-8"
    )

    assert (
        main(
            [
                "profile",
                "-i",
                str(bbv_path),
                "-o",
                str(features_path),
                "--opcode-csv",
                str(mix_path),
            ]
        )
        == 0
    )
    rows = [
        json.loads(line)
        for line in features_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert len(rows) == 6
    assert rows[0]["interval"] == 0
    assert rows[0]["instructions"] == 170
    assert rows[0]["opcode_mix"] == {"alu": 0.75, "load": 0.25}
    assert main(["features", "validate", "-i", str(features_path)]) == 0


def test_bbv_merge_and_normalize(tmp_path):
    left = tmp_path / "a.bbv"
    right = tmp_path / "b.bbv"
    left.write_text("T0: 1:1 2:3\n", encoding="utf-8")
    right.write_text("T1: 2:1 3:1\n", encoding="utf-8")
    merged = tmp_path / "merged.bbv"
    normalized = tmp_path / "normalized.bbv"

    assert main(["bbv", "merge", str(left), str(right), "-o", str(merged)]) == 0
    assert len(parse_bbv(merged)) == 2

    assert main(["bbv", "normalize", str(merged), "-o", str(normalized)]) == 0
    bbv = parse_bbv(normalized)
    for counts in bbv:
        assert abs(sum(counts.values()) - 1.0) < 1e-9
