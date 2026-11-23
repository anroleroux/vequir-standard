"""Wiring schematics: schematic.json beside product.md, drawn on the product's page."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cad.catalog import build_catalog
from cad.schematic import UNIT, check, load, render, route

PLATE = '"""A plate."""\nimport cadquery as cq\nresult = cq.Workplane("XY").box(10, 10, 2)\nregions = {}\n'

LAMP = {
    "title": "Wiring",
    "components": [
        {"ref": "BT1", "name": "Cell", "x": 0, "y": 0, "symbol": "cell",
         "pins": {"left": ["+"], "right": ["-"]}},
        {"ref": "D1", "name": "LED <red>", "item": "plate", "x": 20, "y": 0, "symbol": "diode",
         "pins": {"left": ["A:1"], "right": ["K:2"]}, "modelled": False},
        {"ref": "U1", "name": "MCU", "x": 0, "y": 12, "pins": {"right": ["GP0"], "top": ["VCC"]}},
    ],
    "nets": [
        {"name": "V+", "kind": "power", "pins": ["BT1.+", "D1.A"]},
        {"name": "GND", "kind": "ground", "pins": ["BT1.-", "D1.K"]},
    ],
}


def test_a_schematic_draws_every_part_pin_and_net():
    out = render(LAMP)
    assert out.count('class="comp') == 3 and out.count('class="comp off-model"') == 1
    assert out.count('class="wire net k-power" data-net="V+"') == 1  # one wire joins its pins
    assert 'class=nc' in out  # U1's two pins are on no net
    assert "LED &lt;red&gt;" in out  # escaped
    data = json.loads(out.split("class=sch-data>")[1].split("</script>")[0])
    assert data["nets"]["GND"]["pins"] == ["BT1.-", "D1.K"]
    assert data["comps"]["D1"]["pins"][0] == {"pin": "A", "number": "1", "net": "V+"}


def _star(n_pins: int, kind: str = "signal") -> dict:
    """A hub part with a net to each of four spokes, and one net across all."""
    comps = [{"ref": "H", "x": 20, "y": 20, "pins": {"left": ["A", "B"], "right": ["C", "D"]}}]
    for i, (x, y) in enumerate([(0, 0), (40, 0), (0, 40), (40, 40)]):
        comps.append({"ref": f"S{i}", "x": x, "y": y, "pins": {"right": ["P", "Q"], "left": ["R"]}})
    nets = [{"name": f"N{i}", "pins": [f"S{i}.P", "H." + "ABCD"[i]]} for i in range(4)]
    nets.append({"name": "BUS", "kind": kind, "pins": [f"S{i}.Q" for i in range(n_pins)]})
    return {"components": comps, "nets": nets}


def test_wires_never_share_a_run_with_another_net():
    """Two nets may cross, but never run along the same grid step."""
    data = _star(4)
    routes = route(data)
    assert all(not r["failed"] for r in routes.values())
    steps = {}
    for name, r in routes.items():
        for path in r["paths"]:
            for (x0, y0), (x1, y1) in zip(path, path[1:]):
                for t in range(int(abs(x1 - x0) + abs(y1 - y0)) // UNIT):
                    sx, sy = (x1 > x0) - (x1 < x0), (y1 > y0) - (y1 < y0)
                    a = (x0 + sx * t * UNIT, y0 + sy * t * UNIT)
                    step = frozenset([a, (a[0] + sx * UNIT, a[1] + sy * UNIT)])
                    assert steps.setdefault(step, name) == name, f"{name} runs along {steps[step]}"
    assert routes["BUS"]["dots"]  # four pins on one net: joints, each with a dot


def test_a_big_ground_net_is_drawn_as_symbols():
    out = render(_star(4, "ground"))
    assert out.count('class="gnd k-ground"') == 4 and 'data-net="BUS" tabindex' not in out


def test_a_pin_the_router_cannot_reach_gets_a_label():
    data = _star(2)
    data["components"].append({"ref": "W", "x": -3, "y": -3, "w": 30, "h": 12, "pins": {}})  # over S0
    data["components"][1]["x"] = 1  # S0 boxed in by W: its stubs end inside W
    out = render(data)
    assert 'class="net k-signal" data-net="N0"' in out  # the label in its place


def test_a_part_links_to_its_page():
    out = render(LAMP, {"plate": "products/L1/plate/index.html"}, "../../")
    data = json.loads(out.split("class=sch-data>")[1].split("</script>")[0])
    assert data["comps"]["D1"]["href"] == "../../products/L1/plate/index.html"
    assert data["comps"]["BT1"]["href"] == ""


@pytest.mark.parametrize("change, message", [
    (lambda d: d["nets"][0]["pins"].append("D1.X"), "no pin 'D1.X'"),
    (lambda d: d["nets"][1]["pins"].append("BT1.+"), "on two nets"),
    (lambda d: d["components"][1].update(ref="BT1"), "unique ref"),
    (lambda d: d["nets"][0].update(kind="mains"), "kind is one of"),
    (lambda d: d["components"][0].update(symbol="valve"), "unknown symbol"),
])
def test_a_broken_schematic_is_refused(change, message):
    data = json.loads(json.dumps(LAMP))
    change(data)
    with pytest.raises(ValueError, match=message):
        check(data)


def test_the_product_page_shows_its_schematic(tmp_path):
    root = tmp_path / "products"
    (root / "L1" / "plate").mkdir(parents=True)
    (root / "L1" / "plate" / "part.py").write_text(PLATE)
    (root / "L1" / "product.md").write_text("# L1\n\nA lamp.\n")
    (root / "L1" / "assembly.py").write_text(
        '"""L1, assembled."""\nimport cadquery as cq\nplate = load_part("plate")\n'
        'result = cq.Assembly(name="L1").add(plate.result, name="plate")\nregions = {}\n')
    (root / "L1" / SCHEMATIC_NAME).write_text(json.dumps(LAMP))
    index, failures = build_catalog(root, tmp_path / "results", tmp_path / "site", log=lambda _: None)
    assert failures == []
    page = (tmp_path / "site" / "products" / "L1" / "index.html").read_text()
    assert "<section class=schematic" in page and "sch-svg" in page
    data = json.loads(page.split("class=sch-data>")[1].split("</script>")[0])
    assert data["comps"]["D1"]["href"] == "../../products/L1/plate/index.html"  # the placed part's page


def test_a_broken_schematic_json_names_its_file(tmp_path):
    path = tmp_path / "schematic.json"
    path.write_text("{")
    with pytest.raises(ValueError, match="schematic.json: not valid JSON"):
        load(path)


SCHEMATIC_NAME = "schematic.json"
