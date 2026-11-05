"""3S Li-ion BMS, 20 A.

DIY Electronics' Li-Ion/LiPo 3S cell pack protection module (board XR-121):
a printed circuit board carrying the protection chips and the MOSFETs that
switch the pack's negative lead, with through-hole pads for the pack and the
load. The parts are modelled as keep-out blocks, so a housing knows where to
stay clear: each MOSFET on its own, the small parts lumped into a few larger
blocks, and a block over every terminal for the solder joint and the wire.

Assumptions where the description is silent:
- the layout is read off a photograph of the top of the board, scaled to its
  64 mm length; places are good to about +-0.5 mm, heights are typical;
- the 64 x 20 x 3.4 mm is the board and its parts: a 1.2 mm board with every
  part on top, the tallest 2.2 mm high (the D-PAK MOSFETs), so 3.4 mm in all;
- four D-PAK (TO-252) MOSFETs in a 2 x 2 block at the -x end, each modelled
  as its body and tab (8 x 6.75 x 2.2 mm) and a strip over its leads
  (3.5 x 5 x 1 mm), the leads of the -x column pointing to -x and of the
  other column to +x;
- the R002 current shunt (8.5 x 3.45 x 0.7 mm) below the MOSFETs, at the -y
  edge;
- the small parts (SOT-23 transistors, 0603 resistors and capacitors) lumped
  into a 1.2 mm high column beside the MOSFETs and a 1.2 mm high block across
  the middle; the three SOT-23-6 protection chips and their resistors into a
  1.5 mm high block towards the +x end; the lone 104 resistor near the B-
  pad as a 0.6 mm block;
- the terminals are through-hole pads with a 1.0 mm hole, each carrying a
  2.0 mm high keep-out for the solder and the wire:
  B- (pack negative) at the -y edge beside the shunt; the balance taps B1
  (4.2 V) and B2 (8.4 V) along the -y edge and B+ (12.6 V) at the +y edge;
  P+ and P- (the load and charger) on the +x end, beside the + and - marks;
- the board's corners are rounded to 3 mm;
- x runs along the board, y across it, z up; the board is centred on x and
  y and its underside is on z = 0.
"""
import cadquery as cq

# the board, in mm
length = 64.0  # along x
width = 20.0  # along y
height = 3.4  # overall, board and parts
pcb_t = 1.2  # board thickness
corner_r = 3.0  # the board's corner radius

# keep-out blocks: (x_min, x_max, y_min, y_max, height above the board)
# the four D-PAK MOSFETs, body and tab
fet_rows_y = (5.47, -1.73)  # centre of each row
fet_body_y = 6.75  # body across y
fet_body_h = 2.2  # the tallest part
fet_cols = (  # (body x_min, body x_max, leads x_min, leads x_max)
    (-27.5, -19.5, -31.0, -27.5),  # -x column, leads to -x
    (-19.0, -10.75, -10.75, -7.25),  # +x column, leads to +x
)
fet_leads_y = 5.0  # the lead strip across y
fet_leads_h = 1.0  # the leads' height

small_parts = {  # the lumped small parts
    "shunt": (-29.75, -21.25, -9.5, -6.05, 0.7),  # R002, 2512-size
    "driver_column": (-6.25, -2.0, -9.1, 9.3, 1.2),  # SOT-23s and 0603s by the MOSFETs
    "balance_block": (-1.75, 17.25, -7.0, 9.3, 1.2),  # 0603s and SOT-23s across the middle
    "chip_block": (17.5, 26.5, -4.4, 7.0, 1.5),  # three SOT-23-6 chips and their 0603s
    "r104": (-13.25, -9.0, -7.45, -6.05, 0.6),  # the lone 104 resistor
}

# the terminals: (x_min, x_max, y_min, y_max), each with a hole at its centre
terminals = {
    "b_minus": (-20.0, -15.0, -9.75, -7.2),  # pack negative
    "b1": (1.0, 5.75, -9.75, -7.45),  # 4.2 V balance tap
    "b2": (22.0, 26.5, -9.75, -7.45),  # 8.4 V balance tap
    "b_plus": (22.0, 26.5, 7.2, 9.75),  # 12.6 V balance tap
    "p_plus": (27.75, 32.0, 1.15, 4.65),  # load positive
    "p_minus": (27.75, 32.0, -4.2, -0.7),  # load and charger negative
}
terminal_h = 2.0  # keep-out over each terminal for the solder and the wire
hole_d = 1.0  # through hole in each terminal
terminal_top = pcb_t + terminal_h


def block(x0, x1, y0, y1, h):
    """A box on top of the board spanning x0..x1, y0..y1, h high."""
    return (cq.Workplane("XY", origin=((x0 + x1) / 2, (y0 + y1) / 2, pcb_t))
            .rect(x1 - x0, y1 - y0).extrude(h))


def centre(r):
    return ((r[0] + r[1]) / 2, (r[2] + r[3]) / 2)


board = (cq.Workplane("XY").box(length, width, pcb_t, centered=(True, True, False))
         .edges("|Z").fillet(corner_r))

result = board
for bx0, bx1, lx0, lx1 in fet_cols:
    for y in fet_rows_y:
        result = result.union(block(bx0, bx1, y - fet_body_y / 2, y + fet_body_y / 2, fet_body_h))
        result = result.union(block(lx0, lx1, y - fet_leads_y / 2, y + fet_leads_y / 2, fet_leads_h))
for x0, x1, y0, y1, h in small_parts.values():
    result = result.union(block(x0, x1, y0, y1, h))
for r in terminals.values():
    result = result.union(block(*r, terminal_h))
holes = (cq.Workplane("XY")
         .pushPoints([centre(r) for r in terminals.values()])
         .circle(hole_d / 2).extrude(terminal_top))
result = result.cut(holes)

def terminal_tops(*names):
    """The top faces of the named terminals' keep-outs."""
    rects = [terminals[n] for n in names]
    return result.faces("+Z").filter(
        lambda f: abs(f.Center().z - terminal_top) < 1e-6
        and any(r[0] < f.Center().x < r[1] and r[2] < f.Center().y < r[3] for r in rects))


regions = {
    "b_minus_pad": terminal_tops("b_minus"),  # the pack's negative
    "p_minus_pad": terminal_tops("p_minus"),  # the load and charger's negative
    "p_plus_pad": terminal_tops("p_plus"),  # the load's positive
    "balance_pads": terminal_tops("b1", "b2", "b_plus"),  # B1, B2, B+
    "terminal_holes": result.faces("%CYLINDER").filter(
        lambda f: f.BoundingBox().zlen > pcb_t + 1e-6),  # the six through holes
    "bottom": result.faces("<Z"),
}

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
