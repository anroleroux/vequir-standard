"""Wiring schematics on the catalogue site: ``schematic.json`` beside a
product's ``product.md`` (or an assembly's ``assembly.md``).

The file describes the circuit as parts with pins, and nets joining pins.
The page draws each part as a box with its pins on its sides and routes
each net as wires between its pins, on a 10 px grid, round the parts: the
router (:func:`route`) runs when the site is built, so the page is a plain
SVG.  Wires cross only at right angles, never run along another net's wire,
and a dot marks every joint.  A big ground net is drawn as a ground symbol
at each of its pins instead, as schematics usually do; a net the router
cannot reach falls back to a coloured label at each pin.

The drawing sits in a frame that pans (drag) and zooms (wheel, pinch, or the
+ / - buttons), and it is interactive: pointing at (or tabbing to) a net
lights it up, and clicking a part or a net shows what it joins, with a link
to the part's own page.

    {
      "title": "Wiring",                      optional, the section's heading
      "note": "text under the heading",       optional
      "groups": [                             optional: a dashed frame round some parts
        {"label": "Load sharing", "x": 0, "y": 0, "w": 30, "h": 20, "note": "..."}
      ],
      "components": [
        {"ref": "U1", "name": "Pico 2 W",
         "item": "electronics/pico_2w",       optional: a library item (or a part's
                                              designation) an assembled model places;
                                              the part links to its page
         "x": 40, "y": 0,                     grid units (10 px), the box's top left
         "w": 16,                             optional, grid units; else from its text
         "symbol": "diode",                   optional: diode, resistor, capacitor,
                                              npn, pmos, cell
         "pins": {"left": ["VBUS:40", "VSYS:39"], "right": ["GP2:4"],
                  "top": [], "bottom": []},   each "NAME" or "NAME:number", in order
                                              down (left, right) or across (top, bottom)
         "note": "...", "modelled": true}     modelled: false for parts on the wires only
      ],
      "nets": [
        {"name": "VBUS", "kind": "power",     power, ground, signal or data
         "pins": ["J1.VBUS", "U1.VBUS"], "note": "...",
         "draw": "wire"}                      optional: wire, symbol or label; by default
                                              wire, but symbol for a ground net of more
                                              than three pins
      ]
    }

Leave room between parts for the wires: about 4 grid units between a box and
its neighbour's pins, more where many nets pass.

:func:`load` reads and checks a file; :func:`render` turns it into the
page's section (an inline SVG, a side panel and a small script, no
libraries).
"""

from __future__ import annotations

import heapq
import html
import json
from pathlib import Path

#: The file a product or assembly directory may hold.
SCHEMATIC = "schematic.json"
SIDES = ("left", "right", "top", "bottom")
KINDS = ("power", "ground", "signal", "data")
SYMBOLS = ("diode", "resistor", "capacitor", "npn", "pmos", "cell")
DRAWS = ("wire", "symbol", "label")

UNIT = 10  # px per grid unit: the routing grid
PITCH = 2 * UNIT  # between pins on a side
HEADER = 3 * UNIT  # the box's title band
STUB = 2 * UNIT  # a pin's line, out of the box
CHAR = 6.6  # px per character, 11 px monospace
LABEL_H = 16  # a net label's height
PAD = 24  # round the drawing

# the router's costs, per grid step
STEP, BEND, CROSS, NEAR = 1.0, 6.0, 8.0, 0.6


def _e(text) -> str:
    return html.escape(str(text), quote=True)


def _pin(spec: str) -> tuple[str, str]:
    name, _, number = str(spec).partition(":")
    return name.strip(), number.strip()


def load(path: Path) -> dict:
    """Read ``schematic.json`` and check it; raises ValueError naming the file."""
    path = Path(path)
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: not valid JSON: {exc}") from None
    check(data, str(path))
    return data


def check(data: dict, where: str = SCHEMATIC) -> None:
    """Every part has a unique ref and pins; every net names existing pins,
    and no pin is on two nets."""
    def fail(message):
        raise ValueError(f"{where}: {message}")

    if not isinstance(data, dict) or not isinstance(data.get("components"), list):
        fail("needs a list of components")
    pins: dict[str, set[str]] = {}
    for comp in data["components"]:
        ref = comp.get("ref")
        if not ref or ref in pins:
            fail(f"every component needs a unique ref (got {ref!r})")
        for key in ("x", "y"):
            if not isinstance(comp.get(key), (int, float)):
                fail(f"{ref}: needs numeric {key}")
        if comp.get("symbol") not in (None, *SYMBOLS):
            fail(f"{ref}: unknown symbol {comp['symbol']!r}")
        sides = comp.get("pins", {})
        if set(sides) - set(SIDES):
            fail(f"{ref}: pins go on {', '.join(SIDES)}")
        names = [_pin(p)[0] for side in SIDES for p in sides.get(side, [])]
        if len(names) != len(set(names)) or not all(names):
            fail(f"{ref}: pin names must be unique and non-empty")
        pins[ref] = set(names)
    seen: dict[str, str] = {}
    names = set()
    for net in data.get("nets", []):
        name = net.get("name")
        if not name or name in names:
            fail(f"every net needs a unique name (got {name!r})")
        names.add(name)
        if net.get("kind", "signal") not in KINDS:
            fail(f"net {name}: kind is one of {', '.join(KINDS)}")
        if net.get("draw", "wire") not in DRAWS:
            fail(f"net {name}: draw is one of {', '.join(DRAWS)}")
        for ref_pin in net.get("pins", []):
            ref, _, pin = str(ref_pin).partition(".")
            if pin not in pins.get(ref, ()):
                fail(f"net {name}: no pin {ref_pin!r}")
            if ref_pin in seen:
                fail(f"{ref_pin} is on two nets: {seen[ref_pin]} and {name}")
            seen[ref_pin] = name


def _draw(net: dict) -> str:
    if "draw" in net:
        return net["draw"]
    if net.get("kind") == "ground" and len(net.get("pins", [])) > 3:
        return "symbol"
    return "wire"


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------
def _snap(v: float) -> float:
    return round(v / UNIT) * UNIT


def _box(comp: dict) -> tuple[float, float, float, float]:
    """(x, y, w, h) of a part's box, in px, on the grid."""
    sides = comp.get("pins", {})
    left = [_pin(p)[0] for p in sides.get("left", [])]
    right = [_pin(p)[0] for p in sides.get("right", [])]
    top, bottom = sides.get("top", []), sides.get("bottom", [])
    rows = max(len(left), len(right), 1)
    inner = max((max(map(len, left), default=0) + max(map(len, right), default=0) + 3) * CHAR,
                (len(comp["ref"]) + len(comp.get("name", "")) + 2) * CHAR + 12,
                max(len(top), len(bottom), 1) * PITCH + PITCH,
                6 * UNIT if comp.get("symbol") else 0)
    w = comp["w"] * UNIT if "w" in comp else UNIT * -(-inner // UNIT)
    h = HEADER + rows * PITCH + (UNIT if comp.get("symbol") in ("npn", "pmos") else 0)
    if comp.get("h"):
        h = comp["h"] * UNIT
    return comp["x"] * UNIT, comp["y"] * UNIT, w, h


def _pin_points(comp: dict) -> list[tuple[str, str, str, float, float]]:
    """(name, number, side, x, y) of each pin's end on the box."""
    x, y, w, h = _box(comp)
    points = []
    sides = comp.get("pins", {})
    for i, spec in enumerate(sides.get("left", [])):
        points.append((*_pin(spec), "left", x, y + HEADER + PITCH / 2 + i * PITCH))
    for i, spec in enumerate(sides.get("right", [])):
        points.append((*_pin(spec), "right", x + w, y + HEADER + PITCH / 2 + i * PITCH))
    for side, edge in (("top", y), ("bottom", y + h)):
        specs = sides.get(side, [])
        start = x + _snap((w - (len(specs) - 1) * PITCH) / 2)
        for i, spec in enumerate(specs):
            points.append((*_pin(spec), side, start + i * PITCH, edge))
    return points


_OUT = {"left": (-1, 0), "right": (1, 0), "top": (0, -1), "bottom": (0, 1)}


def _label_box(side: str, x: float, y: float, text: str) -> tuple[float, float, float, float]:
    """(x, y, w, h) of a net label whose stub ends at (x, y)."""
    w = len(text) * CHAR + 12
    if side == "left":
        return x - w, y - LABEL_H / 2, w, LABEL_H
    if side == "right":
        return x, y - LABEL_H / 2, w, LABEL_H
    if side == "top":  # turned to read upward
        return x - LABEL_H / 2, y - w, LABEL_H, w
    return x - LABEL_H / 2, y, LABEL_H, w


# --------------------------------------------------------------------------
# routing
# --------------------------------------------------------------------------
_DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def route(data: dict) -> dict[str, dict]:
    """Route every wired net on the grid.

    Returns, per net name: ``paths`` (lists of (x, y) px points, one per
    connection, corners only), ``dots`` (joints) and ``failed`` (the pins
    the router could not reach, drawn with a label instead).
    """
    boxes = {c["ref"]: _box(c) for c in data["components"]}
    ends: dict[str, tuple[int, int, str]] = {}  # REF.PIN -> its stub's end cell and side
    for comp in data["components"]:
        for name, _, side, px, py in _pin_points(comp):
            dx, dy = _OUT[side]
            ends[f"{comp['ref']}.{name}"] = (round((px + dx * STUB) / UNIT),
                                             round((py + dy * STUB) / UNIT), side)
    blocked: set[tuple[int, int]] = set()
    for x, y, w, h in boxes.values():  # each box, and a unit round it
        gx0, gy0 = round(x / UNIT) - 1, round(y / UNIT) - 1
        gx1, gy1 = round((x + w) / UNIT) + 1, round((y + h) / UNIT) + 1
        blocked.update((i, j) for i in range(gx0, gx1 + 1) for j in range(gy0, gy1 + 1))
    xs = [c[0] for c in ends.values()] + [b[0] / UNIT for b in boxes.values()] \
        + [(b[0] + b[2]) / UNIT for b in boxes.values()]
    ys = [c[1] for c in ends.values()] + [b[1] / UNIT for b in boxes.values()] \
        + [(b[1] + b[3]) / UNIT for b in boxes.values()]
    lo_x, hi_x, lo_y, hi_y = int(min(xs)) - 6, int(max(xs)) + 6, int(min(ys)) - 6, int(max(ys)) + 6

    # what the wires already laid hold: per cell, per net, the axes used ("h", "v")
    # and whether it is a corner, joint or end (which nothing else may touch)
    axes: dict[tuple[int, int], dict[str, set[str]]] = {}
    nodes: dict[tuple[int, int], str] = {}  # cell -> net, for corners, joints and pin ends
    for ref_pin, (gx, gy, _) in ends.items():
        nodes[(gx, gy)] = ref_pin  # every pin's end is taken, wired or not

    wired = [n for n in data.get("nets", []) if _draw(n) == "wire" and len(n.get("pins", [])) > 1]
    for net in data.get("nets", []):  # a ground symbol hangs a unit off its pin's end
        if _draw(net) == "symbol":
            for p in net.get("pins", []):
                gx, gy, side = ends[p]
                blocked.add((gx, gy - 1) if side == "top" else (gx, gy + 1))

    def spread(net):
        cells = [ends[p][:2] for p in net["pins"]]
        return (max(c[0] for c in cells) - min(c[0] for c in cells)
                + max(c[1] for c in cells) - min(c[1] for c in cells))

    result = {}
    for net in sorted(wired, key=lambda n: (spread(n), len(n["pins"]))):
        name = net["name"]
        for p in net["pins"]:
            nodes[ends[p][:2]] = name  # this net's own ends
        own = {ends[p][:2] for p in net["pins"]}

        def cost_into(cell, axis):
            """The cost of a step into ``cell`` along ``axis``, or None if it is barred."""
            if cell in blocked and cell not in own:
                return None
            if not (lo_x <= cell[0] <= hi_x and lo_y <= cell[1] <= hi_y):
                return None
            holder = nodes.get(cell)  # another pin's end, or another net's corner or joint
            if holder is not None and holder != name and cell not in own:
                return None
            extra = 0.0
            for other, used in axes.get(cell, {}).items():
                if other == name:
                    continue
                if axis in used:
                    return None  # along another net's wire
                extra += CROSS
            for dx, dy in _DIRS:  # hugging another net's wire
                for other in axes.get((cell[0] + dx, cell[1] + dy), {}):
                    if other != name:
                        extra += NEAR
                        break
            return STEP + extra

        tree: set[tuple[int, int]] = set()
        first, *rest = net["pins"]
        tree.add(ends[first][:2])
        paths, failed = [], []
        stub_axis = {p: ("h" if ends[p][2] in ("left", "right") else "v") for p in net["pins"]}
        for p in sorted(rest, key=lambda q: min(abs(ends[q][0] - t[0]) + abs(ends[q][1] - t[1])
                                                for t in tree)):
            start = ends[p][:2]
            if start in tree:
                continue
            path = _astar(start, tree, cost_into)
            if path is None:
                failed.append(p)
                continue
            paths.append(path)
            for i, cell in enumerate(path):
                used = axes.setdefault(cell, {}).setdefault(name, set())
                if i > 0:
                    used.add("h" if path[i - 1][1] == cell[1] else "v")
                if i + 1 < len(path):
                    used.add("h" if path[i + 1][1] == cell[1] else "v")
            tree.update(path)
        # corners and joints: cells where this net's wires and stubs meet in 3+ ways
        degree: dict[tuple[int, int], set[tuple[int, int]]] = {}
        for path in paths:
            for a, b in zip(path, path[1:]):
                degree.setdefault(a, set()).add((b[0] - a[0], b[1] - a[1]))
                degree.setdefault(b, set()).add((a[0] - b[0], a[1] - b[1]))
        for p in net["pins"]:
            if p in failed:
                continue
            gx, gy, side = ends[p]
            dx, dy = _OUT[side]
            degree.setdefault((gx, gy), set()).add((-dx, -dy))
        dots = [c for c, ds in degree.items() if len(ds) >= 3]
        for cell, ds in degree.items():
            if len(ds) >= 2 and not ({(1, 0), (-1, 0)} >= ds or {(0, 1), (0, -1)} >= ds):
                nodes[cell] = name  # a corner or joint: others keep off it
            axes.setdefault(cell, {}).setdefault(name, set())
        if len(net["pins"]) > 1 and not paths and len(failed) == len(rest):
            failed = list(net["pins"])  # nothing joined: label them all
        elif failed:
            failed = failed + ([first] if first not in failed else [])
        result[name] = {"paths": [_corners(p) for p in paths], "dots": dots, "failed": failed,
                        "stub_axis": stub_axis}
    return result


def _astar(start, goals: set, cost_into):
    """The cheapest grid path from ``start`` to any cell of ``goals``, with a
    cost for each bend; None if there is none."""
    gx0 = min(g[0] for g in goals)
    gx1 = max(g[0] for g in goals)
    gy0 = min(g[1] for g in goals)
    gy1 = max(g[1] for g in goals)

    def h(c):
        return (max(gx0 - c[0], 0, c[0] - gx1) + max(gy0 - c[1], 0, c[1] - gy1)) * STEP

    frontier = [(h(start), 0.0, start, -1)]
    best = {(start, -1): 0.0}
    came = {}
    while frontier:
        _, g, cell, d = heapq.heappop(frontier)
        if cell in goals:
            path, state = [cell], (cell, d)
            while state in came:
                state = came[state]
                path.append(state[0])
            return path[::-1]
        if g > best.get((cell, d), float("inf")):
            continue
        for nd, (dx, dy) in enumerate(_DIRS):
            if d >= 0 and (dx, dy) == (-_DIRS[d][0], -_DIRS[d][1]):
                continue
            nxt = (cell[0] + dx, cell[1] + dy)
            step = cost_into(nxt, "h" if dy == 0 else "v")
            if step is None:
                continue
            ng = g + step + (BEND if d >= 0 and nd != d else 0.0)
            if ng < best.get((nxt, nd), float("inf")):
                best[(nxt, nd)] = ng
                came[(nxt, nd)] = (cell, d)
                heapq.heappush(frontier, (ng + h(nxt), ng, nxt, nd))
    return None


def _corners(path):
    """A grid path as px points, its straight runs merged."""
    points = [path[0]]
    for a, b, c in zip(path, path[1:], path[2:]):
        if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]):
            points.append(b)
    points.append(path[-1])
    return [(x * UNIT, y * UNIT) for x, y in points]


# --------------------------------------------------------------------------
# drawing
# --------------------------------------------------------------------------
def _symbol(kind: str, x: float, y: float, w: float, h: float) -> str:
    """A small symbol in the middle of a part's box, below its title."""
    cx, cy = x + w / 2, y + HEADER + (h - HEADER) / 2
    if kind == "diode":
        return (f'<path class=sym d="M{cx - 8} {cy - 7}L{cx + 6} {cy}L{cx - 8} {cy + 7}Z'
                f'M{cx + 6} {cy - 7}V{cy + 7}M{x} {cy}H{cx - 8}M{cx + 6} {cy}H{x + w}"/>')
    if kind == "resistor":
        return (f'<path class=sym d="M{x} {cy}H{cx - 12}M{cx + 12} {cy}H{x + w}"/>'
                f'<rect class=sym x="{cx - 12}" y="{cy - 5}" width=24 height=10 />')
    if kind == "capacitor":
        return f'<path class=sym d="M{x} {cy}H{cx - 3}M{cx + 3} {cy}H{x + w}M{cx - 3} {cy - 9}V{cy + 9}M{cx + 3} {cy - 9}V{cy + 9}"/>'
    if kind == "cell":
        return (f'<path class=sym d="M{x} {cy}H{cx - 3}M{cx + 3} {cy}H{x + w}'
                f'M{cx - 3} {cy - 10}V{cy + 10}M{cx + 3} {cy - 5}V{cy + 5}"/>'
                f'<text class=sym-t x="{cx - 12}" y="{cy - 8}">+</text>')
    if kind == "npn":
        return (f'<path class=sym d="M{cx - 6} {cy - 10}V{cy + 10}M{cx - 6} {cy - 4}L{cx + 8} {cy - 12}'
                f'M{cx - 6} {cy + 4}L{cx + 8} {cy + 12}M{cx + 8} {cy + 12}l-6 -1l3 -5z"/>')
    if kind == "pmos":
        return (f'<path class=sym d="M{cx - 8} {cy - 10}V{cy + 10}M{cx - 4} {cy - 10}V{cy + 10}'
                f'M{cx - 4} {cy - 7}H{cx + 8}M{cx - 4} {cy + 7}H{cx + 8}M{cx - 4} {cy}H{cx + 4}'
                f'M{cx - 4} {cy}l5 -3v6z"/>')
    return ""


def _ground(x: float, y: float, side: str) -> str:
    """A ground symbol hung from a stub's end."""
    if side == "top":
        return (f'M{x} {y}V{y - 6}M{x - 7} {y - 6}H{x + 7}M{x - 4.5} {y - 9}H{x + 4.5}'
                f'M{x - 2} {y - 12}H{x + 2}')
    return (f'M{x} {y}V{y + 6}M{x - 7} {y + 6}H{x + 7}M{x - 4.5} {y + 9}H{x + 4.5}'
            f'M{x - 2} {y + 12}H{x + 2}')


def render(data: dict, links: dict[str, str] | None = None, root: str = "") -> str:
    """The schematic's section: heading, the drawing, the side panel and the
    script.  ``links`` maps a component's ``item`` to its page (from the site
    root, or a full URL), and ``root`` is the site root from this page."""
    links = links or {}
    net_of: dict[str, dict] = {}
    for net in data.get("nets", []):
        for ref_pin in net.get("pins", []):
            net_of[ref_pin] = net
    routes = route(data)

    shapes, wires, labels, xs, ys = [], [], [], [], []

    def grow(x, y, w=0, h=0):
        xs.extend((x, x + w))
        ys.extend((y, y + h))

    for group in data.get("groups", []):
        gx, gy, gw, gh = (group[k] * UNIT for k in ("x", "y", "w", "h"))
        grow(gx, gy - 14, gw, gh + 14)
        shapes.append(f'<g class=group><rect x="{gx}" y="{gy}" width="{gw}" height="{gh}" rx=8 />'
                      f'<text x="{gx + 8}" y="{gy - 5}">{_e(group.get("label", ""))}</text>'
                      f'{"<title>" + _e(group["note"]) + "</title>" if group.get("note") else ""}</g>')

    def pill(net, kind, side, ex, ey, ref_pin):
        lx, ly, lw, lh = _label_box(side, ex, ey, net["name"])
        grow(lx, ly, lw, lh)
        if side in ("left", "right"):
            text = f'<text x="{lx + lw / 2}" y="{ly + 12}" text-anchor=middle>{_e(net["name"])}</text>'
        else:
            cx, cy = lx + lw / 2, ly + lh / 2
            text = (f'<text x="{cx}" y="{cy}" text-anchor=middle dominant-baseline=central '
                    f'transform="rotate(-90 {cx} {cy})">{_e(net["name"])}</text>')
        return (f'<g class="net k-{kind}" data-net="{_e(net["name"])}" data-pin="{_e(ref_pin)}" '
                f'tabindex=0 role=button aria-label="Net {_e(net["name"])}"><rect x="{lx}" y="{ly}" '
                f'width="{lw}" height="{lh}" rx="{min(lw, lh) / 2}"/>{text}</g>')

    comps_info = {}
    for comp in data["components"]:
        ref = comp["ref"]
        x, y, w, h = _box(comp)
        grow(x, y, w, h)
        cls = "comp" + ("" if comp.get("modelled", True) else " off-model")
        parts = [f'<rect class=box x="{x}" y="{y}" width="{w}" height="{h}" rx=4 />',
                 f'<text class=ref x="{x + 6}" y="{y + 18}">{_e(ref)}'
                 f'<tspan class=name dx=6>{_e(comp.get("name", ""))}</tspan></text>']
        if comp.get("symbol"):
            parts.append(_symbol(comp["symbol"], x, y, w, h))
        pins_info = []
        for name, number, side, px, py in _pin_points(comp):
            ref_pin = f"{ref}.{name}"
            net = net_of.get(ref_pin)
            dx, dy = _OUT[side]
            ex, ey = px + dx * STUB, py + dy * STUB
            grow(ex - 4, ey - 4, 8, 8)
            net_attr = f' data-net="{_e(net["name"])}"' if net else ""
            kind = net.get("kind", "signal") if net else "nc"
            parts.append(f'<line class="stub k-{kind}"{net_attr} x1="{px}" y1="{py}" x2="{ex}" y2="{ey}"/>')
            if side in ("left", "right") and comp.get("symbol") not in ("diode", "resistor", "capacitor", "cell"):
                tx = px + 5 if side == "left" else px - 5
                anchor = "start" if side == "left" else "end"
                parts.append(f'<text class=pin x="{tx}" y="{py + 4}" text-anchor={anchor}>{_e(name)}</text>')
            elif side in ("top", "bottom"):
                ty = py + 12 if side == "top" else py - 5
                parts.append(f'<text class=pin x="{px}" y="{ty}" text-anchor=middle>{_e(name)}</text>')
            if number:  # small, on the stub, next to the box
                nx = px + dx * 3 if side in ("left", "right") else px + 3
                ny = py - 3 if side in ("left", "right") else py + dy * 8
                anchor = "end" if side == "left" else "start"
                parts.append(f'<text class=num x="{nx}" y="{ny}" text-anchor={anchor}>{_e(number)}</text>')
            if not net:
                parts.append(f'<path class=nc d="M{ex - 3} {ey - 3}l6 6m0 -6l-6 6"/>')
            elif _draw(net) == "symbol":
                labels.append(f'<path class="gnd k-{kind}" data-net="{_e(net["name"])}" data-pin="{_e(ref_pin)}" '
                              f'd="{_ground(ex, ey, side)}"><title>{_e(net["name"])}</title></path>')
                grow(ex - 8, ey - 14, 16, 28)
            elif _draw(net) == "label" or ref_pin in routes.get(net["name"], {}).get("failed", []) \
                    or len(net.get("pins", [])) < 2:
                labels.append(pill(net, kind, side, ex, ey, ref_pin))
            pins_info.append({"pin": name, "number": number, "net": net["name"] if net else ""})
        shapes.append(f'<g class="{cls}" data-ref="{_e(ref)}" tabindex=0 role=button '
                      f'aria-label="{_e(ref)} {_e(comp.get("name", ""))}">{"".join(parts)}</g>')
        href = links.get(comp.get("item", ""), "")
        if href and "://" not in href:
            href = root + href
        comps_info[ref] = {"name": comp.get("name", ""), "note": comp.get("note", ""),
                           "href": href, "modelled": comp.get("modelled", True), "pins": pins_info}

    for net in data.get("nets", []):
        r = routes.get(net["name"])
        if not r or not r["paths"]:
            continue
        kind, name = net.get("kind", "signal"), _e(net["name"])
        d = "".join("M" + "L".join(f"{x} {y}" for x, y in path) for path in r["paths"])
        for x, y in (p for path in r["paths"] for p in path):
            grow(x, y)
        dots = "".join(f'<circle cx="{x * UNIT}" cy="{y * UNIT}" r=3.2 />' for x, y in r["dots"])
        # the net's name, on its longest horizontal run
        runs = [(abs(b[0] - a[0]), a, b) for path in r["paths"] for a, b in zip(path, path[1:])
                if a[1] == b[1]]
        tag = ""
        if runs:
            length, a, b = max(runs)
            if length >= len(net["name"]) * CHAR + 8:
                tag = (f'<text class=tag x="{(a[0] + b[0]) / 2}" y="{a[1] - 4}" '
                       f'text-anchor=middle>{name}</text>')
        wires.append(f'<g class="wire net k-{kind}" data-net="{name}" tabindex=0 role=button '
                     f'aria-label="Net {name}"><path class=hit d="{d}"/><path class=line d="{d}"/>'
                     f'{dots}{tag}</g>')

    nets_info = {net["name"]: {"kind": net.get("kind", "signal"), "note": net.get("note", ""),
                               "pins": net.get("pins", [])} for net in data.get("nets", [])}
    x0, y0 = min(xs) - PAD, min(ys) - PAD
    width, height = max(xs) - x0 + PAD, max(ys) - y0 + PAD
    svg = (f'<svg class=sch-svg viewBox="{x0:.0f} {y0:.0f} {width:.0f} {height:.0f}" '
           f'data-box="{x0:.0f} {y0:.0f} {width:.0f} {height:.0f}" preserveAspectRatio="xMidYMid meet" '
           f'role=group aria-label="{_e(data.get("title", "Schematic"))}">'
           f'{"".join(shapes)}{"".join(wires)}{"".join(labels)}</svg>')
    legend = "".join(
        f'<li><button type=button class="chip k-{info["kind"]}" data-net="{_e(name)}">{_e(name)}</button></li>'
        for name, info in nets_info.items())
    note = f'<p class=muted>{_e(data["note"])}</p>' if data.get("note") else ""
    payload = json.dumps({"comps": comps_info, "nets": nets_info}).replace("</", "<\\/")
    ratio = f"{width:.0f} / {height:.0f}"
    return f"""<section class=schematic id=schematic>
  <h2 class=section-title>{_e(data.get("title", "Schematic"))}</h2>
  {note}
  <div class=sch-grid>
    <div class=sch-canvas style="aspect-ratio:{ratio}">{svg}
      <div class=sch-zoom><button type=button data-zoom=in aria-label="Zoom in">+</button><button
        type=button data-zoom=out aria-label="Zoom out">&minus;</button><button type=button
        data-zoom=fit aria-label="Fit the drawing">Fit</button></div>
    </div>
    <aside class=sch-panel aria-live=polite>
      <div class=sch-info><p class=muted>Drag to pan; wheel, pinch or the buttons to zoom.
      Point at a wire to light up its net; click a part or a net for what it joins.
      Dashed parts are wired in, not modelled.</p></div>
      <h3>Nets</h3>
      <ul class=sch-legend>{legend}</ul>
    </aside>
  </div>
  <script type=application/json class=sch-data>{payload}</script>
  <script>{_JS}</script>
</section>"""


CSS = """
.schematic{margin:28px 0}
.sch-grid{display:grid;grid-template-columns:minmax(0,1fr) 230px;gap:16px;align-items:start}
@media (max-width:820px){.sch-grid{grid-template-columns:1fr}
.sch-canvas{aspect-ratio:auto!important;height:65vh}}
.sch-canvas{position:relative;background:var(--panel);border:1px solid var(--line);border-radius:10px;
overflow:hidden;width:100%;max-height:78vh;min-height:320px;touch-action:none;user-select:none;
-webkit-user-select:none;cursor:grab}
.sch-canvas.grabbing{cursor:grabbing}
.sch-svg{display:block;position:absolute;inset:0;width:100%;height:100%;
font:11px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.sch-zoom{position:absolute;right:8px;top:8px;display:flex;gap:4px}
.sch-zoom button{font:600 .9rem system-ui,sans-serif;min-width:34px;height:34px;padding:0 8px;
border:1px solid var(--line);border-radius:8px;background:var(--panel);color:var(--ink);cursor:pointer}
.sch-zoom button:hover{border-color:var(--accent)}
.sch-svg .box{fill:var(--bg);stroke:var(--ink);stroke-width:1.2}
.sch-svg .off-model .box{stroke-dasharray:4 3}
.sch-svg .ref{font-weight:700;font-size:12px;fill:var(--ink)}
.sch-svg .name{font-weight:400;fill:var(--muted)}
.sch-svg .pin{fill:var(--ink)}
.sch-svg .num{fill:var(--muted);font-size:9px}
.sch-svg .sym{fill:none;stroke:var(--ink);stroke-width:1.3}
.sch-svg .sym-t{fill:var(--ink);font-size:10px}
.sch-svg .stub{stroke:var(--k);stroke-width:1.4}
.sch-svg .nc{stroke:var(--muted);stroke-width:1.2}
.sch-svg .gnd{fill:none;stroke:var(--k);stroke-width:1.4;cursor:pointer}
.sch-svg .group rect{fill:none;stroke:var(--muted);stroke-dasharray:6 4}
.sch-svg .group text{fill:var(--muted);font-size:11px;font-style:italic}
.sch-svg .comp,.sch-svg .net{cursor:pointer;outline:none}
.sch-svg .net rect{fill:var(--k);stroke:none}
.sch-svg .net:not(.wire) text{fill:#fff;font-weight:600}
.sch-svg .wire .line{fill:none;stroke:var(--k);stroke-width:1.5;stroke-linejoin:round}
.sch-svg .wire .hit{fill:none;stroke:transparent;stroke-width:9}
.sch-svg .wire circle{fill:var(--k)}
.sch-svg .wire .tag{fill:var(--k);font-size:10px;font-weight:600;paint-order:stroke;stroke:var(--panel);
stroke-width:3px;stroke-linejoin:round}
.k-power{--k:#c2410c}.k-ground{--k:#475569}.k-signal{--k:#2f6fb1}.k-data{--k:#7c3aed}.k-nc{--k:var(--muted)}
@media (prefers-color-scheme:dark){.k-power{--k:#ea7a3f}.k-ground{--k:#8d99aa}.k-signal{--k:#4f8fd6}
.k-data{--k:#9d6cf0}}
.sch-svg.lit .comp,.sch-svg.lit .net,.sch-svg.lit .gnd{opacity:.22;transition:opacity .12s}
.sch-svg.lit .comp.on,.sch-svg.lit .net.on,.sch-svg.lit .gnd.on{opacity:1}
.sch-svg .stub.on,.sch-svg .gnd.on{stroke-width:3}
.sch-svg .wire.on .line{stroke-width:3}
.sch-svg .comp.on .box,.sch-svg .comp:focus-visible .box{stroke:var(--accent);stroke-width:2.5}
.sch-svg .net:focus-visible rect,.sch-svg .wire:focus-visible .line{stroke-width:3}
.sch-panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.sch-panel h3{font-size:.8rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:14px 0 6px}
.sch-info h4{margin:0 0 4px;font-size:1rem}
.sch-info p{margin:4px 0}
.sch-info ul{list-style:none;padding:0;margin:6px 0;font-size:.9rem}
.sch-info li{padding:2px 0;border-bottom:1px solid var(--line)}
.sch-legend{list-style:none;display:flex;flex-wrap:wrap;gap:6px;padding:0;margin:0}
.chip{font:600 .78rem ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:#fff;background:var(--k);
border:0;border-radius:99px;padding:3px 9px;cursor:pointer}
.chip.link{background:none;color:var(--accent);padding:0;font-weight:400;text-decoration:underline}
"""

_JS = r"""(function () {
  var sec = document.currentScript.parentNode;
  var data = JSON.parse(sec.querySelector('.sch-data').textContent);
  var svg = sec.querySelector('.sch-svg'), info = sec.querySelector('.sch-info');
  var frame = sec.querySelector('.sch-canvas');
  var intro = info.innerHTML, pinned = null;
  function esc(s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

  /* ---- pan and zoom: the view is the SVG's viewBox ---- */
  var home = svg.getAttribute('data-box').split(' ').map(Number);
  var view = home.slice();
  function apply() { svg.setAttribute('viewBox', view.join(' ')); }
  function scale() {  /* drawing units per screen pixel ("meet": the larger one) */
    var r = frame.getBoundingClientRect();
    return Math.max(view[2] / r.width, view[3] / r.height);
  }
  function toSvg(cx, cy) {
    var r = frame.getBoundingClientRect(), s = scale();
    return [view[0] + view[2] / 2 + (cx - r.left - r.width / 2) * s,
            view[1] + view[3] / 2 + (cy - r.top - r.height / 2) * s];
  }
  function zoom(k, cx, cy) {  /* k > 1 zooms in, about the screen point (cx, cy) */
    var w = view[2] / k;
    if (w < home[2] / 12) k = view[2] / (home[2] / 12);
    if (w > home[2] * 2) k = view[2] / (home[2] * 2);
    var p = toSvg(cx, cy);
    view = [p[0] - (p[0] - view[0]) / k, p[1] - (p[1] - view[1]) / k, view[2] / k, view[3] / k];
    apply();
  }
  function centre() { var r = frame.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }
  frame.addEventListener('wheel', function (e) {
    e.preventDefault();
    zoom(Math.exp(-e.deltaY * (e.deltaMode ? 0.05 : 0.0015)), e.clientX, e.clientY);
  }, {passive: false});
  var ptrs = {}, last = null, moved = 0;
  function mid() {
    var ps = Object.keys(ptrs).map(function (k) { return ptrs[k]; });
    if (ps.length === 1) return {x: ps[0].x, y: ps[0].y, d: 0};
    return {x: (ps[0].x + ps[1].x) / 2, y: (ps[0].y + ps[1].y) / 2,
            d: Math.hypot(ps[0].x - ps[1].x, ps[0].y - ps[1].y)};
  }
  frame.addEventListener('pointerdown', function (e) {
    if (e.target.closest('.sch-zoom')) return;
    ptrs[e.pointerId] = {x: e.clientX, y: e.clientY};
    last = mid(); if (Object.keys(ptrs).length === 1) moved = 0;
  });
  frame.addEventListener('pointermove', function (e) {
    if (!ptrs[e.pointerId]) return;
    ptrs[e.pointerId] = {x: e.clientX, y: e.clientY};
    var m = mid(), s = scale();
    if (Object.keys(ptrs).length > 2) return;
    moved += Math.abs(m.x - last.x) + Math.abs(m.y - last.y);
    if (moved > 4 && !frame.classList.contains('grabbing')) {
      frame.classList.add('grabbing');
      try { frame.setPointerCapture(e.pointerId); } catch (err) {}
    }
    if (m.d && last.d) zoom(m.d / last.d, m.x, m.y);
    view[0] -= (m.x - last.x) * s; view[1] -= (m.y - last.y) * s; apply();
    last = m;
  });
  function up(e) {
    delete ptrs[e.pointerId];
    if (!Object.keys(ptrs).length) frame.classList.remove('grabbing');
    last = mid ? (Object.keys(ptrs).length ? mid() : null) : null;
  }
  frame.addEventListener('pointerup', up);
  frame.addEventListener('pointercancel', up);
  frame.addEventListener('dblclick', function (e) {
    if (!e.target.closest('.sch-zoom')) zoom(1.8, e.clientX, e.clientY);
  });
  sec.querySelector('.sch-zoom').addEventListener('click', function (e) {
    var b = e.target.closest('button'); if (!b) return;
    var c = centre(), z = b.getAttribute('data-zoom');
    if (z === 'in') zoom(1.4, c[0], c[1]);
    else if (z === 'out') zoom(1 / 1.4, c[0], c[1]);
    else { view = home.slice(); apply(); }
  });

  /* ---- lighting up nets and parts ---- */
  function clear() {
    svg.classList.remove('lit');
    svg.querySelectorAll('.on').forEach(function (n) { n.classList.remove('on'); });
  }
  function lightNet(name) {
    clear(); svg.classList.add('lit');
    svg.querySelectorAll('[data-net]').forEach(function (n) {
      if (n.getAttribute('data-net') === name) n.classList.add('on');
    });
    (data.nets[name] || {pins: []}).pins.forEach(function (rp) {
      var c = svg.querySelector('.comp[data-ref="' + rp.split('.')[0] + '"]');
      if (c) c.classList.add('on');
    });
  }
  function lightComp(ref) {
    clear(); svg.classList.add('lit');
    var c = svg.querySelector('.comp[data-ref="' + ref + '"]'); if (c) c.classList.add('on');
    if (c) c.querySelectorAll('.stub[data-net]').forEach(function (n) { n.classList.add('on'); });
    var nets = {};
    data.comps[ref].pins.forEach(function (p) { if (p.net) nets[p.net] = 1; });
    svg.querySelectorAll('.wire, .net, .gnd').forEach(function (n) {
      var pin = n.getAttribute('data-pin');
      if (pin ? pin.split('.')[0] === ref : nets[n.getAttribute('data-net')]) n.classList.add('on');
    });
  }
  function netButton(name) {
    return '<button type=button class="chip k-' + data.nets[name].kind + '" data-net="' + esc(name) +
      '">' + esc(name) + '</button>';
  }
  function showNet(name) {
    var n = data.nets[name];
    info.innerHTML = '<h4>' + netButton(name) + ' <span class=muted>' + n.kind + '</span></h4>' +
      (n.note ? '<p>' + esc(n.note) + '</p>' : '') + '<ul>' + n.pins.map(function (rp) {
        var ref = rp.split('.')[0], c = data.comps[ref];
        return '<li><button type=button class="chip link" data-ref="' + esc(ref) + '">' + esc(ref) +
          '</button>.' + esc(rp.split('.')[1]) + ' <span class=muted>' + esc(c.name) + '</span></li>';
      }).join('') + '</ul>';
  }
  function showComp(ref) {
    var c = data.comps[ref];
    info.innerHTML = '<h4>' + esc(ref) + ' ' + esc(c.name) + '</h4>' +
      (c.href ? '<p><a href="' + esc(c.href) + '">Its page</a></p>' : '') +
      (c.modelled ? '' : '<p class=muted>Wired in; not in the 3D model.</p>') +
      (c.note ? '<p>' + esc(c.note) + '</p>' : '') + '<ul>' + c.pins.map(function (p) {
        return '<li>' + esc(p.pin) + (p.number ? ' <span class=muted>(' + esc(p.number) + ')</span>' : '') +
          ' ' + (p.net ? netButton(p.net) : '<span class=muted>not connected</span>') + '</li>';
      }).join('') + '</ul>';
  }
  function pick(target) {
    var net = target.closest('[data-net]'), ref = target.closest('[data-ref]');
    if (net && (net.classList.contains('net') || net.classList.contains('chip') ||
                net.classList.contains('gnd'))) {
      var name = net.getAttribute('data-net'); pinned = 'n:' + name; lightNet(name); showNet(name); return true;
    }
    if (ref) {
      var r = ref.getAttribute('data-ref'); pinned = 'c:' + r; lightComp(r); showComp(r); return true;
    }
    return false;
  }
  function restore() {
    if (!pinned) { clear(); return; }
    if (pinned[0] === 'n') lightNet(pinned.slice(2)); else lightComp(pinned.slice(2));
  }
  sec.addEventListener('click', function (e) {
    if (e.target.closest('.sch-zoom')) return;
    if (svg.contains(e.target) && moved > 4) return;  /* the end of a drag */
    if (!pick(e.target) && svg.contains(e.target)) { pinned = null; clear(); info.innerHTML = intro; }
  });
  sec.addEventListener('keydown', function (e) {
    if ((e.key === 'Enter' || e.key === ' ') && e.target.closest('.sch-svg [tabindex]')) {
      e.preventDefault(); pick(e.target);
    } else if (e.key === 'Escape') { pinned = null; clear(); info.innerHTML = intro; }
  });
  svg.addEventListener('mouseover', function (e) {
    if (frame.classList.contains('grabbing')) return;
    var net = e.target.closest('.net, .gnd'); if (net) lightNet(net.getAttribute('data-net'));
  });
  svg.addEventListener('mouseout', function (e) { if (e.target.closest('.net, .gnd')) restore(); });
})();"""
