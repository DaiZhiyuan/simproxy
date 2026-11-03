from __future__ import annotations

import pytest
from simproxy.formats.bbv import BBV
from simproxy.profiler import FeatureTable, IntervalFeatures


def test_from_bbv_basic_statistics():
    bbv = BBV()
    bbv.append({1: 1, 2: 1}, interval_id=0)
    bbv.append({3: 10}, interval_id=1)

    table = FeatureTable.from_bbv(bbv)
    assert len(table) == 2

    first, second = table.rows
    assert first.instructions == 2
    assert first.num_blocks == 2
    assert first.bbv_entropy == pytest.approx(1.0)
    assert first.top_block_share == pytest.approx(0.5)

    assert second.instructions == 10
    assert second.bbv_entropy == 0.0
    assert second.top_block_share == pytest.approx(1.0)


def test_merge_summary_and_jsonl_roundtrip(tmp_path):
    bbv = BBV()
    bbv.append({1: 1, 2: 1}, interval_id=0)
    bbv.append({3: 10}, interval_id=1)
    table = FeatureTable.from_bbv(bbv)
    table.merge_summary(
        {
            0: {"loads": 5, "stores": 2, "opcode_mix": {"alu": 0.5, "load": 0.5}},
            1: {"branch_taken_rate": 0.25},
        }
    )
    table.validate()

    path = tmp_path / "features.jsonl"
    table.to_jsonl(path)
    restored = FeatureTable.from_jsonl(path)

    assert restored.rows[0].loads == 5
    assert restored.rows[0].opcode_mix == {"alu": 0.5, "load": 0.5}
    assert restored.rows[1].branch_taken_rate == 0.25


def test_unknown_interval_raises():
    table = FeatureTable(rows=[IntervalFeatures(interval=0, instructions=1)])
    with pytest.raises(KeyError):
        table.merge_summary({7: {"loads": 1}})


def test_validate_rejects_decreasing_intervals():
    table = FeatureTable(
        rows=[
            IntervalFeatures(interval=1, instructions=1),
            IntervalFeatures(interval=0, instructions=1),
        ]
    )
    with pytest.raises(ValueError, match="strictly increasing"):
        table.validate()


def test_validate_rejects_bad_opcode_mix():
    table = FeatureTable(
        rows=[
            IntervalFeatures(
                interval=0,
                instructions=1,
                opcode_mix={"alu": 0.5, "load": 0.4},
            )
        ]
    )
    with pytest.raises(ValueError, match="opcode_mix"):
        table.validate()


def test_parquet_roundtrip(tmp_path):
    pytest.importorskip("pyarrow")
    bbv = BBV()
    bbv.append({1: 3, 2: 7}, interval_id=0)
    table = FeatureTable.from_bbv(bbv)
    table.merge_summary({0: {"loads": 4, "opcode_mix": {"alu": 1.0}}})

    path = tmp_path / "features.parquet"
    table.to_parquet(path)
    restored = FeatureTable.from_parquet(path)
    assert restored.rows[0].loads == 4
    assert restored.rows[0].opcode_mix == {"alu": 1.0}
