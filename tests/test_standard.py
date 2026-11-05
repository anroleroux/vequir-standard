"""The standard parts: built and checked against their nominal sizes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cad.catalog import discover_all
from cad.part import build_part

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "library"


def _summary(result):
    assert result.ok, result.error
    return json.loads(result.files["summary"].read_text())


def test_the_library_holds_the_standard_parts():
    assert sorted(e.designation for e in discover_all(ROOT / "products")) == [
        "batteries/cell_18650", "fasteners/m1_2x3_countersunk", "fasteners/m1_2x6_countersunk",
        "terminals/keystone_1107_1"]


def test_the_18650_cell_is_18_4_by_65_standing_up(tmp_path):
    cell = _summary(build_part(LIBRARY / "batteries/cell_18650/part.py", tmp_path / "out"))
    assert cell["bounding_box"]["size"] == pytest.approx([18.4, 18.4, 65.0])
    assert cell["bounding_box"]["min"][2] == pytest.approx(0)  # negative end on z = 0


def test_the_m1_2_screw_is_6_long_with_a_2_3_head(tmp_path):
    screw = _summary(build_part(LIBRARY / "fasteners/m1_2x6_countersunk/part.py", tmp_path / "out"))
    assert screw["bounding_box"]["size"][1:] == pytest.approx([2.3, 6.0])  # head across, length


def test_the_short_m1_2_screw_is_3_long_with_the_same_head(tmp_path):
    screw = _summary(build_part(LIBRARY / "fasteners/m1_2x3_countersunk/part.py", tmp_path / "out"))
    assert screw["bounding_box"]["size"][1:] == pytest.approx([2.3, 3.0])  # head across, length


def test_the_keystone_1107_1_clip_is_a_quarter_inch_wide(tmp_path):
    clip = _summary(build_part(LIBRARY / "terminals/keystone_1107_1/part.py", tmp_path / "out"))
    assert clip["bounding_box"]["size"][1:] == pytest.approx([6.35, 13.7])  # 0.250 in, 0.538 in
