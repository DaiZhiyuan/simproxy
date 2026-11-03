from __future__ import annotations

import gzip

import numpy as np
import pytest
from simproxy.formats.bbv import (
    BBV,
    concat_bbv,
    normalize_counts,
    parse_bbv,
    to_matrix,
    write_bbv,
)

DRPOINTS_TEXT = "T:1:12 :3:7 :8:1 \nT:2:5 :3:9 \n"
SIMPOINT_TEXT = "T0: 1:12 3:7 8:1\nT1: 2:5 3:9\n"


@pytest.mark.parametrize("text", [DRPOINTS_TEXT, SIMPOINT_TEXT])
def test_parse_both_dialects(tmp_path, text):
    path = tmp_path / "sample.bbv"
    path.write_text(text, encoding="utf-8")
    bbv = parse_bbv(path)
    assert len(bbv) == 2
    assert bbv.intervals[0] == {1: 12.0, 3: 7.0, 8: 1.0}
    assert bbv.intervals[1] == {2: 5.0, 3: 9.0}
    assert bbv.interval_ids == [0, 1]


def test_roundtrip(tmp_path):
    bbv = BBV()
    bbv.append({1: 12, 3: 7}, interval_id=0)
    bbv.append({2: 5, 3: 9}, interval_id=1)
    path = tmp_path / "out.bbv"
    write_bbv(path, bbv)
    reparsed = parse_bbv(path)
    assert reparsed.intervals == [{1: 12.0, 3: 7.0}, {2: 5.0, 3: 9.0}]
    assert reparsed.interval_ids == [0, 1]


def test_gzip_roundtrip(tmp_path):
    path = tmp_path / "out.bbv.gz"
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        fh.write(DRPOINTS_TEXT)
    bbv = parse_bbv(path)
    assert len(bbv) == 2
    out = tmp_path / "copy.bbv.gz"
    write_bbv(out, bbv)
    assert len(parse_bbv(out)) == 2


def test_normalize():
    counts = normalize_counts({1: 2, 2: 6})
    assert counts == {1: 0.25, 2: 0.75}
    assert normalize_counts({}) == {}


def test_to_matrix():
    bbv = BBV()
    bbv.append({1: 1, 2: 3})
    bbv.append({2: 2, 3: 2})
    bbids, matrix = to_matrix(bbv, normalize=True)
    assert bbids.tolist() == [1, 2, 3]
    assert matrix.shape == (2, 3)
    np.testing.assert_allclose(matrix[0], [0.25, 0.75, 0.0])
    np.testing.assert_allclose(matrix[1], [0.0, 0.5, 0.5])


def test_concat():
    a = BBV()
    a.append({1: 1}, interval_id=0)
    b = BBV()
    b.append({2: 2}, interval_id=1)
    merged = concat_bbv([a, b])
    assert len(merged) == 2
    assert merged.total_instructions() == 3.0


def test_malformed_line(tmp_path):
    path = tmp_path / "bad.bbv"
    path.write_text("T0: 1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_bbv(path)
