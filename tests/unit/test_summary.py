from __future__ import annotations

from simproxy.profiler import merge_summaries, read_jsonl, read_opcode_mix_csv


def test_read_jsonl(tmp_path):
    path = tmp_path / "summary.jsonl"
    path.write_text(
        '{"interval": 0, "loads": 3}\n{"interval": 1, "stores": 4}\n',
        encoding="utf-8",
    )
    summary = read_jsonl(path)
    assert summary[0]["loads"] == 3
    assert summary[1]["stores"] == 4


def test_read_opcode_mix_csv_normalizes(tmp_path):
    path = tmp_path / "mix.csv"
    path.write_text(
        "interval,opcode_class,count\n0,alu,70\n0,load,30\n1,alu,1\n",
        encoding="utf-8",
    )
    summary = read_opcode_mix_csv(path)
    assert summary[0]["opcode_mix"] == {"alu": 0.7, "load": 0.3}
    assert summary[1]["opcode_mix"] == {"alu": 1.0}


def test_merge_summaries():
    merged = merge_summaries(
        {0: {"interval": 0, "loads": 1}},
        {0: {"interval": 0, "stores": 2}, 1: {"interval": 1, "loads": 3}},
    )
    assert merged[0]["loads"] == 1
    assert merged[0]["stores"] == 2
    assert merged[1]["loads"] == 3
