"""The parts library: reusable parts and assemblies, by category, placed with load_library."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from neobotics.catalog import build_catalog, discover_all, find, used_in
from neobotics.part import build_part, library_roots

PLATE = """\
\"\"\"Plate.\"\"\"
import cadquery as cq

l, b, t = 20.0, 10.0, 2.0
result = cq.Workplane("XY").box(l, b, t, centered=(True, True, False))
"""
PIN = """\
\"\"\"Pin.\"\"\"
import cadquery as cq

plate = load_part("../plate")
result = cq.Workplane("XY").circle(1.0).extrude(5.0)
"""
CLIP = """\
\"\"\"Clip.\"\"\"
import cadquery as cq

plate, pin = load_part("plate"), load_part("pin")
result = (cq.Assembly(name="clip")
          .add(plate.result, name="plate")
          .add(pin.result, name="pin", loc=cq.Location((0, 0, plate.t))))
"""
# a product part, two levels down, that stands a library assembly on itself
USER = """\
\"\"\"Bracket with a clip.\"\"\"
import cadquery as cq

clip = load_library("fasteners/clip")
plate = load_library("fasteners/clip/plate")
result = cq.Workplane("XY").box(plate.l, plate.b, 3.0, centered=(True, True, False))
"""


def _write(path: Path, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)


def _tree(root: Path) -> Path:
    """A products tree and a library beside it; returns the products root."""
    clip = root / "library" / "fasteners" / "clip"
    _write(clip / "plate" / "part.py", PLATE)
    _write(clip / "pin" / "part.py", PIN)
    _write(clip / "assembly.py", CLIP)
    _write(root / "library" / "fasteners" / "category.md", "# Fasteners\n\nClips and pins.\n")
    _write(root / "products" / "P1" / "frame" / "bracket" / "part.py", USER)
    return root / "products"


def _summary(result):
    assert result.ok, result.error
    return json.loads(result.files["summary"].read_text())


def test_load_library_finds_the_library_above_the_script(tmp_path):
    products = _tree(tmp_path)
    summary = _summary(build_part(products / "P1/frame/bracket/part.py", tmp_path / "out"))
    assert summary["bounding_box"]["size"] == pytest.approx([20, 10, 3])


def test_load_library_names_what_is_missing(tmp_path, monkeypatch):
    products = _tree(tmp_path / "repo")
    _write(products / "P1" / "frame" / "other" / "part.py", 'x = load_library("fasteners/nut")\n')
    result = build_part(products / "P1/frame/other/part.py", tmp_path / "out")
    assert not result.ok and "load_library('fasteners/nut'): no part.py or assembly.py" in result.error
    # no library/ above the script, and none named: say how to point at one
    _write(tmp_path / "loose" / "part.py", 'x = load_library("fasteners/clip")\n')
    monkeypatch.delenv("NEOBOTICS_LIBRARY", raising=False)
    result = build_part(tmp_path / "loose" / "part.py", tmp_path / "out2")
    assert not result.ok and "NEOBOTICS_LIBRARY" in result.error


def test_the_library_can_live_anywhere(tmp_path, monkeypatch):
    _tree(tmp_path / "repo")
    _write(tmp_path / "elsewhere" / "part.py", USER)
    monkeypatch.setenv("NEOBOTICS_LIBRARY", str(tmp_path / "repo" / "library"))
    assert build_part(tmp_path / "elsewhere" / "part.py", tmp_path / "out").ok


def test_catalog_reads_the_library_beside_the_products(tmp_path):
    products = _tree(tmp_path)
    entries = discover_all(products)
    assert [e.address for e in entries] == [
        "P1/frame/bracket",
        "library/fasteners/clip", "library/fasteners/clip/pin", "library/fasteners/clip/plate"]
    entry = find(products, "library/fasteners/clip/pin")
    assert entry.designation == "fasteners/clip/pin"
    assert entry.out_dir(tmp_path / "r") == tmp_path / "r/library/fasteners/clip/pin"
    assert find(products, "library/fasteners/clip").out_dir(tmp_path / "r") == \
        tmp_path / "r/library/fasteners/clip/_assembly"
    assert used_in(entries) == {"fasteners/clip": ["P1/frame/bracket"],
                                "fasteners/clip/plate": ["P1/frame/bracket"]}


def test_site_publishes_the_library_with_its_uses(tmp_path):
    products = _tree(tmp_path)
    index, failures = build_catalog(products, tmp_path / "results", tmp_path / "site",
                                    log=lambda _: None)
    assert not failures
    site = tmp_path / "site"
    overview = index.read_text()
    assert "Parts library" in overview and 'href="library/fasteners/index.html"' in overview
    # the overview's category cards are text only; the library's own page keeps the pictures
    library_part = overview[overview.index("Parts library"):]
    assert "class=thumb" not in library_part and 'src="library/' not in library_part
    library = (site / "library/index.html").read_text()
    assert 'href="../library/fasteners/index.html"' in library and "Fasteners" in library
    assert 'src="../library/fasteners/clip/_assembly/part.png"' in library
    category = (site / "library/fasteners/index.html").read_text()
    assert "Category" in category and 'href="clip/index.html"' in category
    assert 'href="../../library/index.html">Parts library</a>' in category  # the breadcrumb
    clip = (site / "library/fasteners/clip/index.html").read_text()
    assert "Library assembly" in clip and "Assembled model" in clip
    assert "load_library(&quot;fasteners/clip&quot;)" in clip
    # who places it, linked from the site root
    assert 'href="../../../products/P1/frame/bracket/index.html"' in clip
    pin = (site / "library/fasteners/clip/pin/index.html").read_text()
    assert "Library part" in pin and "Not placed in any product yet" in pin
    assert (site / "products/P1/frame/bracket/index.html").exists()


# ---- libraries in other repositories -----------------------------------------
STRAP = """\
\"\"\"Strap round a clip.\"\"\"
import cadquery as cq

plate = load_library("fasteners/clip/plate")  # from the other repository's library
result = cq.Workplane("XY").box(plate.l + 4, plate.b, 1.0, centered=(True, True, False))
"""


def _repos(tmp_path: Path) -> tuple[Path, Path]:
    """Two repositories side by side: ``standard`` holds the clip in its
    library; ``power`` holds a strap in its own library and a product that
    uses both, finding ``standard``'s library through ``libraries.txt``."""
    _tree(tmp_path / "standard")
    power = tmp_path / "power"
    _write(power / "library" / "straps" / "strap" / "part.py", STRAP)
    _write(power / "products" / "P2" / "frame" / "mount" / "part.py",
           USER.replace("import cadquery as cq\n",
                        'import cadquery as cq\n\nstrap = load_library("straps/strap")\n'))
    _write(power / "libraries.txt", "# beside this repository\n../standard/library\n\n")
    return tmp_path / "standard", power


def test_libraries_txt_names_other_repositories_libraries(tmp_path, monkeypatch):
    monkeypatch.delenv("NEOBOTICS_LIBRARY", raising=False)
    standard, power = _repos(tmp_path)
    # its own library first, then the listed ones, from any depth
    assert library_roots(power / "products" / "P2" / "frame" / "mount") == [
        power / "library", standard / "library"]
    assert library_roots(power / "library" / "straps" / "strap") == [
        power / "library", standard / "library"]
    # a product part using its own library's strap, which uses the other library's plate
    summary = _summary(build_part(power / "products/P2/frame/mount/part.py", tmp_path / "out"))
    assert summary["bounding_box"]["size"] == pytest.approx([20.0, 10.0, 3.0])
    assert build_part(power / "library/straps/strap/part.py", tmp_path / "strap").ok


def test_the_environment_list_is_searched_first(tmp_path, monkeypatch):
    standard, power = _repos(tmp_path)
    elsewhere = tmp_path / "elsewhere" / "library"
    _write(elsewhere / "fasteners" / "clip" / "plate" / "part.py", PLATE.replace("20.0", "30.0"))
    monkeypatch.setenv("NEOBOTICS_LIBRARY", os.pathsep.join([str(elsewhere), str(tmp_path / "nope")]))
    assert library_roots(power / "library") == [
        elsewhere, power / "library", standard / "library"]  # missing ones left out
    summary = _summary(build_part(power / "library/straps/strap/part.py", tmp_path / "out"))
    assert summary["bounding_box"]["size"][0] == pytest.approx(34.0)  # the first plate found


def test_a_missing_item_names_every_library_searched(tmp_path, monkeypatch):
    monkeypatch.delenv("NEOBOTICS_LIBRARY", raising=False)
    standard, power = _repos(tmp_path)
    _write(power / "library" / "straps" / "bad" / "part.py", 'x = load_library("fasteners/nut")\n')
    result = build_part(power / "library/straps/bad/part.py", tmp_path / "out")
    assert not result.ok
    assert str(power / "library") in result.error and str(standard / "library") in result.error


def test_a_library_only_repository_builds_its_site(tmp_path, monkeypatch):
    """No products/: the overview is the library, with pictures, under the
    title and lede from site.md."""
    monkeypatch.delenv("NEOBOTICS_LIBRARY", raising=False)
    standard, _ = _repos(tmp_path)
    shutil.rmtree(standard / "products")
    _write(standard / "site.md", "# Acme Standard <parts>\n\nClips & pins.\n")
    index, failures = build_catalog(standard / "products", tmp_path / "results",
                                    tmp_path / "site", log=lambda _: None)
    assert not failures
    overview = index.read_text()
    assert "<h1>Acme Standard &lt;parts&gt;</h1>" in overview and "Clips &amp; pins." in overview
    assert "<h2>Products" not in overview
    assert 'src="library/fasteners/clip/_assembly/part.png"' in overview  # pictured
    clip = (tmp_path / "site/library/fasteners/clip/index.html").read_text()
    assert "<title>Clip · Acme Standard &lt;parts&gt;</title>" in clip
    assert ">Acme Standard &lt;parts&gt;</a>" in clip  # the breadcrumb's root
    with pytest.raises(FileNotFoundError):
        discover_all(tmp_path / "nothing" / "products")
