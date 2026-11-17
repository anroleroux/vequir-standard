"""Single-cell 3.7 V 3 A BMS strip (Sunlephant 210454).

A one-cell lithium protection board, as Mantech lists it: L = 30.3,
W = 3.7, T = 2.0 mm. A narrow board with a nickel-plated pad at each end,
the 8205A dual MOSFET and the protection IC between them.

Assumptions where the description is silent:
- T = 2.0 mm is the overall thickness: a 1.0 mm board and parts 1.0 mm tall;
- the end pads are 4.0 x 3.2 mm, 0.3 mm thick, 0.2 mm in from the board's
  end, centred across it: B+ at +x and P- at -x (as the photo reads);
- the 8205A is a TSSOP-8 body, 4.4 x 3.0 mm, lying along the board, 3 mm
  towards -x of centre; the protection IC a SOT-23-6 body, 2.9 x 1.6 mm,
  6 mm towards +x; the small resistors and capacitors are not modelled;
- the leads, the B- pad and the printing are not modelled;
- x along the board, y across it, z up; centred on x and y, underside on z = 0.
"""
import cadquery as cq

# the board, in mm
length = 30.3  # along x
width = 3.7  # along y
thickness = 2.0  # overall, over the parts
pcb_t = 1.0  # board thickness

# the end pads
pad_l = 4.0  # along x
pad_w = 3.2  # along y
pad_t = 0.3  # thickness
pad_inset = 0.2  # from the board's end

# the chips
part_h = thickness - pcb_t  # their height above the board
mosfet = (4.4, 3.0)  # 8205A, TSSOP-8 body: along x, across
mosfet_x = -3.0
ic = (2.9, 1.6)  # protection IC, SOT-23-6 body
ic_x = 6.0

board = cq.Workplane("XY").box(length, width, pcb_t, centered=(True, True, False))
pad_x = length / 2 - pad_inset - pad_l / 2  # each pad's centre
pads = (
    cq.Workplane("XY", origin=(0, 0, pcb_t))
    .pushPoints([(pad_x, 0), (-pad_x, 0)])
    .rect(pad_l, pad_w)
    .extrude(pad_t)
)
chips = (
    cq.Workplane("XY", origin=(0, 0, pcb_t))
    .center(mosfet_x, 0).rect(*mosfet).extrude(part_h)
    .union(cq.Workplane("XY", origin=(ic_x, 0, pcb_t)).rect(*ic).extrude(part_h))
)
result = board.union(pads).union(chips)

top_of_pads = pcb_t + pad_t
regions = {
    "b_plus_pad": result.faces("+Z").filter(  # at +x, to the cell's positive
        lambda f: abs(f.Center().z - top_of_pads) < 1e-6 and f.Center().x > 0),
    "p_minus_pad": result.faces("+Z").filter(  # at -x, the pack's negative out
        lambda f: abs(f.Center().z - top_of_pads) < 1e-6 and f.Center().x < 0),
    "bottom": result.faces("<Z"),
}

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
