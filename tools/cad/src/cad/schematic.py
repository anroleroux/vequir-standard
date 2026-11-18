"""Wiring schematics on the catalogue site: ``schematic.json`` beside a
product's ``product.md`` (or an assembly's ``assembly.md``).

The file describes the circuit as parts with pins, and nets joining pins;
the page draws each part as a box with its pins on its sides, and each pin's
net as a coloured label at the end of a short stub, the way net labels join
a schematic without wires.  It is interactive: pointing at (or tabbing to)
a net lights up every pin on it, and clicking a part or a net shows what it
joins, with a link to the part's own page.

    {
      "title": "Wiring",                      optional, the section's heading
      "note": "text under the heading",       optional
      "groups": [                             optional: a dashed frame round some parts
        {"label": "Load sharing", "x": 0, "y": 0, "w": 30, "h": 20, "note": "..."}
      ],
      "components": [
        {"ref": "U1", "name": "Pico 2 W",
         "item": "electronics/pico_2w",       optional: a library item (or a part's
                                              designation) the assembled model places;
                                              the part links to its page
         "x": 40, "y": 0,                     grid units (10 px), the box's top left
         "w": 16,                             optional, grid units; else from its text
         "symbol": "diode",                   optional: diode, resistor, npn, pmos, cell
         "pins": {"left": ["VBUS:40", "VSYS:39"], "right": ["GP2:4"],
                  "top": [], "bottom": []},   each "NAME" or "NAME:number", in order
                                              down (left, right) or across (top, bottom)
         "note": "...", "modelled": true}     modelled: false for parts on the wires only
      ],
      "nets": [
        {"name": "VBUS", "kind": "power",     power, ground, signal or data
         "pins": ["J1.VBUS", "U1.VBUS"], "note": "..."}
      ]
    }

:func:`load` reads and checks a file; :func:`render` turns it into the
page's section (an inline SVG, a side panel and a small script, no
libraries).
"""

from __future__ import annotations

import html
import json
from pathlib import Path

#: The file a product or assembly directory may hold.
SCHEMATIC = "schematic.json"
SIDES = ("left", "right", "top", "bottom")
KINDS = ("power", "ground", "signal", "data")
SYMBOLS = ("diode", "resistor", "npn", "pmos", "cell")

UNIT = 10  # px per grid unit
PITCH = 2 * UNIT  # between pins on a side
HEADER = 3 * UNIT  # the box's title band
STUB = 2 * UNIT  # a pin's line, out of the box
CHAR = 6.6  # px per character, 11 px monospace
LABEL_H = 16  # a net label's height
PAD = 16  # round the drawing


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
        for ref_pin in net.get("pins", []):
            ref, _, pin = str(ref_pin).partition(".")
            if pin not in pins.get(ref, ()):
                fail(f"net {name}: no pin {ref_pin!r}")
            if ref_pin in seen:
                fail(f"{ref_pin} is on two nets: {seen[ref_pin]} and {name}")
            seen[ref_pin] = name


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------
def _box(comp: dict) -> tuple[float, float, float, float]:
    """(x, y, w, h) of a part's box, in px."""
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
        start = x + (w - (len(specs) - 1) * PITCH) / 2
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
    if kind == "cell":
        return (f'<path class=sym d="M{cx - 3} {cy - 10}V{cy + 10}M{cx + 3} {cy - 5}V{cy + 5}"/>'
                f'<text class=sym-t x="{cx - 9}" y="{cy - 8}">+</text>')
    if kind == "npn":
        return (f'<path class=sym d="M{cx - 6} {cy - 10}V{cy + 10}M{cx - 6} {cy - 4}L{cx + 8} {cy - 12}'
                f'M{cx - 6} {cy + 4}L{cx + 8} {cy + 12}M{cx + 8} {cy + 12}l-6 -1l3 -5z"/>')
    if kind == "pmos":
        return (f'<path class=sym d="M{cx - 8} {cy - 10}V{cy + 10}M{cx - 4} {cy - 10}V{cy + 10}'
                f'M{cx - 4} {cy - 7}H{cx + 8}M{cx - 4} {cy + 7}H{cx + 8}M{cx - 4} {cy}H{cx + 4}'
                f'M{cx - 4} {cy}l5 -3v6z"/>')
    return ""


def render(data: dict, links: dict[str, str] | None = None, root: str = "") -> str:
    """The schematic's section: heading, the drawing, the side panel and the
    script.  ``links`` maps a component's ``item`` to its page (from the site
    root, or a full URL), and ``root`` is the site root from this page."""
    links = links or {}
    net_of: dict[str, dict] = {}
    for net in data.get("nets", []):
        for ref_pin in net.get("pins", []):
            net_of[ref_pin] = net

    shapes, labels, xs, ys = [], [], [], []

    def grow(x, y, w=0, h=0):
        xs.extend((x, x + w))
        ys.extend((y, y + h))

    for group in data.get("groups", []):
        gx, gy, gw, gh = (group[k] * UNIT for k in ("x", "y", "w", "h"))
        grow(gx, gy - 14, gw, gh + 14)
        shapes.append(f'<g class=group><rect x="{gx}" y="{gy}" width="{gw}" height="{gh}" rx=8 />'
                      f'<text x="{gx + 8}" y="{gy - 5}">{_e(group.get("label", ""))}</text>'
                      f'{"<title>" + _e(group["note"]) + "</title>" if group.get("note") else ""}</g>')

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
            net_attr = f' data-net="{_e(net["name"])}"' if net else ""
            kind = net.get("kind", "signal") if net else "nc"
            parts.append(f'<line class="stub k-{kind}"{net_attr} x1="{px}" y1="{py}" x2="{ex}" y2="{ey}"/>')
            if side in ("left", "right") and not comp.get("symbol") in ("diode", "resistor"):
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
            if net:
                lx, ly, lw, lh = _label_box(side, ex, ey, net["name"])
                grow(lx, ly, lw, lh)
                if side in ("left", "right"):
                    text = (f'<text x="{lx + lw / 2}" y="{ly + 12}" text-anchor=middle>'
                            f'{_e(net["name"])}</text>')
                else:
                    cx, cy = lx + lw / 2, ly + lh / 2
                    text = (f'<text x="{cx}" y="{cy}" text-anchor=middle dominant-baseline=central '
                            f'transform="rotate(-90 {cx} {cy})">{_e(net["name"])}</text>')
                labels.append(f'<g class="net k-{kind}" data-net="{_e(net["name"])}" data-pin="{_e(ref_pin)}" '
                              f'tabindex=0 role=button '
                              f'aria-label="Net {_e(net["name"])}"><rect x="{lx}" y="{ly}" width="{lw}" '
                              f'height="{lh}" rx="{min(lw, lh) / 2}"/>{text}</g>')
            else:
                parts.append(f'<path class=nc d="M{ex - 3} {ey - 3}l6 6m0 -6l-6 6"/>')
                grow(ex - 3, ey - 3, 6, 6)
            pins_info.append({"pin": name, "number": number, "net": net["name"] if net else ""})
        shapes.append(f'<g class="{cls}" data-ref="{_e(ref)}" tabindex=0 role=button '
                      f'aria-label="{_e(ref)} {_e(comp.get("name", ""))}">{"".join(parts)}</g>')
        href = links.get(comp.get("item", ""), "")
        if href and "://" not in href:
            href = root + href
        comps_info[ref] = {"name": comp.get("name", ""), "note": comp.get("note", ""),
                           "href": href, "modelled": comp.get("modelled", True), "pins": pins_info}

    nets_info = {net["name"]: {"kind": net.get("kind", "signal"), "note": net.get("note", ""),
                               "pins": net.get("pins", [])} for net in data.get("nets", [])}
    x0, y0 = min(xs) - PAD, min(ys) - PAD
    width, height = max(xs) - x0 + PAD, max(ys) - y0 + PAD
    svg = (f'<svg class=sch-svg viewBox="{x0:.0f} {y0:.0f} {width:.0f} {height:.0f}" '
           f'style="min-width:{width * 0.62:.0f}px" role=group '
           f'aria-label="{_e(data.get("title", "Schematic"))}">'
           f'{"".join(shapes)}{"".join(labels)}</svg>')
    legend = "".join(
        f'<li><button type=button class="chip k-{info["kind"]}" data-net="{_e(name)}">{_e(name)}</button></li>'
        for name, info in nets_info.items())
    note = f'<p class=muted>{_e(data["note"])}</p>' if data.get("note") else ""
    payload = json.dumps({"comps": comps_info, "nets": nets_info}).replace("</", "<\\/")
    return f"""<section class=schematic id=schematic>
  <h2 class=section-title>{_e(data.get("title", "Schematic"))}</h2>
  {note}
  <div class=sch-grid>
    <div class=sch-canvas>{svg}</div>
    <aside class=sch-panel aria-live=polite>
      <div class=sch-info><p class=muted>Point at a net label to light up everything on it;
      click a part or a net for what it joins. Dashed parts are wired in, not modelled.</p></div>
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
@media (max-width:820px){.sch-grid{grid-template-columns:1fr}}
.sch-canvas{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:auto;
max-height:80vh;-webkit-overflow-scrolling:touch}
.sch-svg{display:block;width:100%;height:auto;font:11px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.sch-svg .box{fill:var(--bg);stroke:var(--ink);stroke-width:1.2}
.sch-svg .off-model .box{stroke-dasharray:4 3}
.sch-svg .ref{font-weight:700;font-size:12px;fill:var(--ink)}
.sch-svg .name{font-weight:400;fill:var(--muted)}
.sch-svg .pin{fill:var(--ink)}
.sch-svg .num{fill:var(--muted);font-size:9px}
.sch-svg .sym{fill:none;stroke:var(--ink);stroke-width:1.3}
.sch-svg .sym-t{fill:var(--ink);font-size:10px}
.sch-svg .stub{stroke:var(--ink);stroke-width:1.2}
.sch-svg .nc{stroke:var(--muted);stroke-width:1.2}
.sch-svg .group rect{fill:none;stroke:var(--muted);stroke-dasharray:6 4}
.sch-svg .group text{fill:var(--muted);font-size:11px;font-style:italic}
.sch-svg .comp,.sch-svg .net{cursor:pointer;outline:none}
.sch-svg .net rect{fill:var(--k);stroke:none}
.sch-svg .net text{fill:#fff;font-weight:600}
.k-power{--k:#c2410c}.k-ground{--k:#475569}.k-signal{--k:#2f6fb1}.k-data{--k:#7c3aed}.k-nc{--k:var(--muted)}
@media (prefers-color-scheme:dark){.k-power{--k:#ea7a3f}.k-ground{--k:#7d8a9c}.k-signal{--k:#4f8fd6}
.k-data{--k:#9d6cf0}}
.sch-svg.lit .comp,.sch-svg.lit .net{opacity:.25;transition:opacity .12s}
.sch-svg.lit .comp.on,.sch-svg.lit .net.on{opacity:1}
.sch-svg .stub.on{stroke:var(--k);stroke-width:3}
.sch-svg .comp.on .box,.sch-svg .comp:focus-visible .box{stroke:var(--accent);stroke-width:2.5}
.sch-svg .net:focus-visible rect{stroke:var(--ink);stroke-width:2}
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
  var intro = info.innerHTML, pinned = null;
  function esc(s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
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
    svg.querySelectorAll('.net').forEach(function (n) {
      if (n.getAttribute('data-pin').split('.')[0] === ref) n.classList.add('on');
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
    if (net && (net.classList.contains('net') || net.classList.contains('chip'))) {
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
    if (!pick(e.target) && svg.contains(e.target)) { pinned = null; clear(); info.innerHTML = intro; }
  });
  sec.addEventListener('keydown', function (e) {
    if ((e.key === 'Enter' || e.key === ' ') && e.target.closest('.sch-svg [tabindex]')) {
      e.preventDefault(); pick(e.target);
    } else if (e.key === 'Escape') { pinned = null; clear(); info.innerHTML = intro; }
  });
  svg.addEventListener('mouseover', function (e) {
    var net = e.target.closest('.net'); if (net) lightNet(net.getAttribute('data-net'));
  });
  svg.addEventListener('mouseout', function (e) { if (e.target.closest('.net')) restore(); });
})();"""
